import os
import datetime
from dotenv import load_dotenv
from notion_client import Client

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

token = os.environ["NOTION_TOKEN"]
db_id = os.environ["NOTION_DB_ID"]

today = datetime.date(2026, 6, 26)
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
        "date": {"start": monday.strftime("%Y-%m-%d")}
    },
}

result = notion.pages.create(
    parent={"database_id": db_id},
    properties=properties,
)

print(f"✅ Nový scorecard vytvorený: {title} — vypľ hodnoty v Notion alebo dashboarde.")
print(f"   Page ID: {result['id']}")
print(f"   URL: {result.get('url', 'N/A')}")
