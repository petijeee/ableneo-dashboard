#!/usr/bin/env python3
"""
Ableneo FAQ Engine
------------------
Usage:
  python3 faq_engine.py expand    — expand all short articles to 1200+ words
  python3 faq_engine.py daily     — generate + publish 1 new article
  python3 faq_engine.py new "<topic>"  — generate + publish a specific topic
"""

import os, sys, base64, time, json, re, requests
from datetime import date
from pathlib import Path

# ── Load .env ────────────────────────────────────────────────────────
env_path = Path(__file__).parent / ".env"
for line in env_path.read_text().splitlines():
    line = line.strip()
    if not line or line.startswith("#") or "=" not in line:
        continue
    k, _, v = line.partition("=")
    k = k.strip()
    v = v.strip().strip('"').strip("'")
    if k and v:
        os.environ[k] = v   # always override so fresh .env values are used

import anthropic

ANTHROPIC_KEY = os.environ["ANTHROPIC_API_KEY"]
WP_URL        = os.environ.get("WP_URL", "https://ableneo.com")
WP_USER       = os.environ.get("WP_USER", "peter.urbanec")
WP_PASSWORD   = os.environ.get("WP_APP_PASSWORD", "")
PARENT_ID     = 3067
BASE_URL      = "https://www.ableneo.com/ai-transformation-faq"
MIN_WORDS     = 800   # articles below this get expanded

client = anthropic.Anthropic(api_key=ANTHROPIC_KEY)


# ── WordPress helpers ─────────────────────────────────────────────────

def wp_auth():
    token = base64.b64encode(f"{WP_USER}:{WP_PASSWORD}".encode()).decode()
    return {"Authorization": f"Basic {token}", "Content-Type": "application/json"}

def get_all_faq_pages():
    r = requests.get(f"{WP_URL}/wp-json/wp/v2/pages",
        params={"parent": PARENT_ID, "per_page": 100, "status": "publish",
                "_fields": "id,slug,title,content,link"},
        headers=wp_auth())
    return r.json() if r.status_code == 200 else []

def update_wp_page(page_id, title, content):
    r = requests.post(f"{WP_URL}/wp-json/wp/v2/pages/{page_id}",
        json={"title": title, "content": content, "status": "publish"},
        headers=wp_auth())
    return r.status_code in (200, 201)

def create_wp_page(title, slug, content):
    r = requests.post(f"{WP_URL}/wp-json/wp/v2/pages",
        json={"title": title, "slug": slug, "content": content,
              "status": "publish", "parent": PARENT_ID},
        headers=wp_auth())
    if r.status_code in (200, 201):
        return r.json()
    print(f"  ❌ Create failed: {r.status_code} {r.text[:200]}")
    return None

def slug_exists(slug):
    r = requests.get(f"{WP_URL}/wp-json/wp/v2/pages",
        params={"slug": slug, "status": "publish"}, headers=wp_auth())
    pages = r.json()
    return len(pages) > 0 if isinstance(pages, list) else False

def update_hub_page(new_slug, new_title):
    """Append new article link to the hub page under correct category."""
    r = requests.get(f"{WP_URL}/wp-json/wp/v2/pages/{PARENT_ID}", headers=wp_auth())
    if r.status_code != 200:
        return
    page = r.json()
    content = page["content"]["rendered"]
    link = f'<li><a href="{BASE_URL}/{new_slug}/">{new_title}</a></li>'
    # append before closing </ul> of last section
    updated = content.replace("</ul>\n\n<hr/>", f"  {link}\n</ul>\n\n<hr/>", 1)
    if updated == content:
        updated = content + f"\n<ul>\n  {link}\n</ul>"
    requests.post(f"{WP_URL}/wp-json/wp/v2/pages/{PARENT_ID}",
        json={"content": updated}, headers=wp_auth())


# ── Claude content generation ─────────────────────────────────────────

