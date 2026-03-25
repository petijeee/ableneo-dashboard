#!/usr/bin/env python3
"""
faq_improver.py — SEO-enhance all FAQ articles on ableneo.com
Improvements per article:
  1. Rewrite H2s as questions (PAA uplift)
  2. Add internal cross-links between related articles
  3. Add "Next Reads" section at the end
  4. Add at least one comparison/data table
  5. Add FAQ schema JSON-LD (rich results)
  6. Weave in Slovak/Czech regional context
"""

import os, base64, re, time, json
import requests
import anthropic
import dotenv

ENV_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
_env = dotenv.dotenv_values(ENV_PATH)

WP_URL      = _env["WP_URL"].rstrip("/")
WP_USER     = _env["WP_USER"]
WP_PASS     = _env["WP_APP_PASSWORD"]
API_KEY     = _env["ANTHROPIC_API_KEY"]
PARENT_ID   = 3067
BASE        = "https://www.ableneo.com/ai-transformation-faq"

client = anthropic.Anthropic(api_key=API_KEY)

def auth():
    token = base64.b64encode(f"{WP_USER}:{WP_PASS}".encode()).decode()
    return {"Authorization": f"Basic {token}", "Content-Type": "application/json"}

def get_all_children():
    r = requests.get(f"{WP_URL}/wp-json/wp/v2/pages",
        params={"parent": PARENT_ID, "per_page": 100, "status": "publish",
                "_fields": "id,slug,title,content,link"},
        headers=auth())
    return r.json()

def strip_tags(html):
    return re.sub('<[^>]+>', '', html)

def clean_claude_output(text):
    """Remove markdown code fences if Claude wrapped content in them."""
    text = text.strip()
    text = re.sub(r'^```html\s*', '', text)
    text = re.sub(r'^```\s*', '', text)
    text = re.sub(r'\s*```$', '', text)
    return text.strip()

def improve_article(slug, title, current_html, all_slugs):
    """Send article to Claude for full SEO improvement."""

    # Build a short list of related articles for cross-linking
    related = [s for s in all_slugs if s != slug][:20]
    related_str = "\n".join(f"- {BASE}/{s}/" for s in related)

    system = """You are an expert SEO content editor specialising in B2B technology content.
You write clean, semantic HTML — no markdown, no code fences, just raw HTML ready for WordPress.
Your job is to improve existing articles to maximise rankings in Google, Google AI Overviews,
Perplexity, and ChatGPT for queries related to AI business transformation in Slovakia and Czech Republic."""

    prompt = f"""Improve this WordPress article HTML. Apply ALL of the following:

1. **Rewrite every H2 as a question** (e.g. "Why Data Quality Matters" → "Why Does Data Quality Matter for AI?")
   — this wins "People Also Ask" featured snippets

2. **Add 3–5 internal cross-links** naturally within the body text using these related article URLs:
{related_str}
   — use descriptive anchor text, not "click here"

3. **Add a "Next Reads" section** at the very end (before any closing tags) with 3 relevant links:
   <h2>Next Reads</h2>
   <ul>
     <li><a href="...">Title</a></li>
     ...
   </ul>

4. **Add at least one HTML table** with relevant comparison/data (e.g. comparing options, stages, timelines, costs)
   — tables win featured snippets

5. **Add FAQ schema JSON-LD** at the very top inside a <script type="application/ld+json"> tag.
   Include 4–6 Q&A pairs from the article content. Format:
   {{"@context":"https://schema.org","@type":"FAQPage","mainEntity":[{{"@type":"Question","name":"...","acceptedAnswer":{{"@type":"Answer","text":"..."}}}}]}}

6. **Weave in Slovak/Czech context** naturally — mention Slovak/Czech companies, reference local regulations
   (EU AI Act, GDPR), local talent market, or regional business culture where relevant.
   Add at least 2 references to Slovakia or Czech Republic.

ARTICLE TITLE: {title}
ARTICLE SLUG: {slug}

CURRENT HTML:
{current_html}

Return ONLY the improved HTML. No markdown. No explanations. No code fences. Raw HTML only."""

    msg = client.messages.create(
        model="claude-opus-4-5",
        max_tokens=4000,
        messages=[{"role": "user", "content": prompt}],
        system=system,
    )
    return clean_claude_output(msg.content[0].text)

def update_page(page_id, title, content):
    r = requests.post(f"{WP_URL}/wp-json/wp/v2/pages/{page_id}",
        json={"title": title, "content": content, "status": "publish"},
        headers=auth())
    return r.status_code == 200

def count_words(html):
    return len(strip_tags(html).split())

def main():
    print("🔍 Fetching all FAQ child pages...")
    children = get_all_children()
    all_slugs = [c["slug"] for c in children]
    print(f"   Found {len(children)} articles\n")

    ok = 0
    failed = 0

    for i, page in enumerate(children, 1):
        slug  = page["slug"]
        title = page["title"]["rendered"]
        pid   = page["id"]
        current_html = page["content"]["rendered"]
        wc_before = count_words(current_html)

        print(f"[{i:02d}/{len(children)}] {slug}")
        print(f"         Before: {wc_before} words")

        try:
            improved = improve_article(slug, title, current_html, all_slugs)
            wc_after = count_words(improved)

            success = update_page(pid, title, improved)
            if success:
                print(f"         After:  {wc_after} words  ✅")
                ok += 1
            else:
                print(f"         ❌ WordPress update failed")
                failed += 1

        except Exception as e:
            print(f"         ❌ Error: {e}")
            failed += 1

        # Respect API rate limits
        time.sleep(2)

    print(f"\n{'='*50}")
    print(f"✅ Improved: {ok}/{len(children)}")
    print(f"❌ Failed:   {failed}")
    print(f"\nCheck: {BASE}/")

if __name__ == "__main__":
    main()
