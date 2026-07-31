import os
import sys
from datetime import date, timedelta
from dotenv import load_dotenv
from notion_client import Client

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

token = os.environ.get("NOTION_TOKEN")
db_id = os.environ.get("NOTION_DB_ID")

if not token or not db_id:
    print("ERROR: Missing NOTION_TOKEN or NOTION_DB_ID in .env")
    sys.exit(1)

today = date.today()
monday = today - timedelta(days=today.weekday())
friday = monday + timedelta(days=4)
week_num = monday.isocalendar()[1]

title = f"W{week_num} · {monday.day}.{monday.month}–{friday.day}.{friday.month}.{friday.year}"

notion = Client(auth=token)

properties = {
    "Name": {
        "title": [{"text": {"content": title}}]
    },
    "Week": {
        "date": {"start": monday.isoformat()}
    },
}

number_fields = [
    "KR1_Workshop_Attendees", "KR2_LinkedIn_Impressions", "KR3_Website_Visitors",
    "KR4_LLM_Platforms", "KR5_Media_Mentions", "KR6_Employer_Applications",
    "L1_Posts_Published", "L2_Post_Avg_Impressions", "L3_Workshop_Invites",
    "L4_Partner_Conversations", "L5_Case_Studies_Pipeline", "L6_Media_Pitches",
    "L7_Speaking_Proposals"
]
for field in number_fields:
    properties[field] = {"number": None}

text_fields = ["Priority1", "Priority2", "Priority3", "Notes"]
for field in text_fields:
    properties[field] = {"rich_text": []}

try:
    page = notion.pages.create(
        parent={"database_id": db_id},
        properties=properties,
    )
    print(f"✅ Nový scorecard vytvorený: {title} — vypľ hodnoty v Notion alebo dashboarde.")
except Exception as e:
    print(f"ERROR creating Notion page: {e}")
    sys.exit(1)
