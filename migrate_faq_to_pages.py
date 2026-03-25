#!/usr/bin/env python3
"""
Migrate FAQ posts (IDs 3068–3120) → pages under parent ai-transformation-faq (ID 3067)
Result: ableneo.com/ai-transformation-faq/[slug]/
"""

import base64, requests, time

WP_URL      = "https://ableneo.com"
WP_USER     = "peter.urbanec"
WP_PASSWORD = "XOIK DAyS SJ3u GUqp zoq8 5jFc"
PARENT_ID   = 3067

FAQ_POST_IDS = list(range(3068, 3121))   # 3068 to 3120 inclusive

def headers():
    token = base64.b64encode(f"{WP_USER}:{WP_PASSWORD}".encode()).decode()
    return {
        "Authorization": f"Basic {token}",
        "Content-Type":  "application/json",
    }

def get_post(post_id):
    r = requests.get(f"{WP_URL}/wp-json/wp/v2/posts/{post_id}", headers=headers())
    if r.status_code == 200:
        return r.json()
    print(f"  ⚠️  GET post {post_id} failed: {r.status_code}")
    return None

def create_page(post):
    payload = {
        "title":   post["title"]["rendered"],
        "content": post["content"]["rendered"],
        "excerpt": post.get("excerpt", {}).get("rendered", ""),
        "slug":    post["slug"],
        "status":  "publish",
        "parent":  PARENT_ID,
    }
    r = requests.post(f"{WP_URL}/wp-json/wp/v2/pages", json=payload, headers=headers())
    if r.status_code in (200, 201):
        return r.json()
    print(f"  ❌ CREATE page failed: {r.status_code} {r.text[:200]}")
    return None

def delete_post(post_id):
    r = requests.delete(
        f"{WP_URL}/wp-json/wp/v2/posts/{post_id}",
        params={"force": True},
        headers=headers()
    )
    if r.status_code == 200:
        return True
    print(f"  ⚠️  DELETE post {post_id} failed: {r.status_code}")
    return False

def main():
    print(f"🔄 Migrating {len(FAQ_POST_IDS)} FAQ posts → pages under parent {PARENT_ID}\n")
    success, failed = 0, 0

    for post_id in FAQ_POST_IDS:
        post = get_post(post_id)
        if not post:
            failed += 1
            continue

        slug  = post["slug"]
        title = post["title"]["rendered"]
        print(f"  [{post_id}] {slug}")

        page = create_page(post)
        if not page:
            failed += 1
            continue

        new_url = page.get("link", "")
        deleted = delete_post(post_id)
        status  = "✅" if deleted else "⚠️ (page created, post NOT deleted)"
        print(f"    {status} → {new_url}")
        success += 1
        time.sleep(0.3)   # polite rate limit

    print(f"\n{'='*50}")
    print(f"✅ Migrated:  {success}")
    print(f"❌ Failed:    {failed}")
    print(f"\nHub page: https://www.ableneo.com/ai-transformation-faq/")

if __name__ == "__main__":
    main()
