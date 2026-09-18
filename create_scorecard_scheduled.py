import os
import sys
from datetime import date, timedelta
from dotenv import load_dotenv

load_dotenv()

NOTION_TOKEN = os.getenv("NOTION_TOKEN")
NOTION_DB_ID = os.getenv("NOTION_DB_ID")

if not NOTION_TOKEN or not NOTION_DB_ID:
    print("ERROR: Missing NOTION_TOKEN or NOTION_DB_ID in .env")
    sys.exit(1)

today = date(2026, 9, 18)
monday = today - timedelta(days=today.weekday())
friday = monday + timedelta(days=4)
week_num = monday.isocalendar()[1]

title = f"W{week_num} · {monday.day}.{monday.month}–{friday.day}.{friday.month}.{friday.year}"
monday_str = monday.strftime("%Y-%m-%d")

print(f"Creating scorecard: {title}")
print(f"Week starts: {monday_str}")

from notion_client import Client

notion = Client(auth=NOTION_TOKEN)

properties = {
    "Name": {
        "title": [{"text": {"content": title}}]
    },
    "Week": {
        "date": {"start": monday_str}
    },
}

try:
    page = notion.pages.create(
        parent={"database_id": NOTION_DB_ID},
        properties=properties
    )
    print(f"✅ Nový scorecard vytvorený: {title} — vypľ hodnoty v Notion alebo dashboarde.")
    print(f"   Page ID: {page['id']}")
except Exception as e:
    print(f"ERROR: Notion API call failed: {e}")
    sys.exit(1)
