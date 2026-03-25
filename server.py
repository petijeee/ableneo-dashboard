#!/usr/bin/env python3
"""Weekly Marketing Scorecard Dashboard — Python/Flask backend"""

import os
import sys
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()

import calendar
from flask import Flask, jsonify, request, send_from_directory
from api.notion_client import get_all_weeks, create_week
from api.compute_utils import enrich_weeks, week_label, current_week_monday
from config import KR_TARGETS, L_TARGETS

app = Flask(__name__, static_folder="public", static_url_path="")


# ── API routes ────────────────────────────────────────────────────

@app.get("/api/data")
def api_data():
    try:
        weeks = get_all_weeks()
        enriched = enrich_weeks(weeks)
        return jsonify({"ok": True, "weeks": enriched})
    except Exception as e:
        print(f"GET /api/data error: {e}", file=sys.stderr)
        return jsonify({"ok": False, "error": str(e)}), 500


@app.get("/api/config")
def api_config():
    return jsonify({"ok": True, "KR_TARGETS": KR_TARGETS, "L_TARGETS": L_TARGETS})


@app.post("/api/weeks")
def api_create_week():
    try:
        body = request.get_json(silent=True) or {}
        week_start = body.get("week_start") or current_week_monday()
        title = body.get("title") or week_label(week_start)

        week_data = {"week_start": week_start, "title": title, **body}
        week = create_week(week_data)
        return jsonify({"ok": True, "week": week}), 201
    except Exception as e:
        print(f"POST /api/weeks error: {e}", file=sys.stderr)
        return jsonify({"ok": False, "error": str(e)}), 500


@app.get("/api/monthly")
def api_monthly():
    try:
        from datetime import date
        weeks = get_all_weeks()

        months_dict = {}
        for week in weeks:
            ws = week.get("week_start")
            if not ws:
                continue
            d = date.fromisoformat(ws)
            mk = f"{d.year}-{d.month:02d}"
            if mk not in months_dict:
                months_dict[mk] = {
                    "monthKey": mk,
                    "title": f"{calendar.month_abbr[d.month]} {d.year}",
                    "isMonthly": True,
                    "weeks": [],
                }
            months_dict[mk]["weeks"].append(week)

        months = []
        for mk in sorted(months_dict.keys()):
            entry = months_dict[mk]
            ws = entry["weeks"]
            agg = {"monthKey": mk, "title": entry["title"], "isMonthly": True}
            for cfg in KR_TARGETS.values():
                field = cfg["field"]
                vals = [w[field] for w in ws if w.get(field) is not None]
                agg[field] = sum(vals) if vals else None
            for cfg in L_TARGETS.values():
                field = cfg["field"]
                vals = [w[field] for w in ws if w.get(field) is not None]
                agg[field] = sum(vals) if vals else None
            months.append(agg)

        enriched = enrich_weeks(months)
        return jsonify({"ok": True, "months": enriched})
    except Exception as e:
        print(f"GET /api/monthly error: {e}", file=sys.stderr)
        return jsonify({"ok": False, "error": str(e)}), 500


@app.get("/api/health")
def api_health():
    return jsonify({
        "ok": True,
        "notion_configured": bool(
            os.environ.get("NOTION_TOKEN") and os.environ.get("NOTION_DB_ID")
        ),
    })


# ── Serve frontend ────────────────────────────────────────────────

@app.get("/")
def serve_index():
    return send_from_directory("public", "index.html")


# ── Entry point ───────────────────────────────────────────────────

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 3000))
    token = os.environ.get("NOTION_TOKEN")
    db_id = os.environ.get("NOTION_DB_ID")

    if not token or not db_id:
        print("⚠️  NOTION_TOKEN alebo NOTION_DB_ID nie je nastavené")
        print("   Skopíruj .env.example do .env a vyplň hodnoty")
        print()

    print(f"Dashboard beží → http://localhost:{port}")
    app.run(host="0.0.0.0", port=port, debug=False)