SYSTEM_PROMPT = """You are a senior AI transformation consultant writing authoritative content for Ableneo,
an AI transformation consultancy based in Slovakia serving Slovak and Czech companies.

Writing style:
- Clear, direct, professional — no fluff or hype
- Practical and specific — give real examples, not vague generalisations
- Authoritative but accessible — C-level and director audience
- British English spelling
- Structure: H2 and H3 headings, bullet points, numbered lists where appropriate
- Length: 1100–1400 words of actual content (excluding HTML tags)
- Always end with a CTA mentioning Ableneo and linking to /contact

Format: Return clean HTML using only <h2>, <h3>, <p>, <ul>, <ol>, <li>, <table>, <thead>, <tbody>, <tr>, <th>, <td>, <strong>, <a>, <script> tags.
No markdown. No code blocks. No preamble — start directly with <p> or <h2>.

Context about Ableneo:
- AI transformation consultancy for mid-size and enterprise companies
- Focus: Slovakia and Czech Republic
- Services: AI strategy, implementation, change management, AI readiness assessments
- Website: https://www.ableneo.com
- FAQ hub: https://www.ableneo.com/ai-transformation-faq/
"""

IMPROVE_PROMPT = """You are an expert SEO content editor. Rewrite the article below applying ALL of these improvements:

1. QUESTION H2s — Rewrite every <h2> as a direct question (e.g. "The Core Shift" → "What Is the Core Difference Between AI and Traditional Business?"). This wins "People Also Ask" boxes.

2. INTERNAL CROSS-LINKS — Add 4–6 contextual <a href="..."> links to related articles from this list:
{link_list}

3. NEXT READS SECTION — Add at the end, before the CTA, a section:
<h2>What to Read Next</h2>
<ul>
  <li><a href="...">Article title</a> — one-line reason why</li>
  ... (3 articles)
</ul>

4. TABLES — Add at least one <table> with <thead>/<tbody> where a comparison, checklist, or list of items can be shown as a table. This wins featured snippets.

5. FAQ SCHEMA — Append at the very end a <script type="application/ld+json"> block with FAQPage schema containing 3–5 Q&A pairs extracted from the article content.

6. REGIONAL CONTEXT — Weave in 2–3 specific references to Slovak or Czech business reality (e.g. specific industries, regulatory context, typical company sizes, local market dynamics). Make it feel written for this market, not generic.

Return the complete rewritten article as clean HTML. No markdown. No preamble. Start directly with <p> or <h2>."""

def clean_claude_output(text):
    """Strip markdown code fences if Claude wrapped content in them."""
    text = re.sub(r'^```(?:html)?\s*', '', text.strip())
    text = re.sub(r'\s*```$', '', text.strip())
    return text.strip()

ARTICLE_RULES = """
MANDATORY structure for every article:

1. FAQ SCHEMA FIRST — Start with a <script type="application/ld+json"> FAQPage schema block containing 4–6 Q&A pairs from the article. Format:
{"@context":"https://schema.org","@type":"FAQPage","mainEntity":[{"@type":"Question","name":"...","acceptedAnswer":{"@type":"Answer","text":"..."}}]}

2. QUESTION H2s — Every <h2> must be phrased as a direct question (e.g. "Why Does Data Quality Matter for AI?" not "Data Quality"). This wins "People Also Ask" snippets.

3. AT LEAST ONE TABLE — Include a <table> with <thead>/<tbody> comparing options, stages, timelines, or criteria. Tables win featured snippets.

4. INTERNAL CROSS-LINKS — Add 4–6 contextual <a href="{base}/[related-slug]/"> links naturally within the body. Use descriptive anchor text.

5. NEXT READS SECTION — End with:
<h2>What Should You Read Next?</h2>
<ul>
  <li><a href="{base}/[slug]/">Article title</a> — one-line reason</li>
  <li><a href="{base}/[slug]/">Article title</a> — one-line reason</li>
  <li><a href="{base}/[slug]/">Article title</a> — one-line reason</li>
</ul>

6. SK/CZ CONTEXT — Weave in at least 2 specific references to Slovak or Czech business reality (industries, regulations, company sizes, local dynamics). Make it feel written for this market.

7. CTA AT THE END — Final paragraph links to https://www.ableneo.com/contact

Return ONLY clean HTML. No markdown. No code fences. No preamble.""".replace("{base}", BASE_URL)

