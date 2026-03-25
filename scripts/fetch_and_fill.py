#!/usr/bin/env python3
"""
Weekly auto-fill: fetch LinkedIn stats and write them into the current week's
Notion scorecard row.

Usage (called by Claude scheduled task every Friday):
    python scripts/fetch_and_fill.py [YYYY-MM-DD]

If a date arg is given it is used as this week's Monday; otherwise the
current week's Monday is derived automatically.
"""

import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv
load_dotenv(ROOT / ".env")

from api.notion_client import get_client, ds_id
from api.linkedin_client import fetch_weekly_stats


# ── Date helpers ──────────────────────────────────────────────────────

def this_week_monday() -> str:
    today = datetime.now(tz=timezone.utc).date()
    monday = today - timedelta(days=today.weekday())   # weekday() 0 = Monday
    return monday.strftime("%Y-%m-%d")


# ── Notion helpers ────────────────────────────────────────────────────

def find_week_page(client, monday_str: str) -> str | None:
    """Return the Notion page ID for the row whose Week == monday_str, or None."""
    res = client.data_sources.query(
        ds_id(),
        filter={
            "property": "Week",
            "date": {"equals": monday_str},
        },
    )
    pages = res.get("results", [])
    return pages[0]["id"] if pages else None


def update_notion_row(client, page_id: str, fields: dict):
    """Patch number fields on an existing Notion page."""
    properties = {}
    for field, value in fields.items():
        if value is not None:
            properties[field] = {"number": value}

    if not properties:
        print("  Nothing to update (all values are None).")
        return

    client.pages.update(page_id, properties=properties)
    print(f"  Updated {len(properties)} field(s) on page {page_id}")


# ── Main ──────────────────────────────────────────────────────────────

def main():
    monday = sys.argv[1] if len(sys.argv) > 1 else this_week_monday()
    print(f"[fetch_and_fill] week starting {monday}")

    # 1. Fetch LinkedIn stats
    print("📊  Fetching LinkedIn stats …")
    try:
        li_stats = fetch_weekly_stats(monday)
        print(f"  LinkedIn → {li_stats}")
    except Exception as e:
        print(f"  ⚠️  LinkedIn fetch failed: {e}")
        li_stats = {}

    # 2. Merge all fetched stats
    all_stats = {**li_stats}

    if not any(v is not None for v in all_stats.values()):
        print("  No data fetched — nothing to write to Notion.")
        return

    # 3. Find the Notion row for this week
    client = get_client()
    page_id = find_week_page(client, monday)

    if not page_id:
        print(f"  ⚠️  No Notion scorecard row found for {monday}.")
        print("       Create it first via the dashboard or the scorecard-creator task.")
        return

    # 4. Update Notion
    print(f"📝  Updating Notion row {page_id} …")
    update_notion_row(client, page_id, all_stats)
    print("✅  Scorecard auto-filled.")


if __name__ == "__main__":
    main()
