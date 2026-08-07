import os
import datetime
from notion_client import Client
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

NOTION_TOKEN = os.getenv("NOTION_TOKEN")
NOTION_DB_ID = os.getenv("NOTION_DB_ID")

today = datetime.date.today()
monday = today - datetime.timedelta(days=today.weekday())
friday = monday + datetime.timedelta(days=4)
week_num = monday.isocalendar()[1]

title = f"W{week_num} · {monday.day}.{monday.month}–{friday.day}.{friday.month}.{friday.year}"
print(f"Creating scorecard: {title}")
print(f"Monday: {monday}, Friday: {friday}, Week: {week_num}")

notion = Client(auth=NOTION_TOKEN)

properties = {
    "Name": {
        "title": [{"text": {"content": title}}]
    },
    "Week": {
        "date": {"start": monday.isoformat()}
    },
}

result = notion.pages.create(
    parent={"database_id": NOTION_DB_ID},
    properties=properties,
)

page_url = result.get("url", "")
print(f"✅ Nový scorecard vytvorený: {title} — vypľ hodnoty v Notion alebo dashboarde.")
print(f"URL: {page_url}")