def generate_article(title, slug, existing_content=None):
    """Generate or expand an article using Claude — always applying full quality standards."""
    if existing_content:
        plain = re.sub('<[^>]+>', '', existing_content)
        word_count = len(plain.split())
        prompt = f"""Expand and fully rewrite this article to 1300–1600 words applying ALL mandatory rules below.

Title: {title}
Slug: {slug}
Current content ({word_count} words):
{existing_content[:3000]}

{ARTICLE_RULES}"""
    else:
        prompt = f"""Write a comprehensive 1300–1600 word article for the Ableneo AI Transformation FAQ applying ALL mandatory rules below.

Title: {title}
Slug: {slug}

{ARTICLE_RULES}"""

    message = client.messages.create(
        model="claude-haiku-4-5",
        max_tokens=3000,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}]
    )
    return clean_claude_output(message.content[0].text)


# ── Topic bank for daily generation ──────────────────────────────────

TOPIC_BANK = [
    ("AI Transformation KPIs: What to Measure and How", "ai-transformation-kpis"),
    ("How to Get Board Approval for AI Investment", "ai-board-approval"),
    ("AI in Accounting and Finance Departments", "ai-in-finance-accounting"),
    ("How to Write an AI Use Case Business Case", "ai-use-case-business-case"),
    ("AI Procurement: What to Look For in Contracts", "ai-procurement-contracts"),
    ("The Role of the Chief AI Officer", "chief-ai-officer-role"),
    ("AI Transformation in Insurance", "ai-transformation-insurance"),
    ("How to Audit Your AI Systems", "ai-systems-audit"),
    ("AI in Legal Departments: Opportunities and Risks", "ai-in-legal"),
    ("How to Build an AI Centre of Excellence", "ai-centre-of-excellence"),
    ("AI for Customer Segmentation", "ai-customer-segmentation"),
    ("Responsible AI: A Practical Framework for Companies", "responsible-ai-framework"),
    ("AI in Project Management: Tools and Techniques", "ai-project-management-tools"),
    ("How to Measure AI Adoption in Your Organisation", "measuring-ai-adoption"),
    ("AI Transformation in Healthcare", "ai-transformation-healthcare"),
    ("Building a Proprietary AI Dataset", "building-proprietary-ai-dataset"),
    ("AI in Procurement and Supply Management", "ai-in-procurement"),
    ("How to Transition from RPA to AI", "rpa-to-ai-transition"),
    ("AI Transformation in Education and Training", "ai-transformation-education"),
    ("The Business Case for Explainable AI", "explainable-ai-business-case"),
    ("AI in Real Estate: Use Cases and ROI", "ai-in-real-estate"),
    ("How to Set Up an AI Sandbox Environment", "ai-sandbox-environment"),
    ("AI-Powered Business Intelligence: Beyond Dashboards", "ai-business-intelligence"),
    ("How to Handle AI Incidents and Failures", "ai-incident-management"),
    ("AI Transformation for Family-Owned Businesses", "ai-family-businesses"),
    ("Building AI into Your Product Roadmap", "ai-product-roadmap"),
    ("AI and Cybersecurity: Risks and Protections", "ai-cybersecurity"),
    ("How to Upskill Your IT Team for AI", "upskilling-it-team-ai"),
    ("AI in Corporate Communications", "ai-corporate-communications"),
    ("The Future of Work After AI Transformation", "future-of-work-ai"),
]

def get_next_topic():
    """Pick the next unpublished topic from the bank."""
    for title, slug in TOPIC_BANK:
        if not slug_exists(slug):
            return title, slug
    return None, None


# ── Commands ──────────────────────────────────────────────────────────

