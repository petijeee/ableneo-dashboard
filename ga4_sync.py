#!/usr/bin/env python3
"""
ga4_sync.py — Sync weekly GA4 visitors to Notion KR3
Run manually: python3 ga4_sync.py
Cron (every Monday 8:00): set up via launchd or cron
"""

import os, base64, json, requests
from datetime import date, timedelta
import dotenv
from google.analytics.data_v1beta import BetaAnalyticsDataClient
from google.analytics.data_v1beta.types import (
    RunReportRequest, DateRange, Metric
)
from google.oauth2 import service_account

ENV_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
_env = dotenv.dotenv_values(ENV_PATH)

NOTION_TOKEN  = _env["NOTION_TOKEN"]
NOTION_DB_ID  = _env["NOTION_DB_ID"]
GA4_PROPERTY  = "460545906"
KEY_FILE      = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ableneo-dashboard-876971dadc19.json")

def notion_auth():
    return {
        "Authorization": f"Bearer {NOTION_TOKEN}",
        "Content-Type": "application/json",
        "Notion-Version": "2022-06-28"
    }

def get_current_week_page_id():
    """Find this week's Notion page."""
    today = date.today()
    monday = today - timedelta(days=today.weekday())
    r = requests.post(
        f"https://api.notion.com/v1/databases/{NOTION_DB_ID}/query",
        json={
            "filter": {"property": "Week", "date": {"equals": str(monday)}},
            "page_size": 1
        },
        headers=notion_auth()
    )
    data = r.json()
    results = data.get("results", [])
    if not results:
        print("❌ No page found for this week")
        return None
    return results[0]["id"]

def get_visitors_with_yoy():
    """Get last 30 days visitors + same period last year from GA4."""
    credentials = service_account.Credentials.from_service_account_file(
        KEY_FILE,
        scopes=["https://www.googleapis.com/auth/analytics.readonly"]
    )
    client = BetaAnalyticsDataClient(credentials=credentials)

    today = date.today()
    # Current: last 30 days
    current_start = today - timedelta(days=30)
    # Prior year: same 30-day window 1 year ago
    prior_start   = today - timedelta(days=365+30)
    prior_end     = today - timedelta(days=365)

    request = RunReportRequest(
        property=f"properties/{GA4_PROPERTY}",
        date_ranges=[
            DateRange(start_date=str(current_start), end_date=str(today),     name="current"),
            DateRange(start_date=str(prior_start),   end_date=str(prior_end), name="prior_year"),
        ],
        metrics=[Metric(name="activeUsers")]
    )
    response = client.run_report(request)

    current = 0
    prior   = 0
    for row in response.rows:
        val = int(row.metric_values[0].value)
        if row.dimension_values[0].value == "current":
            current = val
        else:
            prior = val

    yoy_pct = ((current - prior) / prior * 100) if prior > 0 else None
    return current, prior, yoy_pct

def update_notion_page(page_id, visitors, yoy_pct):
    """Update KR3_Website_Visitors and KR3_Website_YoY in Notion."""
    props = {"KR3_Website_Visitors": {"number": visitors}}
    if yoy_pct is not None:
        props["KR3_Website_YoY"] = {"number": round(yoy_pct / 100, 4)}  # Notion percent = decimal
    r = requests.patch(
        f"https://api.notion.com/v1/pages/{page_id}",
        json={"properties": props},
        headers=notion_auth()
    )
    return r.status_code == 200

def main():
    print("🔍 Fetching GA4 visitors (last 30 days + YoY)...")
    try:
        current, prior, yoy_pct = get_visitors_with_yoy()
        yoy_str = f"{yoy_pct:+.1f}%" if yoy_pct is not None else "N/A (no prior year data)"
        print(f"   Current (last 30d): {current:,}")
        print(f"   Prior year (same):  {prior:,}")
        print(f"   YoY change:         {yoy_str}")
    except Exception as e:
        print(f"❌ GA4 error: {e}")
        return

    print("🔍 Finding current week in Notion...")
    page_id = get_current_week_page_id()
    if not page_id:
        return

    print(f"   Page ID: {page_id}")
    ok = update_notion_page(page_id, current, yoy_pct)

    if ok:
        print(f"✅ KR3_Website_Visitors → {current:,}")
        print(f"✅ KR3_Website_YoY      → {yoy_str}")
    else:
        print("❌ Notion update failed")

if __name__ == "__main__":
    main()
