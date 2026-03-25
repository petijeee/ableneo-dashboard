"""
LinkedIn Company Page fetcher
Fetches: page impressions (KR2), posts published (L1), avg post impressions (L2)

Required .env vars:
  LINKEDIN_ACCESS_TOKEN  — from scripts/linkedin_auth.py
  LINKEDIN_ORG_ID        — numeric ID from linkedin.com/company/<id>/admin/

Docs: https://learn.microsoft.com/en-us/linkedin/marketing/community-management/
"""
import os
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests

# ── Helpers ──────────────────────────────────────────────────────────

_TOKEN_FILE = Path(__file__).parent.parent / ".linkedin_token.json"


def _load_token() -> dict:
    """Load token from .linkedin_token.json (written by linkedin_auth.py)."""
    if _TOKEN_FILE.exists():
        with open(_TOKEN_FILE) as f:
            return json.load(f)
    # Fallback to env var (e.g. set manually or via CI)
    token = os.environ.get("LINKEDIN_ACCESS_TOKEN")
    if token:
        return {"access_token": token}
    raise RuntimeError(
        "No LinkedIn access token found. "
        "Run  python scripts/linkedin_auth.py  to authorise."
    )


def _headers() -> dict:
    data = _load_token()
    return {
        "Authorization": f"Bearer {data['access_token']}",
        "X-Restli-Protocol-Version": "2.0.0",
        "LinkedIn-Version": "202501",
    }


def _org_urn() -> str:
    org_id = os.environ.get("LINKEDIN_ORG_ID", "").strip()
    if not org_id:
        raise RuntimeError("LINKEDIN_ORG_ID is not set in .env")
    return f"urn:li:organization:{org_id}"


# ── Public API ───────────────────────────────────────────────────────

def fetch_weekly_stats(monday_date_str: str) -> dict:
    """
    Fetch LinkedIn stats for the 7-day window starting on monday_date_str.

    Returns:
        {
          "KR2_LinkedIn_Impressions": int,   # total page + post impressions
          "L1_Posts_Published":       int,   # posts created that week
          "L2_Post_Avg_Impressions":  int,   # mean impressions per post
        }
    """
    monday = datetime.strptime(monday_date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    sunday = monday + timedelta(days=6, hours=23, minutes=59, seconds=59)

    start_ms = int(monday.timestamp() * 1000)
    end_ms   = int(sunday.timestamp() * 1000)

    org_urn  = _org_urn()
    hdrs     = _headers()

    impressions  = _fetch_page_impressions(org_urn, hdrs, start_ms, end_ms)
    posts        = _fetch_posts_this_week(org_urn, hdrs, start_ms, end_ms)

    posts_count  = len(posts)
    post_imps    = [p.get("impressions", 0) for p in posts]
    avg_imps     = round(sum(post_imps) / posts_count) if posts_count else None

    return {
        "KR2_LinkedIn_Impressions": impressions if impressions is not None else None,
        "L1_Posts_Published":       posts_count if posts_count > 0 else None,
        "L2_Post_Avg_Impressions":  avg_imps,
    }


# ── Internal fetchers ────────────────────────────────────────────────

def _fetch_page_impressions(org_urn: str, hdrs: dict, start_ms: int, end_ms: int):
    """Total impressions on organisation page views for the given period."""
    try:
        resp = requests.get(
            "https://api.linkedin.com/v2/organizationalEntityShareStatistics",
            headers=hdrs,
            params={
                "q": "organizationalEntity",
                "organizationalEntity": org_urn,
                "timeIntervals.timeGranularityType": "DAY",
                "timeIntervals.timeRange.start": start_ms,
                "timeIntervals.timeRange.end": end_ms,
            },
            timeout=15,
        )
        resp.raise_for_status()
        elements = resp.json().get("elements", [])
        return sum(
            e.get("totalShareStatistics", {}).get("impressionCount", 0)
            for e in elements
        )
    except requests.HTTPError as e:
        print(f"[linkedin] share-stats HTTP {e.response.status_code}: {e.response.text}")
        return None


def _fetch_posts_this_week(org_urn: str, hdrs: dict, start_ms: int, end_ms: int) -> list:
    """Return list of posts published this week, each with .impressions."""
    posts = []
    start_param = {"author": org_urn, "q": "author", "count": 50, "sortBy": "LAST_MODIFIED"}

    try:
        resp = requests.get(
            "https://api.linkedin.com/rest/posts",
            headers=hdrs,
            params=start_param,
            timeout=15,
        )
        resp.raise_for_status()
        all_posts = resp.json().get("elements", [])

        for post in all_posts:
            created = post.get("createdAt", 0)
            if start_ms <= created <= end_ms:
                post_urn = post.get("id", "")
                imps = _fetch_post_impressions(post_urn, hdrs)
                posts.append({"urn": post_urn, "impressions": imps})
            elif created < start_ms:
                break  # sorted descending — no need to keep going

    except requests.HTTPError as e:
        print(f"[linkedin] posts HTTP {e.response.status_code}: {e.response.text}")

    return posts


def _fetch_post_impressions(post_urn: str, hdrs: dict) -> int:
    """Fetch impression count for a single post."""
    if not post_urn:
        return 0
    try:
        resp = requests.get(
            "https://api.linkedin.com/v2/socialActions/{}/statistics".format(
                requests.utils.quote(post_urn, safe="")
            ),
            headers=hdrs,
            timeout=10,
        )
        if resp.status_code == 200:
            return resp.json().get("impressionCount", 0)
    except Exception:
        pass
    return 0
