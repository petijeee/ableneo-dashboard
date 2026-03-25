import math
from datetime import date, timedelta
from config import KR_TARGETS, L_TARGETS, STATUS


def calc_percent_to_target(value, kr_key: str) -> float | None:
    """Return % to annual target (0-100+), or None if data missing."""
    if value is None:
        return None
    kr = KR_TARGETS.get(kr_key)
    if not kr:
        return None

    target_type = kr.get("targetType")
    target = kr.get("target")

    if target_type in ("absolute", "ytd"):
        if not target:
            return None
        return round((value / target) * 100)

    if target_type == "yoy":
        baseline = kr.get("baseline")
        if not baseline or not target:
            return None
        return round((value / target) * 100)

    return None


def calc_status(pct) -> dict:
    """Return status dict {emoji, label} based on % to target."""
    if pct is None:
        return {"emoji": "—", "label": "No data"}
    if pct >= STATUS["ON_TRACK"]["minPct"]:
        return STATUS["ON_TRACK"]
    if pct >= STATUS["AT_RISK"]["minPct"]:
        return STATUS["AT_RISK"]
    return STATUS["BEHIND"]


def calc_trend(current, previous, threshold: float = 0.1) -> str:
    """Return ▲, ▼, or → based on change vs previous value."""
    if current is None or previous is None or previous == 0:
        return "→"
    change = (current - previous) / previous
    if change > threshold:
        return "▲"
    if change < -threshold:
        return "▼"
    return "→"


def calc_4week_avg(weeks: list[dict], field: str) -> float | None:
    """Calculate rolling 4-week average for a field (from the end of the list)."""
    last4 = weeks[-4:]
    values = [w[field] for w in last4 if w.get(field) is not None]
    if not values:
        return None
    avg = sum(values) / len(values)
    return round(avg * 10) / 10


def enrich_weeks(weeks: list[dict]) -> list[dict]:
    """Add computed fields (pct, status, trend, avg4) to each week."""
    enriched = []
    for i, week in enumerate(weeks):
        prev = weeks[i - 1] if i > 0 else None
        w = dict(week)

        # Enrich KRs
        for kr_key, kr in KR_TARGETS.items():
            field = kr["field"]
            value = week.get(field)
            prev_value = prev.get(field) if prev else None
            pct = calc_percent_to_target(value, kr_key)
            status = calc_status(pct)
            trend = calc_trend(value, prev_value)
            avg4 = calc_4week_avg(weeks[: i + 1], field)

            w[f"{kr_key}_pct"] = pct
            w[f"{kr_key}_status"] = status["emoji"]
            w[f"{kr_key}_statusLabel"] = status["label"]
            w[f"{kr_key}_trend"] = trend
            w[f"{kr_key}_avg4"] = avg4

        # Enrich Leading Indicators
        for l_key, l in L_TARGETS.items():
            field = l["field"]
            value = week.get(field)
            prev_value = prev.get(field) if prev else None
            target = l.get("target")
            avg4 = calc_4week_avg(weeks[: i + 1], field)
            trend = calc_trend(value, prev_value)

            pct = None
            if value is not None and isinstance(target, (int, float)):
                pct = round((value / target) * 100)

            w[f"{l_key}_pct"] = pct
            w[f"{l_key}_trend"] = trend
            w[f"{l_key}_avg4"] = avg4

        enriched.append(w)
    return enriched


def week_label(week_start_str: str) -> str:
    """Generate week label from a YYYY-MM-DD date string.
    e.g. '2026-03-10' → 'W11 · 9.3–13.3'
    """
    d = date.fromisoformat(week_start_str)
    # Find Monday of that week
    monday = d - timedelta(days=d.weekday())
    friday = monday + timedelta(days=4)
    week_num = monday.isocalendar()[1]
    return f"W{week_num} · {monday.day}.{monday.month}–{friday.day}.{friday.month}"


def current_week_monday() -> str:
    """Return the Monday of the current week as YYYY-MM-DD."""
    today = date.today()
    monday = today - timedelta(days=today.weekday())
    return monday.isoformat()
