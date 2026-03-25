import os
from notion_client import Client
from config import KR_TARGETS, L_TARGETS

_client = None

def get_client():
    global _client
    if _client is None:
        _client = Client(auth=os.environ["NOTION_TOKEN"])
    return _client

def ds_id():
    """Data Source ID — used for querying and creating pages (notion-client v3+)."""
    return os.environ["NOTION_DS_ID"]


def row_to_week(page: dict) -> dict:
    """Convert a Notion page dict to a flat Python dict."""
    props = page["properties"]

    def get_prop(key):
        p = props.get(key)
        if p is None:
            return None
        t = p["type"]
        if t == "number":
            return p["number"]
        if t == "rich_text":
            return "".join(r["plain_text"] for r in p["rich_text"])
        if t == "date":
            return p["date"]["start"] if p["date"] else None
        if t == "title":
            return "".join(r["plain_text"] for r in p["title"])
        return None

    week = {
        "id": page["id"],
        "title": get_prop("Title"),
        "week_start": get_prop("Week"),
    }

    for cfg in KR_TARGETS.values():
        week[cfg["field"]] = get_prop(cfg["field"])
        if "yoyField" in cfg:
            week[cfg["yoyField"]] = get_prop(cfg["yoyField"])

    for cfg in L_TARGETS.values():
        week[cfg["field"]] = get_prop(cfg["field"])

    for text_field in ["Priority1", "Priority2", "Priority3", "Notes"]:
        week[text_field] = get_prop(text_field)

    return week


def get_all_weeks() -> list[dict]:
    """Fetch all DB entries sorted ascending by week_start."""
    client = get_client()
    results = []
    cursor = None

    while True:
        kwargs = {
            "sorts": [{"property": "Week", "direction": "ascending"}],
        }
        if cursor:
            kwargs["start_cursor"] = cursor

        res = client.data_sources.query(ds_id(), **kwargs)
        results.extend(res["results"])

        if res.get("has_more"):
            cursor = res["next_cursor"]
        else:
            break

    return [row_to_week(p) for p in results]


def create_week(week_data: dict) -> dict:
    """Create a new weekly entry in the Notion DB."""
    client = get_client()
    properties = {
        "Title": {"title": [{"text": {"content": week_data.get("title", "")}}]},
        "Week": {"date": {"start": week_data["week_start"]}},
    }

    num_fields = (
        [cfg["field"] for cfg in KR_TARGETS.values()]
        + [cfg["field"] for cfg in L_TARGETS.values()]
    )

    for field in num_fields:
        val = week_data.get(field)
        properties[field] = {"number": val if val is not None else None}

    for text_field in ["Priority1", "Priority2", "Priority3", "Notes"]:
        val = week_data.get(text_field, "") or ""
        properties[text_field] = {"rich_text": [{"text": {"content": val}}]}

    page = client.pages.create(parent={"data_source_id": ds_id()}, properties=properties)
    return row_to_week(page)
