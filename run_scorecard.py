import os
import sys
from datetime import date, timedelta
from dotenv import load_dotenv
from notion_client import Client

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

NOTION_TOKEN = os.environ.get("NOTION_TOKEN")
NOTION_DB_ID = os.environ.get("NOTION_DB_ID")

if not NOTION_TOKEN or not NOTION_DB_ID:
    print("ERROR: Missing NOTION_TOKEN or NOTION_DB_ID in .env")
    sys.exit(1)

today = date(2026, 7, 24)  # Friday
monday = today - timedelta(days=today.weekday())  # weekday() Monday=0 ... Friday=4
friday = monday + timedelta(days=4)

iso_week = monday.isocalendar()[1]

title = f"W{iso_week} · {monday.day}.{monday.month}–{friday.day}.{friday.month}.{friday.year}"

print(f"Creating scorecard: {title}")
print(f"Week: {monday.isoformat()} to {friday.isoformat()}")

notion = Client(auth=NOTION_TOKEN)

number_fields = [
    "KR1_Workshop_Attendees",
    "KR2_LinkedIn_Impressions",
    "KR3_Website_Visitors",
    "KR4_LLM_Platforms",
    "KR5_Media_Mentions",
    "KR6_Employer_Applications",
    "L1_Posts_Published",
    "L2_Post_Avg_Impressions",
    "L3_Workshop_Invites",
    "L4_Partner_Conversations",
    "L5_Case_Studies_Pipeline",
    "L6_Media_Pitches",
    "L7_Speaking_Proposals",
]

text_fields = ["Priority1", "Priority2", "Priority3", "Notes"]

properties = {
    "Name": {"title": [{"text": {"content": title}}]},
    "Week": {"date": {"start": monday.isoformat()}},
}

try:
    response = notion.pages.create(
        parent={"database_id": NOTION_DB_ID},
        properties=properties,
    )
    page_id = response.get("id", "unknown")
    print(f"✅ Nový scorecard vytvorený: {title} — vyplň hodnoty v Notion alebo dashboarde.")
    print(f"   Page ID: {page_id}")
except Exception as e:
    print(f"ERROR: Notion API call failed: {e}")
    sys.exit(1)