def cmd_improve():
    """Apply full SEO improvement pass to all articles."""
    print("🔍 Fetching all FAQ articles...\n")
    pages = get_all_faq_pages()
    if not pages:
        print("❌ No pages found.")
        return

    # Build link list for cross-linking
    link_list = "\n".join(
        f"- {BASE_URL}/{p['slug']}/ — {p['title']['rendered']}"
        for p in pages
    )

    print(f"Found {len(pages)} articles. Improving all with SEO pass...\n")

    for i, page in enumerate(pages):
        slug  = page["slug"]
        title = page["title"]["rendered"]
        current_html = page["content"]["rendered"]
        # Strip old JSON-LD schema blocks before sending
        clean_html = re.sub(
            r'<script[^>]*type=["\']application/ld\+json["\'][^>]*>.*?</script>\s*',
            '', current_html, flags=re.DOTALL
        ).strip()

        print(f"  [{i+1}/{len(pages)}] {slug} → improving...")
        try:
            prompt = IMPROVE_PROMPT.replace("{link_list}", link_list) + \
                     f"\n\nTitle: {title}\n\nCurrent article HTML:\n{clean_html[:4000]}"
            message = client.messages.create(
                model="claude-haiku-4-5",
                max_tokens=3000,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": prompt}]
            )
            content = clean_claude_output(message.content[0].text)
            ok = update_wp_page(page["id"], title, content)
            wc = len(re.sub('<[^>]+>', '', content).split())
            print(f"    {'✅' if ok else '❌'} {wc} words → {page['link']}")
        except Exception as e:
            print(f"    ❌ Error: {e}")
        time.sleep(1.5)

    print(f"\n✅ SEO improvement pass complete. {len(pages)} articles updated.")


def cmd_expand():
    """Expand all articles below MIN_WORDS threshold."""
    print(f"🔍 Fetching all FAQ articles...\n")
    pages = get_all_faq_pages()
    short = []
    for p in pages:
        plain = re.sub('<[^>]+>', '', p["content"]["rendered"])
        wc = len(plain.split())
        if wc < MIN_WORDS:
            short.append((p, wc))

    print(f"Found {len(short)} articles under {MIN_WORDS} words (out of {len(pages)} total)\n")

    for i, (page, wc) in enumerate(short):
        slug  = page["slug"]
        title = page["title"]["rendered"]
        print(f"  [{i+1}/{len(short)}] {slug} ({wc} words) → expanding...")
        try:
            content = generate_article(title, slug, page["content"]["rendered"])
            ok = update_wp_page(page["id"], title, content)
            new_wc = len(re.sub('<[^>]+>', '', content).split())
            print(f"    {'✅' if ok else '❌'} {new_wc} words → {page['link']}")
        except Exception as e:
            print(f"    ❌ Error: {e}")
        time.sleep(1.5)

    print(f"\n✅ Expansion complete.")

def cmd_daily():
    """Generate and publish one new article."""
    title, slug = get_next_topic()
    if not title:
        print("✅ All topics in bank already published. Add more to TOPIC_BANK.")
        return
    print(f"📝 Generating: {title}")
    try:
        content = generate_article(title, slug)
        page = create_wp_page(title, slug, content)
        if page:
            wc = len(re.sub('<[^>]+>', '', content).split())
            update_hub_page(slug, title)
            print(f"✅ Published ({wc} words) → {page['link']}")
        else:
            print("❌ Failed to publish")
    except Exception as e:
        print(f"❌ Error: {e}")

def cmd_new(topic):
    """Generate and publish a specific topic."""
    slug = re.sub(r'[^a-z0-9]+', '-', topic.lower()).strip('-')
    if slug_exists(slug):
        print(f"⚠️  Article already exists: {BASE_URL}/{slug}/")
        return
    print(f"📝 Generating: {topic}")
    try:
        content = generate_article(topic, slug)
        page = create_wp_page(topic, slug, content)
        if page:
            wc = len(re.sub('<[^>]+>', '', content).split())
            update_hub_page(slug, topic)
            print(f"✅ Published ({wc} words) → {page['link']}")
    except Exception as e:
        print(f"❌ Error: {e}")


# ── Entry point ───────────────────────────────────────────────────────

if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "help"

    if cmd == "improve":
        cmd_improve()
    elif cmd == "expand":
        cmd_expand()
    elif cmd == "daily":
        cmd_daily()
    elif cmd == "new" and len(sys.argv) > 2:
        cmd_new(" ".join(sys.argv[2:]))
    else:
        print(__doc__)
