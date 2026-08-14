import os
import datetime
from dotenv import load_dotenv
from notion_client import Client

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), ".env"))

token = os.environ.get("NOTION_TOKEN")
db_id = os.environ.get("NOTION_DB_ID")

if not token or not db_id:
    raise ValueError("NOTION_TOKEN or NOTION_DB_ID not set in .env")

today = datetime.date(2026, 8, 14)
monday = today - datetime.timedelta(days=today.weekday())
friday = monday + datetime.timedelta(days=4)
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

try:
    page = notion.pages.create(
        parent={"database_id": db_id},
        properties=properties,
    )
    print(f"✅ Nový scorecard vytvorený: {title} — vypľ hodnoty v Notion alebo dashboarde.")
except Exception as e:
    print(f"❌ Chyba pri vytváraní scorecardу: {e}")
    raise
