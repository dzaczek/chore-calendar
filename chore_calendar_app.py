from copy import deepcopy
from datetime import date
import json
import re

from flask import Flask, render_template_string

app = Flask(__name__)


@app.after_request
def security_headers(response):
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    response.headers["Content-Security-Policy"] = (
        "default-src 'none'; "
        "script-src 'unsafe-inline' 'unsafe-eval' https://cdn.jsdelivr.net; "
        "style-src 'unsafe-inline'; "
        "connect-src 'self' blob: https://cdn.jsdelivr.net; "
        "img-src 'self' data: blob:; "
        "worker-src blob:; "
        "form-action 'self'; "
        "base-uri 'self'; "
        "frame-ancestors 'none'"
    )
    response.headers["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains; preload"
    return response

DAYS = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
PERIODS = ["daily", "weekly", "monthly", "custom"]
DEFAULT_CATEGORY_COLORS = {
    "daily": "#9fc9af",
    "weekly": "#a8c8d8",
    "monthly": "#d8b0d2",
    "custom": "#c3d4a2",
}

DEFAULT_DATA = {
    "settings": {
        "title": "Chore Planner",
        "people": ["Jacek", "Alex", "Mia"],
        "view_year": 2026,
        "view_month": 3,
        "category_colors": deepcopy(DEFAULT_CATEGORY_COLORS),
        "custom_periods": [],
        "week_start": "sunday",
    },
    "tasks": [
        {
            "id": "task-1",
            "title": "Kitchen Counter",
            "period": "daily",
            "day": "",
            "icon": "KC",
        },
        {
            "id": "task-2",
            "title": "Vacuum",
            "period": "weekly",
            "day": "Friday",
            "icon": "V",
        },
        {
            "id": "task-3",
            "title": "Fridge Check",
            "period": "monthly",
            "day": "Saturday",
            "icon": "F",
        },
        {
            "id": "task-4",
            "title": "Deep Clean",
            "period": "custom",
            "day": "",
            "icon": "DC",
            "placements": [],
        },
    ],
}


def default_icon(title):
    compact = "".join(part[0] for part in title.split()[:2]).upper()
    return compact or "?"


def normalize_month_date(value):
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return None

    return min(31, max(1, parsed))


def normalize_hex_color(value, fallback):
    candidate = str(value or "").strip()
    if re.fullmatch(r"#[0-9a-fA-F]{6}", candidate):
        return candidate.lower()
    return fallback


def normalize_category_colors(raw_colors):
    candidate = raw_colors if isinstance(raw_colors, dict) else {}
    return {
        period: normalize_hex_color(candidate.get(period), default)
        for period, default in DEFAULT_CATEGORY_COLORS.items()
    }


def normalize_task(task, index):
    title = str(task.get("title") or f"Task {index + 1}").strip()
    raw_period = str(task.get("period") or task.get("frequency") or task.get("category") or "weekly").lower()
    legacy_map = {
        "daily": "daily",
        "weekly": "weekly",
        "monthly": "monthly",
        "quarterly": "custom",
        "custom": "custom",
    }
    period = legacy_map.get(raw_period, raw_period if raw_period.startswith("every_") else "weekly")
    day = str(task.get("day") or "").strip()
    if period in ("daily", "custom"):
        day = ""
    elif day not in DAYS:
        day = DAYS[0]

    month_date = (
        normalize_month_date(task.get("month_date"))
        or normalize_month_date(task.get("monthDate"))
        or normalize_month_date(task.get("date_number"))
        or normalize_month_date(task.get("dateNumber"))
    )
    if period not in {"monthly"}:
        month_date = None

    icon = str(task.get("icon") or "").strip() or default_icon(title)

    result = {
        "id": str(task.get("id") or f"task-{index + 1}"),
        "title": title,
        "period": period,
        "day": day,
        "month_date": month_date,
        "icon": icon[:4],
    }
    if period == "custom":
        placements = task.get("placements") if isinstance(task.get("placements"), list) else []
        result["placements"] = placements
    return result


def normalize_data(raw_data):
    if not isinstance(raw_data, dict):
        return deepcopy(DEFAULT_DATA)

    settings = raw_data.get("settings") or {}
    old_people = settings.get("people")
    old_assignees = settings.get("assignees")
    people = old_people if isinstance(old_people, list) else old_assignees if isinstance(old_assignees, list) else []
    people = [str(person).strip() for person in people if str(person).strip()]

    tasks = raw_data.get("tasks") if isinstance(raw_data.get("tasks"), list) else []
    today = date.today()
    normalized = {
        "settings": {
            "title": str(settings.get("title") or DEFAULT_DATA["settings"]["title"]).strip(),
            "people": people or deepcopy(DEFAULT_DATA["settings"]["people"]),
            "view_year": int(settings.get("view_year") or today.year),
            "view_month": int(settings.get("view_month") or today.month),
            "category_colors": normalize_category_colors(
                settings.get("category_colors") or settings.get("categoryColors")
            ),
            "custom_periods": settings.get("custom_periods") if isinstance(settings.get("custom_periods"), list) else [],
            "week_start": settings.get("week_start") if settings.get("week_start") in ("sunday", "monday") else "sunday",
        },
        "tasks": [normalize_task(task, index) for index, task in enumerate(tasks)],
    }

    normalized["settings"]["view_month"] = min(12, max(1, normalized["settings"]["view_month"]))
    normalized["settings"]["view_year"] = min(2100, max(2000, normalized["settings"]["view_year"]))

    if not normalized["tasks"]:
        normalized["tasks"] = deepcopy(DEFAULT_DATA["tasks"])

    return normalized


def _render(print_mode):
    return render_template_string(
        TEMPLATE,
        initial_data=json.dumps(deepcopy(DEFAULT_DATA)),
        days=DAYS,
        periods=PERIODS,
        default_category_colors=DEFAULT_CATEGORY_COLORS,
        print_mode=print_mode,
    )


@app.route("/")
def index():
    return _render(False)


@app.route("/print")
def print_view():
    return _render(True)




TEMPLATE = r"""
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Chore Planner</title>
  <script src="https://cdn.jsdelivr.net/npm/sortablejs@1.15.2/Sortable.min.js"></script>
  <script src="https://cdn.jsdelivr.net/npm/lz-string@1.5.0/libs/lz-string.min.js"></script>
  <script src="https://cdn.jsdelivr.net/npm/qrcode-generator@1.4.4/qrcode.min.js"></script>
  <script src="https://cdn.jsdelivr.net/npm/html2pdf.js@0.10.2/dist/html2pdf.bundle.min.js"></script>
  <style>
    :root {
      --bg: #eef1ea;
      --bg-accent: #f7faf4;
      --card: rgba(255, 255, 255, 0.86);
      --line: #b9c4ba;
      --text: #26312a;
      --muted: #657166;
      --accent: #476f5b;
      --accent-strong: #385848;
      --chip: #edf4ec;
      --daily: #9fc9af;

      --weekly: #a8c8d8;
      --monthly: #d8b0d2;
      --custom: #c3d4a2;
      --shadow: 0 18px 42px rgba(69, 45, 20, 0.12);
      --radius: 20px;
    }

    * { box-sizing: border-box; }

    body {
      margin: 0;
      min-height: 100vh;
      color: var(--text);
      font-family: "Avenir Next", "Trebuchet MS", sans-serif;
      background:
        radial-gradient(circle at top left, rgba(255,255,255,0.75), transparent 32%),
        linear-gradient(135deg, var(--bg), var(--bg-accent));
    }

    body.modal-open {
      overflow: hidden;
    }

    button, input, select {
      font: inherit;
    }

    .page {
      max-width: 1600px;
      margin: 0 auto;
      padding: 24px;
      display: grid;
      grid-template-columns: 128px minmax(0, 1fr);
      gap: 24px;
      align-items: start;
    }

    .panel, .board {
      background: var(--card);
      border: 1px solid rgba(136, 108, 72, 0.16);
      border-radius: var(--radius);
      box-shadow: var(--shadow);
      backdrop-filter: blur(10px);
    }

    .panel {
      padding: 14px;
      position: sticky;
      top: 24px;
      display: grid;
      gap: 12px;
    }

    .board {
      padding: 16px;
      overflow: auto;
      background: rgba(255, 255, 255, 0.72);
      min-height: calc(100vh - 48px);
    }

    .print-sheet {
      width: 290mm;
      min-height: 190mm;
      margin: 0 auto;
      padding: 4mm;
      background: white;
      border: none;
      box-shadow: none;
    }

    h1, h2, h3, p {
      margin: 0;
    }

    .eyebrow {
      display: inline-flex;
      align-items: center;
      gap: 8px;
      margin-bottom: 12px;
      padding: 5px 10px;
      border-radius: 999px;
      background: rgba(245, 238, 228, 0.95);
      color: var(--muted);
      font-size: 11px;
      font-weight: 700;
      letter-spacing: 0.08em;
      text-transform: uppercase;
    }

    .panel-title {
      font-size: 18px;
      line-height: 1.1;
    }

    .subtle {
      color: var(--muted);
      font-size: 12px;
      line-height: 1.4;
    }

    .section {
      margin-top: 18px;
      padding-top: 18px;
      border-top: 1px solid rgba(136, 108, 72, 0.14);
    }

    .section:first-of-type {
      margin-top: 0;
      padding-top: 0;
      border-top: 0;
    }

    .section-head {
      display: flex;
      align-items: start;
      justify-content: space-between;
      gap: 14px;
    }

    .section-copy {
      display: grid;
      gap: 6px;
    }

    .field {
      margin-top: 12px;
    }

    .field label {
      display: block;
      margin-bottom: 6px;
      font-size: 13px;
      font-weight: 700;
      color: var(--muted);
    }

    input[type="text"], select {
      width: 100%;
      border: 1px solid var(--line);
      border-radius: 14px;
      padding: 11px 12px;
      color: var(--text);
      background: rgba(255,255,255,0.82);
    }

    .row {
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 10px;
    }

    .button-row {
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
      margin-top: 16px;
    }

    .settings-actions {
      align-items: stretch;
    }

    button {
      border: 0;
      border-radius: 14px;
      padding: 11px 14px;
      font-weight: 800;
      cursor: pointer;
      color: white;
      background: var(--accent);
      transition: transform 120ms ease, background 120ms ease;
    }

    button:hover {
      transform: translateY(-1px);
      background: var(--accent-strong);
    }

    button.secondary {
      background: #eadcc7;
      color: var(--text);
    }

    button.secondary:hover {
      background: #e2d0b5;
    }

    .action-button {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      gap: 8px;
    }

    .action-button svg {
      width: 16px;
      height: 16px;
      flex-shrink: 0;
    }

    .settings-save {
      flex: 1 1 170px;
    }

    .action-rail {
      display: grid;
      gap: 10px;
    }

    .rail-button {
      width: 100%;
      min-height: 76px;
      padding: 12px 8px;
      border-radius: 18px;
      display: grid;
      justify-items: center;
      gap: 8px;
      text-align: center;
    }

    .rail-button svg {
      width: 22px;
      height: 22px;
      flex-shrink: 0;
    }

    .rail-button span {
      font-size: 11px;
      line-height: 1.05;
    }

    .task-modal[hidden], .settings-modal[hidden] {
      display: none !important;
    }

    .task-modal, .settings-modal {
      position: fixed;
      inset: 0;
      z-index: 1000;
      padding: 24px;
      display: flex;
      align-items: center;
      justify-content: center;
      background: rgba(28, 37, 31, 0.42);
      backdrop-filter: blur(8px);
    }

    .task-modal-card, .settings-modal-card {
      width: min(100%, 480px);
      max-height: calc(100vh - 48px);
      overflow: auto;
      padding: 20px;
      border-radius: 24px;
      border: 1px solid rgba(136, 108, 72, 0.16);
      background: rgba(255, 255, 255, 0.96);
      box-shadow: var(--shadow);
    }

    .task-modal-head, .settings-modal-head {
      display: flex;
      align-items: start;
      justify-content: space-between;
      gap: 16px;
    }

    .task-modal-title, .settings-modal-title {
      font-size: 24px;
      line-height: 1;
    }

    .task-modal-close, .settings-modal-close {
      flex-shrink: 0;
    }

    .task-form, .settings-form {
      margin-top: 10px;
    }

    .board-head {
      display: flex;
      justify-content: space-between;
      align-items: end;
      gap: 16px;
      margin-bottom: 8px;
      padding-bottom: 6px;
      border-bottom: 1px solid rgba(101, 113, 102, 0.2);
    }

    .board-title {
      font-size: clamp(18px, 2.4vw, 26px);
      line-height: 1;
      letter-spacing: -0.02em;
    }

    .board-meta {
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
      justify-content: flex-end;
    }

    .meta-chip {
      padding: 4px 8px;
      border-radius: 4px;
      border: 1px solid var(--line);
      background: #fff;
      color: var(--muted);
      font-size: 11px;
      font-weight: 700;
    }

    .layout {
      display: grid;
      grid-template-columns: minmax(0, 1fr) minmax(0, 240px);
      gap: 12px;
      align-items: stretch;
    }

    .stack {
      display: flex;
      flex-direction: column;
      gap: 12px;
      min-width: 0;
      min-height: 100%;
    }

    .surface {
      border: 1px solid rgba(101, 113, 102, 0.18);
      border-radius: 6px;
      padding: 12px;
      background: rgba(255, 255, 255, 0.78);
      min-width: 0;
    }

    .calendar-surface {
      padding-top: 10px;
      display: flex;
      flex-direction: column;
      min-height: 100%;
    }

    .legend-surface {
      padding: 8px;
      background: rgba(247, 250, 244, 0.86);
      display: flex;
      flex-direction: column;
      min-height: 100%;
    }

    .surface h3 {
      margin-bottom: 2px;
      font-size: 14px;
    }

    .surface-note {
      margin-bottom: 6px;
      color: var(--muted);
      font-size: 11px;
    }

    .period-switcher {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      margin-bottom: 14px;
    }

    .period-pill {
      border: 1px solid var(--line);
      background: #fff;
      color: var(--muted);
      border-radius: 4px;
      padding: 7px 10px;
      font-size: 12px;
      font-weight: 800;
      cursor: pointer;
    }

    .period-pill.active {
      background: var(--accent);
      border-color: var(--accent);
      color: white;
    }

    .calendar-grid {
      display: grid;
      grid-template-columns: repeat(7, minmax(80px, 1fr));
      gap: 4px;
      overflow: visible;
      padding-bottom: 4px;
      grid-auto-rows: 1fr;
      flex: 1;
      min-height: 500px;
    }

    .day-column {
      min-width: 0;
      display: flex;
      flex-direction: column;
      border: 1px solid rgba(136, 108, 72, 0.16);
      border-radius: 4px;
      background: rgba(255, 255, 255, 0.64);
      overflow: hidden;
      min-height: 0;
    }

    .day-head {
      padding: 6px 7px;
      border-bottom: 1px solid rgba(101, 113, 102, 0.14);
      background: rgba(240, 245, 239, 0.92);
    }

    .month-cell .day-head {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 6px;
    }

    .day-name {
      font-weight: 900;
      font-size: 11px;
      line-height: 1;
    }

    .day-note {
      margin-top: 0;
      color: var(--muted);
      font-size: 10px;
      line-height: 1;
    }

    .day-dropzone {
      min-height: 0;
      padding: 6px;
      display: flex;
      flex-wrap: wrap;
      align-content: flex-start;
      gap: 5px;
      flex: 1;
    }

    .month-cell .day-dropzone {
      min-height: 0;
    }

    .empty-month-cell {
      background: #fbf9f5;
    }

    .empty-cell {
      min-height: 110px;
      background: transparent;
    }

    .calendar-dot {
      width: 24px;
      height: 24px;
      border-radius: 999px;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      color: #fff;
      font-size: 8px;
      font-weight: 900;
      letter-spacing: 0.03em;
      box-shadow: inset 0 0 0 1px rgba(255,255,255,0.45);
      cursor: grab;
    }

    .calendar-dot.daily { background: var(--daily); color: #1c3a25; }

    .calendar-dot.weekly { background: var(--weekly); color: #173747; }
    .calendar-dot.monthly { background: var(--monthly); color: #4c2448; }
    .calendar-dot.custom { background: var(--custom); color: #33441c; cursor: pointer; }

    .legend-groups {
      display: grid;
      grid-template-columns: 1fr;
      gap: 6px;
      flex: 1;
    }

    .legend-group {
      border: 1px solid rgba(101, 113, 102, 0.18);
      background: rgba(255,255,255,0.9);
    }

    .legend-head {
      padding: 6px 7px;
      font-size: 10px;
      font-weight: 900;
      text-transform: uppercase;
      letter-spacing: 0.08em;
      border-bottom: 1px solid rgba(101, 113, 102, 0.14);
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 8px;
    }

    .legend-head.daily { background: #d5e8dc; }

    .legend-head.weekly { background: #d9e7ef; }
    .legend-head.monthly { background: #efdceb; }
    .legend-head.custom { background: #dfe7d5; }

    .legend-head-title {
      min-width: 0;
    }

    .legend-head-actions {
      display: inline-flex;
      align-items: center;
      gap: 4px;
    }

    .legend-color-button {
      width: 18px;
      height: 18px;
      padding: 0;
      border-radius: 999px;
      border: 1px solid rgba(38, 49, 42, 0.18);
      display: inline-flex;
      align-items: center;
      justify-content: center;
      font-size: 9px;
      line-height: 1;
      color: var(--text);
      background: #fff;
    }

    .legend-color-button.daily { background: var(--daily); color: #1c3a25; }

    .legend-color-button.weekly { background: var(--weekly); color: #173747; }
    .legend-color-button.monthly { background: var(--monthly); color: #4c2448; }
    .legend-color-button.custom { background: var(--custom); color: #33441c; }

    button.legend-color-button:hover {
      transform: translateY(-1px);
    }

    button.legend-color-button.daily:hover { background: var(--daily); }

    button.legend-color-button.weekly:hover { background: var(--weekly); }
    button.legend-color-button.monthly:hover { background: var(--monthly); }
    button.legend-color-button.custom:hover { background: var(--custom); }

    .legend-color-input {
      position: absolute;
      width: 0;
      height: 0;
      opacity: 0;
      pointer-events: none;
    }

    .legend-list {
      padding: 6px 7px 7px;
      display: flex;
      flex-direction: column;
      gap: 3px;
    }

    .legend-item {
      display: grid;
      grid-template-columns: 20px 1fr;
      gap: 4px;
      align-items: start;
    }

    .legend-item.is-draggable {
      cursor: grab;
    }

    .legend-item.is-draggable:active {
      cursor: grabbing;
    }

    .legend-icon {
      width: 16px;
      height: 16px;
      border-radius: 999px;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      font-size: 7px;
      font-weight: 900;
    }

    .legend-icon.daily { background: var(--daily); color: #1c3a25; }

    .legend-icon.weekly { background: var(--weekly); color: #173747; }
    .legend-icon.monthly { background: var(--monthly); color: #4c2448; }
    .legend-icon.custom { background: var(--custom); color: #33441c; }

    .legend-copy {
      min-width: 0;
    }

    .legend-top {
      display: grid;
      grid-template-columns: minmax(0, 1fr) auto;
      gap: 4px;
      align-items: start;
    }

    .legend-title {
      font-size: 9px;
      font-weight: 800;
      line-height: 1.1;
      word-break: break-word;
    }

    .legend-sub {
      margin-top: 1px;
      font-size: 8px;
      color: var(--muted);
    }

    .legend-actions {
      display: flex;
      gap: 3px;
      cursor: default;
    }

    .icon-action {
      width: 16px;
      height: 16px;
      padding: 0;
      border-radius: 999px;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      font-size: 8px;
      line-height: 1;
      cursor: pointer;
    }

    .help-tooltip {
      position: absolute;
      z-index: 900;
      width: 220px;
      padding: 10px 12px;
      border-radius: 10px;
      background: rgba(255,255,255,0.97);
      border: 1px solid rgba(136,108,72,0.2);
      box-shadow: 0 8px 24px rgba(0,0,0,0.15);
      font-size: 12px;
      line-height: 1.5;
      color: #333;
      pointer-events: auto;
    }

    .help-tooltip::before {
      content: "";
      position: absolute;
      top: -6px;
      right: 14px;
      width: 10px;
      height: 10px;
      background: rgba(255,255,255,0.97);
      border-top: 1px solid rgba(136,108,72,0.2);
      border-left: 1px solid rgba(136,108,72,0.2);
      transform: rotate(45deg);
    }

    .task-actions {
      margin-top: 8px;
      display: flex;
      gap: 6px;
    }

    .task-actions button {
      flex: 1;
      padding: 7px 9px;
      font-size: 12px;
    }

    .empty {
      padding: 16px;
      border: 1px dashed rgba(136, 108, 72, 0.3);
      border-radius: 14px;
      color: var(--muted);
      text-align: center;
      font-size: 13px;
      background: rgba(255,255,255,0.44);
    }

    .helper {
      margin-top: 12px;
      color: var(--muted);
      font-size: 12px;
      line-height: 1.45;
    }

    .qr-page {
      display: none;
    }

    .print-line {
      margin-top: 10px;
      display: grid;
      grid-template-columns: 1.2fr 0.8fr;
      gap: 10px;
      font-size: 12px;
      color: var(--muted);
    }

    .print-slot {
      border-bottom: 1px solid rgba(111, 101, 88, 0.55);
      height: 24px;
      display: flex;
      align-items: end;
      white-space: nowrap;
    }

    .sheet-note {
      margin-top: 10px;
      padding-top: 10px;
      border-top: 1px dashed rgba(136, 108, 72, 0.22);
      color: var(--muted);
      font-size: 12px;
      line-height: 1.4;
    }

    @media print {
      html, body, * {
        -webkit-print-color-adjust: exact !important;
        print-color-adjust: exact !important;
      }

      html, body {
        margin: 0;
        padding: 0;
        background: white;
        width: 100%;
        height: 100%;
      }

      *, *::before, *::after {
        box-sizing: border-box;
      }

      .page {
        display: block;
        max-width: none;
        margin: 0;
        padding: 0;
        width: 100%;
        height: 100%;
      }

      .panel {
        display: none !important;
      }

      .board {
        border: 0;
        box-shadow: none;
        margin: 0;
        padding: 0;
        background: white;
        width: 100%;
        height: 100%;
        min-height: 0;
        overflow: hidden;
      }

      .print-sheet {
        width: 100%;
        height: 100%;
        margin: 0;
        padding: 0;
        border: 0;
        box-shadow: none;
        display: flex;
        flex-direction: column;
        overflow: hidden;
      }

      .eyebrow, .period-switcher, .task-actions, .sheet-note, footer, .help-button, .board-intro {
        display: none !important;
      }

      .board-head {
        margin: 0 0 1mm 0;
        padding: 0 0 1mm 0;
        align-items: center;
        border-bottom-color: #ccc;
        flex: 0 0 auto;
      }

      .board-title {
        font-size: 11pt;
        letter-spacing: 0;
      }

      .meta-chip {
        background: white;
        border-color: #ccc;
        color: #333;
        font-size: 6pt;
        padding: 1px 4px;
      }

      .layout {
        display: flex;
        flex: 1 1 0;
        width: 100%;
        gap: 1mm;
        min-height: 0;
        overflow: hidden;
      }

      .layout > * {
        min-width: 0;
        min-height: 0;
      }

      .stack {
        flex: 1 1 0;
        min-width: 0;
        min-height: 0;
        display: flex;
        flex-direction: column;
        overflow: hidden;
      }

      .surface {
        border: none;
        border-radius: 0;
        background: white;
        padding: 0;
      }

      .calendar-surface, .legend-surface {
        padding: 0;
        min-height: 0;
        overflow: hidden;
      }

      .calendar-surface {
        background: white;
        flex: 1 1 0;
        display: flex;
        flex-direction: column;
        min-height: 0;
      }

      .legend-surface {
        background: white;
        flex: 0 0 auto;
        width: 18%;
        overflow: hidden;
      }

      .calendar-grid {
        flex: 1 1 0;
        grid-template-columns: repeat(7, 1fr);
        gap: 0.5mm;
        overflow: hidden;
        grid-auto-rows: minmax(0, 1fr);
        align-content: stretch;
        min-height: 0;
        width: 100%;
      }

      .day-column {
        min-width: 0;
        border-color: #b8b8b8;
        border-radius: 0;
        overflow: hidden;
      }

      .day-head {
        background: white;
        padding: 0.5mm 0.8mm;
      }

      .day-name {
        font-size: 6.5pt;
      }

      .day-note {
        font-size: 6.5pt;
        font-weight: 800;
        color: #333;
      }

      .day-dropzone {
        min-height: 0;
        padding: 0.5mm;
        gap: 0.4mm;
      }

      .month-cell .day-dropzone, .empty-cell {
        min-height: 0;
      }

      .calendar-dot {
        width: 3.8mm;
        height: 3.8mm;
        font-size: 3.8pt;
        box-shadow: none;
      }

      .legend-groups {
        flex: 1 1 auto;
        width: 100%;
        gap: 0.7mm;
        grid-auto-rows: max-content;
        align-content: start;
        min-height: 0;
      }

      .legend-group {
        break-inside: avoid;
        page-break-inside: avoid;
      }

      .legend-head {
        padding: 0.6mm 0.8mm;
        font-size: 5pt;
      }

      .legend-list {
        padding: 0.5mm 0.7mm;
        gap: 0.3mm;
      }

      .legend-item {
        grid-template-columns: 3.5mm 1fr;
        gap: 0.4mm;
      }

      .legend-icon {
        width: 3.2mm;
        height: 3.2mm;
        font-size: 3.2pt;
      }

      .legend-title {
        font-size: 4.5pt;
        line-height: 1.05;
      }

      .legend-sub {
        font-size: 3.8pt;
      }

      .icon-action {
        width: 3.8mm;
        height: 3.8mm;
        font-size: 4pt;
      }

      .legend-actions {
        display: none !important;
      }

      .legend-head-actions {
        display: none !important;
      }

      .sheet-note {
        display: none !important;
      }

      .qr-page {
        display: block;
        page-break-before: always;
        width: 100%;
        text-align: center;
        padding-top: 5mm;
        overflow: hidden;
      }

      .qr-content {
        display: inline-block;
      }

      .qr-title {
        font-size: 14pt;
        margin: 0 0 4mm 0;
        color: #333;
      }

      #qrCodeContainer {
        display: inline-block;
        padding: 3mm;
        border: 1px solid #ccc;
        border-radius: 3mm;
        background: white;
      }

      #qrCodeContainer svg {
        display: block;
        max-width: 120mm;
        max-height: 120mm;
        width: auto;
        height: auto;
      }

      .qr-desc {
        max-width: 300px;
        margin: 4mm auto 0;
        font-size: 9pt;
        line-height: 1.4;
        color: #666;
      }

      .qr-error {
        max-width: 300px;
        margin: 4mm auto 0;
        font-size: 9pt;
        color: #c33;
      }

      @page {
        size: A4 landscape;
        margin: 3mm;
      }
    }

    body.print-mode {
      background: white;
    }

    body.print-mode .page {
      grid-template-columns: 1fr;
      max-width: none;
      padding: 16px;
    }

    body.print-mode .panel {
      display: none !important;
    }

    body.print-mode .board {
      border: 0;
      box-shadow: none;
      background: transparent;
      min-height: 0;
      padding: 0;
      overflow: auto;
    }

    body.print-mode .task-modal, body.print-mode .settings-modal {
      display: none !important;
    }

    @media (max-width: 1180px) {
      .page {
        grid-template-columns: 1fr;
      }

      .panel {
        position: static;
      }

      .action-rail {
        grid-template-columns: repeat(4, minmax(0, 1fr));
      }

      .layout {
        grid-template-columns: 1fr;
      }
    }

    @media (max-width: 720px) {
      .page {
        padding: 14px;
      }

      .board, .panel {
        padding: 16px;
      }

      .row {
        grid-template-columns: 1fr;
      }

      .board-head {
        flex-direction: column;
        align-items: start;
      }

      .board-meta {
        justify-content: start;
      }

      .task-modal, .settings-modal {
        padding: 12px;
      }

      .task-modal-card, .settings-modal-card {
        max-height: calc(100vh - 24px);
        padding: 16px;
        border-radius: 18px;
      }
    }
  </style>
</head>
<body class="{{ 'print-mode' if print_mode else 'screen-mode' }}">
  <div class="page">
    <aside class="panel">
      <div class="eyebrow">Menu</div>
      <h1 class="panel-title">Chore Planner</h1>
      <p class="subtle">No inputs stay here. Settings and tasks open from popup menus behind the icons.</p>

      <div class="action-rail">
        <button type="button" class="rail-button secondary" onclick="openSettingsModal()" title="Settings">
          <svg viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
            <circle cx="12" cy="12" r="3.25" />
            <path d="M19.4 15a1 1 0 0 0 .2 1.1l.1.1a1 1 0 0 1 0 1.4l-1.2 1.2a1 1 0 0 1-1.4 0l-.1-.1a1 1 0 0 0-1.1-.2 1 1 0 0 0-.6.9V20a1 1 0 0 1-1 1h-1.7a1 1 0 0 1-1-1v-.2a1 1 0 0 0-.7-.9 1 1 0 0 0-1.1.2l-.1.1a1 1 0 0 1-1.4 0l-1.2-1.2a1 1 0 0 1 0-1.4l.1-.1a1 1 0 0 0 .2-1.1 1 1 0 0 0-.9-.6H4a1 1 0 0 1-1-1v-1.7a1 1 0 0 1 1-1h.2a1 1 0 0 0 .9-.7 1 1 0 0 0-.2-1.1l-.1-.1a1 1 0 0 1 0-1.4l1.2-1.2a1 1 0 0 1 1.4 0l.1.1a1 1 0 0 0 1.1.2 1 1 0 0 0 .6-.9V4a1 1 0 0 1 1-1h1.7a1 1 0 0 1 1 1v.2a1 1 0 0 0 .7.9 1 1 0 0 0 1.1-.2l.1-.1a1 1 0 0 1 1.4 0l1.2 1.2a1 1 0 0 1 0 1.4l-.1.1a1 1 0 0 0-.2 1.1 1 1 0 0 0 .9.6H20a1 1 0 0 1 1 1v1.7a1 1 0 0 1-1 1h-.2a1 1 0 0 0-.9.7z" />
          </svg>
          <span>Settings</span>
        </button>
        <button type="button" class="rail-button secondary" onclick="openPrintView()" title="Print">
          <svg viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
            <path d="M7 9V4h10v5" />
            <path d="M6 18H5a2 2 0 0 1-2-2v-5a3 3 0 0 1 3-3h12a3 3 0 0 1 3 3v5a2 2 0 0 1-2 2h-1" />
            <path d="M7 14h10v6H7z" />
            <path d="M17 11h.01" />
          </svg>
          <span>Print</span>
        </button>
        <button type="button" class="rail-button secondary" onclick="exportPdf()" title="Save as PDF">
          <svg viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
            <path d="M14 3v4a1 1 0 0 0 1 1h4" />
            <path d="M5 3h9l5 5v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2z" />
            <path d="M9 17h6" />
            <path d="M9 13h6" />
          </svg>
          <span>PDF</span>
        </button>
        <button type="button" class="rail-button secondary" onclick="shareLink()" title="Share link">
          <svg viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
            <circle cx="18" cy="5" r="3"/>
            <circle cx="6" cy="12" r="3"/>
            <circle cx="18" cy="19" r="3"/>
            <path d="M8.59 13.51l6.83 3.98"/>
            <path d="M15.41 6.51l-6.82 3.98"/>
          </svg>
          <span>Share</span>
        </button>
        <button type="button" class="rail-button secondary" onclick="resetData()" title="Reset">
          <svg viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
            <path d="M3 12a9 9 0 1 0 3-6.7" />
            <path d="M3 4v5h5" />
          </svg>
          <span>Reset</span>
        </button>
        <button type="button" class="rail-button secondary" onclick="openBackupModal()" title="Backup">
          <svg viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
            <path d="M5 4h11l3 3v13H5z" />
            <path d="M8 4v6h8V4" />
            <path d="M8 20v-6h8v6" />
          </svg>
          <span>Backup</span>
        </button>
        <button type="button" class="rail-button" onclick="openTaskModal()" title="Add task">
          <svg viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
            <path d="M12 5v14" />
            <path d="M5 12h14" />
          </svg>
          <span>Add</span>
        </button>
      </div>
    </aside>

    <main class="board">
      <div class="print-sheet">
        <div class="board-head">
          <div>
            <div class="eyebrow">Month View</div>
            <h2 id="boardTitle" class="board-title">Chore Planner</h2>
          </div>
          <div class="board-meta">
            <div class="meta-chip" id="statsChip">0 tasks</div>
            <div class="meta-chip" id="periodChip">Daily</div>
            <div class="meta-chip" id="monthChip">March 2026</div>
            <button class="meta-chip help-button" onclick="openHelpModal()" title="How to use" style="cursor:pointer;border:1px solid var(--line);background:#fff;font-weight:900;font-size:13px;padding:4px 10px;">?</button>
          </div>
        </div>

        <p class="board-intro" style="margin:0 0 8px;padding:8px 12px;background:rgba(245,238,228,0.7);border-radius:8px;font-size:11px;line-height:1.5;color:#666;">
          Add tasks to categories, drag them onto calendar days. Your data lives <strong>only in this browser</strong> &mdash; use
          <strong>Share</strong> to transfer via link or <strong>Backup</strong> to save a file. Click <strong style="font-size:13px;">?</strong> for full guide.
        </p>

        <div class="layout">
          <div class="stack">
            <section class="surface calendar-surface">
              <div class="period-switcher" id="periodSwitcher"></div>
              <div class="calendar-grid" id="calendarGrid"></div>
            </section>
          </div>

          <section class="surface legend-surface">
            <div class="legend-groups" id="masterTaskList"></div>
          </section>
        </div>
      </div>
    </main>
    <div class="qr-page" id="qrPage">
      <div class="qr-content">
        <h2 class="qr-title">Scan to load this calendar</h2>
        <div id="qrCodeContainer"></div>
        <p class="qr-desc">Scan this QR code with your phone to open the calendar with all current tasks and settings. The data is encoded in the URL.</p>
        <p class="qr-error" id="qrError" style="display:none;">Calendar data is too large for a QR code. Use the Share link or Backup file instead.</p>
      </div>
    </div>
    <footer style="text-align:center;padding:8px;font-size:11px;color:#999;letter-spacing:0.02em;">
      <a href="https://github.com/dzaczek/chore-calendar" target="_blank" rel="noopener" style="color:#999;text-decoration:none;">dzaczek &copy; 2026 &middot; github.com/dzaczek/chore-calendar</a>
    </footer>
  </div>

  <div class="settings-modal" id="settingsModal" hidden onclick="closeSettingsModalOnBackdrop(event)">
    <div class="settings-modal-card" role="dialog" aria-modal="true" aria-labelledby="settingsModalHeading">
      <div class="settings-modal-head">
        <div class="section-copy">
          <div class="eyebrow">Settings</div>
          <h3 class="settings-modal-title" id="settingsModalHeading">General settings</h3>
          <p class="surface-note">Board title, people and current month are configured here in a popup menu.</p>
        </div>
        <button type="button" class="secondary settings-modal-close" onclick="closeSettingsModal()">Close</button>
      </div>

      <form class="settings-form" id="settingsForm" onsubmit="submitSettingsForm(event)">
        <div class="field">
          <label for="titleInput">Board title</label>
          <input id="titleInput" type="text" placeholder="Chore Planner">
        </div>

        <div class="row">
          <div class="field">
            <label for="monthSelect">Month</label>
            <select id="monthSelect"></select>
          </div>
          <div class="field">
            <label for="yearInput">Year</label>
            <input id="yearInput" type="text" inputmode="numeric" placeholder="2026">
          </div>
        </div>

        <div class="field">
          <label for="weekStartSelect">Week starts on</label>
          <select id="weekStartSelect">
            <option value="sunday">Sunday</option>
            <option value="monday">Monday</option>
          </select>
        </div>

        <div class="button-row settings-actions">
          <button type="submit" class="settings-save action-button">
            <svg viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
              <path d="M5 4h11l3 3v13H5z" />
              <path d="M8 4v6h8V4" />
              <path d="M8 20v-6h8v6" />
            </svg>
            <span>Save</span>
          </button>
          <button type="button" class="secondary" onclick="closeSettingsModal()">Cancel</button>
        </div>
      </form>
    </div>
  </div>

  <div class="task-modal" id="taskModal" hidden onclick="closeTaskModalOnBackdrop(event)">
    <div class="task-modal-card" role="dialog" aria-modal="true" aria-labelledby="taskModalHeading">
      <div class="task-modal-head">
        <div class="section-copy">
          <div class="eyebrow">Task Window</div>
          <h3 class="task-modal-title" id="taskModalHeading">Add task</h3>
          <p class="surface-note">Weekly tasks stay on a weekday. Monthly can be moved to an exact date. Custom tasks are placed manually by dragging to calendar days.</p>
        </div>
        <button type="button" class="secondary task-modal-close" onclick="closeTaskModal()">Close</button>
      </div>

      <form class="task-form" id="taskForm" onsubmit="submitTaskForm(event)">
        <div class="field">
          <label for="taskTitle">Task name</label>
          <input id="taskTitle" type="text" placeholder="Bathroom sink">
        </div>

        <div class="row">
          <div class="field">
            <label for="taskIcon">Icon</label>
            <input id="taskIcon" type="text" maxlength="4" placeholder="BS">
          </div>
          <div class="field">
            <label for="taskPeriod">Period</label>
            <select id="taskPeriod" onchange="toggleDayField()"></select>
          </div>
        </div>

        <div class="field" id="taskDayWrap">
          <label for="taskDay">Weekday shown in calendar</label>
          <select id="taskDay"></select>
        </div>

        <div class="button-row">
          <button type="submit" id="taskModalSubmit">Add task</button>
          <button type="button" class="secondary" onclick="closeTaskModal()">Cancel</button>
        </div>
      </form>
    </div>
  </div>

  <div class="task-modal" id="backupModal" hidden onclick="closeBackupModalOnBackdrop(event)">
    <div class="task-modal-card" role="dialog" aria-modal="true" aria-labelledby="backupModalHeading">
      <div class="task-modal-head">
        <div class="section-copy">
          <div class="eyebrow">Backup</div>
          <h3 class="task-modal-title" id="backupModalHeading">Backup &amp; Restore</h3>
          <p class="surface-note">Download your calendar data as a file or restore from a previous backup.</p>
        </div>
        <button type="button" class="secondary task-modal-close" onclick="closeBackupModal()">Close</button>
      </div>
      <div style="margin-top:16px;display:grid;gap:12px;">
        <button type="button" class="action-button" onclick="downloadBackup()" style="width:100%;padding:14px;font-size:14px;">
          <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
            <path d="M5 4h11l3 3v13H5z" />
            <path d="M8 4v6h8V4" />
            <path d="M8 20v-6h8v6" />
          </svg>
          <span>Download Backup</span>
        </button>
        <button type="button" class="secondary action-button" onclick="triggerRestore()" style="width:100%;padding:14px;font-size:14px;">
          <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
            <path d="M3 15v4a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-4" />
            <polyline points="7 10 12 15 17 10" />
            <line x1="12" y1="15" x2="12" y2="3" />
          </svg>
          <span>Restore Backup</span>
        </button>
        <input type="file" id="restoreFileInput" accept=".json" style="display:none;" onchange="restoreBackup(event)">
      </div>
    </div>
  </div>

  <div class="task-modal" id="helpModal" hidden onclick="closeHelpModalOnBackdrop(event)">
    <div class="settings-modal-card" role="dialog" aria-modal="true" aria-labelledby="helpModalHeading" style="max-width:560px;">
      <div class="task-modal-head">
        <div class="section-copy">
          <div class="eyebrow">Help</div>
          <h3 class="task-modal-title" id="helpModalHeading">How to use Chore Planner</h3>
        </div>
        <button type="button" class="secondary task-modal-close" onclick="closeHelpModal()">Close</button>
      </div>
      <div style="margin-top:14px;font-size:13px;line-height:1.6;color:#333;">
        <p style="margin:0 0 12px;padding:10px;background:#fff8e8;border-radius:8px;border:1px solid #e8d8b0;font-weight:600;">
          &#9888; Your data is stored <strong>only in this browser</strong> (localStorage). The server does not save anything. If you clear browser data or switch devices, your calendar will be empty.
        </p>

        <h4 style="margin:14px 0 6px;font-size:14px;">How to keep your data safe</h4>
        <ul style="margin:0 0 10px;padding-left:20px;">
          <li><strong>Share link</strong> &mdash; generates a compressed URL with all your data. Send it to someone or open it on another device to transfer your calendar.</li>
          <li><strong>Backup</strong> &mdash; downloads a JSON file with your calendar. Use <em>Restore</em> to load it back anytime.</li>
          <li>Data is auto-saved to your browser after every change.</li>
        </ul>

        <h4 style="margin:14px 0 6px;font-size:14px;">Task categories</h4>
        <ul style="margin:0 0 10px;padding-left:20px;">
          <li><strong>Daily</strong> &mdash; appears on every day of the month automatically.</li>
          <li><strong>Weekly</strong> &mdash; appears every week on a chosen weekday. Drag the dot to a different day column to change the weekday.</li>
          <li><strong>Monthly</strong> &mdash; appears once per month. Drag the dot to a specific date to pin it to that day.</li>
          <li><strong>Custom</strong> &mdash; manual placement. Create a task, then drag it from the legend onto any calendar day you want. Click a dot on the calendar to remove it. The legend shows how many times the task is placed.</li>
          <li><strong>Every N Days</strong> &mdash; repeats every N days within the month. Drag to set the start date.</li>
        </ul>

        <h4 style="margin:14px 0 6px;font-size:14px;">Tips</h4>
        <ul style="margin:0 0 10px;padding-left:20px;">
          <li>Click <strong>&#9998;</strong> next to a category to change its color.</li>
          <li>Click <strong>+</strong> next to a category to quickly add a task in that group.</li>
          <li>Use the <strong>period pills</strong> above the calendar to filter by category.</li>
          <li>Use <strong>Print</strong> to generate an A4 landscape version for printing.</li>
          <li>Use <strong>Settings</strong> to change the title, people list, and current month.</li>
        </ul>

        <p style="margin:10px 0 0;color:#999;font-size:11px;text-align:center;">
          <a href="https://github.com/dzaczek/chore-calendar" target="_blank" rel="noopener" style="color:#999;">github.com/dzaczek/chore-calendar</a>
        </p>
      </div>
    </div>
  </div>

  <script>
    const DAYS = {{ days|tojson }};
    const PERIODS = {{ periods|tojson }};
    const DEFAULT_CATEGORY_COLORS = {{ default_category_colors|tojson }};
    const MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"];
    const STORAGE_KEY = "chore_planner_data";
    const serverDefaults = {{ initial_data|safe }};
    let state = loadInitialState();
    let activePeriod = "all";
    let taskModalTaskId = null;

    function loadInitialState() {
      const urlParam = new URLSearchParams(window.location.search).get("d");
      const existing = localStorage.getItem(STORAGE_KEY);
      if (urlParam) {
        try {
          const json = LZString.decompressFromEncodedURIComponent(urlParam);
          if (json) {
            const parsed = JSON.parse(json);
            const clean = new URL(window.location);
            clean.searchParams.delete("d");
            clean.searchParams.delete("period");
            window.history.replaceState(null, "", clean.toString());
            if (existing) {
              const accept = confirm(
                "Someone shared a calendar with you.\n\n" +
                "OK = Load shared calendar (replaces your current data)\n" +
                "Cancel = Keep your current calendar"
              );
              if (accept) {
                saveToLocalStorage(parsed);
                return parsed;
              } else {
                return JSON.parse(existing);
              }
            }
            saveToLocalStorage(parsed);
            return parsed;
          }
        } catch (e) { /* ignore bad URL data */ }
      }
      if (existing) {
        try { return JSON.parse(existing); } catch (e) { /* ignore */ }
      }
      return serverDefaults;
    }

    function saveToLocalStorage(data) {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(data));
    }

    function generateShareLink() {
      const json = JSON.stringify(state);
      const compressed = LZString.compressToEncodedURIComponent(json);
      const url = new URL(window.location.origin + "/");
      url.searchParams.set("d", compressed);
      return url.toString();
    }

    function uid() {
      return "id-" + Math.random().toString(36).slice(2, 10);
    }

    function escapeHtml(value) {
      return String(value)
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#039;");
    }

    function mixColorWithWhite(hex, ratio) {
      const r = parseInt(hex.slice(1,3), 16);
      const g = parseInt(hex.slice(3,5), 16);
      const b = parseInt(hex.slice(5,7), 16);
      const mr = Math.round(r * ratio + 255 * (1 - ratio));
      const mg = Math.round(g * ratio + 255 * (1 - ratio));
      const mb = Math.round(b * ratio + 255 * (1 - ratio));
      return `#${mr.toString(16).padStart(2,"0")}${mg.toString(16).padStart(2,"0")}${mb.toString(16).padStart(2,"0")}`;
    }

    function defaultIcon(title) {
      const parts = String(title || "").trim().split(/\s+/).filter(Boolean);
      const icon = parts.slice(0, 2).map(part => part[0]).join("").toUpperCase();
      return icon || "?";
    }

    function taskNumber(task) {
      const index = state.tasks.findIndex(item => item.id === task.id);
      return index >= 0 ? index + 1 : "?";
    }

    function findTask(taskId) {
      return state.tasks.find(task => task.id === taskId);
    }

    function customPeriods() {
      return state.settings.custom_periods || [];
    }

    function allPeriods() {
      return [...PERIODS, ...customPeriods().map(cp => cp.id)];
    }

    function findCustomPeriod(periodId) {
      return customPeriods().find(cp => cp.id === periodId);
    }

    function isCustomPeriod(period) {
      return period.startsWith("every_");
    }

    function periodLabel(period) {
      if (period === "all") return "All Periods";
      if (period === "daily") return "Daily";
      if (period === "weekly") return "Weekly";
      if (period === "monthly") return "Monthly";
      if (period === "custom") return "Custom";
      const cp = findCustomPeriod(period);
      if (cp) return `Every ${cp.interval} Days`;
      return period;
    }

    function tasksForPeriod(period) {
      return state.tasks.filter(task => task.period === period);
    }

    function currentCategoryColor(period) {
      const customColors = state.settings.category_colors || {};
      if (customColors[period]) return customColors[period];
      if (DEFAULT_CATEGORY_COLORS[period]) return DEFAULT_CATEGORY_COLORS[period];
      const cp = findCustomPeriod(period);
      return cp ? cp.color : "#b8c8a8";
    }

    function applyCategoryColors() {
      allPeriods().forEach(period => {
        document.documentElement.style.setProperty(`--${period}`, currentCategoryColor(period));
      });
    }

    function addCustomPeriod() {
      const input = prompt("Every how many days? (2-30)");
      if (!input) return;
      const interval = Math.min(30, Math.max(2, parseInt(input, 10)));
      if (!Number.isFinite(interval)) {
        alert("Please enter a number between 2 and 30.");
        return;
      }
      const existing = customPeriods().find(cp => cp.interval === interval);
      if (existing) {
        alert(`Category "Every ${interval} Days" already exists.`);
        return;
      }
      const id = `every_${interval}`;
      const colors = ["#c9d4a0", "#d4c9a0", "#a0c9d4", "#d4a0c9", "#a0d4b8", "#c4a0d4", "#d4b8a0"];
      const color = colors[customPeriods().length % colors.length];
      if (!state.settings.custom_periods) state.settings.custom_periods = [];
      state.settings.custom_periods.push({ id, interval, color });
      state.settings.category_colors = state.settings.category_colors || {};
      state.settings.category_colors[id] = color;
      saveAll(false, false);
    }

    function removeCustomPeriod(periodId) {
      const cp = findCustomPeriod(periodId);
      if (!cp) return;
      const tasksInPeriod = tasksForPeriod(periodId);
      if (tasksInPeriod.length > 0) {
        if (!confirm(`This will delete ${tasksInPeriod.length} task(s) in "${periodLabel(periodId)}". Continue?`)) return;
        state.tasks = state.tasks.filter(t => t.period !== periodId);
      }
      state.settings.custom_periods = customPeriods().filter(c => c.id !== periodId);
      delete (state.settings.category_colors || {})[periodId];
      saveAll(false, false);
    }

    function currentYear() {
      return state.settings.view_year;
    }

    function currentMonth() {
      return state.settings.view_month;
    }

    function weekdayIndex(day) {
      return DAYS.indexOf(day);
    }

    function parseMonthDate(value) {
      const parsed = Number.parseInt(value, 10);
      if (!Number.isFinite(parsed)) {
        return null;
      }
      return Math.min(31, Math.max(1, parsed));
    }

    function dayLimitForMonth(year, month) {
      return new Date(year, month, 0).getDate();
    }

    function manualMonthDateForTask(task, dayLimit = null) {
      if (!["monthly"].includes(task.period) && !isCustomPeriod(task.period)) {
        return null;
      }

      const parsed = parseMonthDate(task.month_date);
      if (parsed === null) {
        return null;
      }

      return dayLimit === null ? parsed : Math.min(parsed, dayLimit);
    }

    function taskScheduleLabel(task) {
      if (task.period === "daily") {
        return "All month";
      }

      if (task.period === "custom") {
        const count = customPlacementsThisMonth(task).length;
        return count > 0 ? `${count}× placed` : "Drag to calendar";
      }

      const cp = findCustomPeriod(task.period);
      if (cp) {
        const manualDate = manualMonthDateForTask(task, dayLimitForMonth(currentYear(), currentMonth()));
        if (manualDate !== null) return `From day ${manualDate}`;
        return `Every ${cp.interval} days`;
      }

      const manualDate = manualMonthDateForTask(task, dayLimitForMonth(currentYear(), currentMonth()));
      if (manualDate !== null) {
        return `Date ${manualDate}`;
      }

      return task.day;
    }

    function weekStartOffset() {
      return state.settings.week_start === "monday" ? 1 : 0;
    }

    function orderedDays() {
      const offset = weekStartOffset();
      return [...DAYS.slice(offset), ...DAYS.slice(0, offset)];
    }

    function monthMatrix(year, month) {
      const firstDay = new Date(year, month - 1, 1);
      const daysInMonth = new Date(year, month, 0).getDate();
      const offset = weekStartOffset();
      const lead = (firstDay.getDay() - offset + 7) % 7;
      const total = Math.ceil((lead + daysInMonth) / 7) * 7;
      const cells = [];

      for (let index = 0; index < total; index += 1) {
        const dateNumber = index - lead + 1;
        if (dateNumber < 1 || dateNumber > daysInMonth) {
          cells.push(null);
          continue;
        }

        const dateObj = new Date(year, month - 1, dateNumber);
        cells.push({
          year,
          month,
          dateNumber,
          weekday: DAYS[dateObj.getDay()],
          weekdayIndex: dateObj.getDay()
        });
      }

      return cells;
    }

    function compactCellsForPrint(cells) {
      const compact = cells.filter(Boolean);
      const padded = [...compact];
      while (padded.length % 7 !== 0) {
        padded.push(null);
      }
      return padded;
    }

    function customPlacementsThisMonth(task) {
      if (task.period !== "custom") return [];
      const year = currentYear();
      const month = currentMonth();
      return (task.placements || []).filter(p => p.year === year && p.month === month);
    }

    function matchingDatesForTask(task, cells) {
      if (task.period === "daily") {
        return cells.filter(Boolean).map(cell => cell.dateNumber);
      }

      if (task.period === "custom") {
        const dates = customPlacementsThisMonth(task).map(p => p.date);
        return [...new Set(dates)];
      }

      const cp = findCustomPeriod(task.period);
      if (cp) {
        const allDates = cells.filter(Boolean).map(cell => cell.dateNumber);
        const manualStart = manualMonthDateForTask(task, Math.max(...allDates));
        const start = manualStart !== null ? manualStart : 1;
        return allDates.filter(d => d >= start && (d - start) % cp.interval === 0);
      }

      const manualDate = manualMonthDateForTask(
        task,
        cells.reduce((max, cell) => cell ? Math.max(max, cell.dateNumber) : max, 0)
      );
      if (manualDate !== null) {
        return [manualDate];
      }

      const matching = cells.filter(cell => cell && cell.weekday === task.day);
      if (task.period === "weekly") {
        return matching.map(cell => cell.dateNumber);
      }

      return matching.length ? [matching[0].dateNumber] : [];
    }

    function tasksForDate(cell, cells) {
      return state.tasks.filter(task => {
        if (activePeriod !== "all" && task.period !== activePeriod) {
          return false;
        }
        return matchingDatesForTask(task, cells).includes(cell.dateNumber);
      });
    }

    function renderFields() {
      document.getElementById("titleInput").value = state.settings.title || "";
      document.getElementById("yearInput").value = state.settings.view_year || "";

      document.getElementById("monthSelect").innerHTML = MONTHS
        .map((month, index) => `<option value="${index + 1}">${month}</option>`)
        .join("");
      document.getElementById("monthSelect").value = String(state.settings.view_month || 1);

      document.getElementById("weekStartSelect").value = state.settings.week_start || "sunday";

      const taskPeriodInput = document.getElementById("taskPeriod");
      const all = allPeriods();
      const selectedTaskPeriod = all.includes(taskPeriodInput.value) ? taskPeriodInput.value : "daily";
      taskPeriodInput.innerHTML = all
        .map(period => `<option value="${period}">${periodLabel(period)}</option>`)
        .join("");
      taskPeriodInput.value = selectedTaskPeriod;

      const taskDayInput = document.getElementById("taskDay");
      const selectedTaskDay = DAYS.includes(taskDayInput.value) ? taskDayInput.value : DAYS[0];
      taskDayInput.innerHTML = DAYS
        .map(day => `<option value="${day}">${day}</option>`)
        .join("");
      taskDayInput.value = selectedTaskDay;

      updateTaskModalState();
      applyCategoryColors();
      toggleDayField();
    }

    function renderHeader() {
      const month = currentMonth();
      const year = currentYear();
      document.getElementById("boardTitle").textContent = state.settings.title || "Chore Planner";
      document.getElementById("statsChip").textContent = `${state.tasks.length} task${state.tasks.length === 1 ? "" : "s"}`;
      document.getElementById("periodChip").textContent = periodLabel(activePeriod);
      document.getElementById("monthChip").textContent = `${MONTHS[month - 1]} ${year}`;
    }

    function periodStyle(period) {
      const color = currentCategoryColor(period);
      if (isCustomPeriod(period)) {
        return `background:${color};color:#2a3a1c;`;
      }
      return "";
    }

    function calendarDot(task) {
      const dot = document.createElement("div");
      dot.className = `calendar-dot ${task.period}`;
      if (isCustomPeriod(task.period)) {
        dot.style.background = currentCategoryColor(task.period);
        dot.style.color = "#2a3a1c";
      }
      dot.dataset.taskId = task.id;
      dot.title = task.title;
      dot.textContent = (task.icon || defaultIcon(task.title)).slice(0, 3);
      return dot;
    }

    function legendItem(task) {
      const entry = document.createElement("article");
      entry.className = "legend-item";
      if (task.period !== "daily") {
        entry.classList.add("is-draggable");
      }
      entry.dataset.taskId = task.id;
      const iconStyle = periodStyle(task.period);
      entry.innerHTML = `
        <div class="legend-icon ${task.period}" ${iconStyle ? `style="${iconStyle}"` : ""}>${escapeHtml((task.icon || defaultIcon(task.title)).slice(0, 3))}</div>
        <div class="legend-copy">
          <div class="legend-top">
            <div class="legend-title">${escapeHtml(task.title)}</div>
            <div class="legend-actions">
              <button class="secondary icon-action" onclick="editTask('${task.id}')" title="Edit">✎</button>
              <button class="secondary icon-action" onclick="deleteTask('${task.id}')" title="Delete">🗑</button>
            </div>
          </div>
          <div class="legend-sub">${escapeHtml(taskScheduleLabel(task))}</div>
        </div>
      `;
      return entry;
    }

    function periodHelpText(period) {
      if (period === "daily") return "Tasks appear on every day of the month automatically.";
      if (period === "weekly") return "Tasks appear on a chosen weekday every week. Drag to a different day to change.";
      if (period === "monthly") return "Tasks appear once per month. Drag to a specific date to pin the day.";
      if (period === "custom") return "Manual placement. Create a task here, then drag it onto any calendar day. Click a dot to remove it.";
      const cp = findCustomPeriod(period);
      if (cp) return `Tasks repeat every ${cp.interval} days. Drag to a date to set the start day.`;
      return "";
    }

    function periodSection(period, isCustom) {
      const color = currentCategoryColor(period);
      const visibleTasks = tasksForPeriod(period);
      const deleteBtn = isCustom
        ? `<button class="secondary legend-color-button" type="button" onclick="removeCustomPeriod('${period}')" title="Delete category" style="background:#e8a0a0;color:#4a1c1c;">x</button>`
        : "";
      const helpText = periodHelpText(period);
      return `
        <section class="legend-group">
          <div class="legend-head" style="background: ${mixColorWithWhite(color, 0.42)};">
            <span class="legend-head-title">${periodLabel(period)}</span>
            <span class="legend-head-actions">
              <button class="secondary legend-color-button" type="button" onclick="toggleHelpTooltip(event, '${period}')" title="${helpText}" style="background:#fff;color:#666;font-size:10px;font-weight:900;">?</button>
              <button class="secondary legend-color-button" type="button" onclick="openCategoryColorPicker('${period}')" title="Change color" style="background:${color};">✎</button>
              <input id="categoryColor-${period}" class="legend-color-input" type="color" value="${color}" onchange="updateCategoryColor('${period}', this.value)">
              <button class="secondary legend-color-button" type="button" onclick="addTaskForPeriod('${period}')" title="Add task" style="background:${color};">+</button>
              ${deleteBtn}
            </span>
          </div>
          <div class="legend-list" data-period-list="${period}">
            ${visibleTasks.length ? "" : '<div class="empty">No tasks.</div>'}
          </div>
        </section>
      `;
    }

    function renderTaskList() {
      const list = document.getElementById("masterTaskList");
      const builtIn = PERIODS.map(period => periodSection(period, false)).join("");
      const custom = customPeriods().map(cp => periodSection(cp.id, true)).join("");
      const addBtn = '<button class="secondary" type="button" onclick="addCustomPeriod()" style="width:100%;padding:6px;font-size:11px;border-radius:4px;margin-top:4px;">+ Add Every N Days Category</button>';
      list.innerHTML = builtIn + custom + addBtn;

      allPeriods().forEach(period => {
        const target = list.querySelector(`[data-period-list="${period}"]`);
        if (!target) return;
        tasksForPeriod(period).forEach(task => {
          target.appendChild(legendItem(task));
        });

        Sortable.create(target, {
          group: {
            name: "calendar-tasks",
            pull: "clone",
            put: false
          },
          animation: 150,
          sort: false,
          draggable: ".legend-item.is-draggable",
          filter: ".legend-actions, .legend-actions *",
          preventOnFilter: false
        });
      });
    }

    function renderPeriodSwitcher() {
      const switcher = document.getElementById("periodSwitcher");
      switcher.innerHTML = ["all", ...allPeriods()].map(period => `
        <button class="period-pill ${period === activePeriod ? "active" : ""}" onclick="setActivePeriod('${period}')">
          ${periodLabel(period)}
        </button>
      `).join("");
    }

    function removeCustomPlacement(taskId, dateNumber) {
      const task = findTask(taskId);
      if (!task || !task.placements) return;
      const year = currentYear();
      const month = currentMonth();
      const idx = task.placements.findIndex(p => p.year === year && p.month === month && p.date === dateNumber);
      if (idx >= 0) {
        task.placements.splice(idx, 1);
        saveAll(false, false);
      }
    }

    function setActivePeriod(period) {
      activePeriod = period;
      render();
    }

    function renderCalendar() {
      const grid = document.getElementById("calendarGrid");
      grid.innerHTML = "";
      const year = currentYear();
      const month = currentMonth();
      const baseCells = monthMatrix(year, month);
      const isPrintLayout = document.body.classList.contains("print-mode");
      const cells = isPrintLayout ? compactCellsForPrint(baseCells) : baseCells;
      const rowCount = Math.max(1, Math.ceil(cells.length / 7));
      grid.style.gridTemplateRows = `repeat(${rowCount}, minmax(0, 1fr))`;

      cells.forEach(cell => {
        const box = document.createElement("section");
        box.className = `day-column month-cell ${cell ? "" : "empty-month-cell"}`;
        if (!cell) {
          box.innerHTML = `<div class="day-dropzone empty-cell"></div>`;
          grid.appendChild(box);
          return;
        }

        const dateTasks = tasksForDate(cell, cells);
        box.innerHTML = `
          <div class="day-head">
            <div class="day-name">${cell.weekday.slice(0, 3).toUpperCase()}</div>
            <div class="day-note">${cell.dateNumber}</div>
          </div>
          <div class="day-dropzone" data-day="${cell.weekday}" data-date="${cell.dateNumber}"></div>
        `;
        grid.appendChild(box);

        const zone = box.querySelector(".day-dropzone");
        dateTasks.forEach(task => {
          const dot = calendarDot(task);
          if (task.period === "custom") {
            dot.title = task.title + " (click to remove)";
            dot.addEventListener("click", () => removeCustomPlacement(task.id, cell.dateNumber));
          }
          zone.appendChild(dot);
        });
      });

      document.querySelectorAll(".day-dropzone").forEach(zone => {
        if (!zone.dataset.day) return;
        Sortable.create(zone, {
          group: {
            name: "calendar-tasks",
            pull: true,
            put: true
          },
          animation: 150,
          sort: false,
          onAdd: async event => {
            const task = findTask(event.item.dataset.taskId);
            if (!task) {
              render();
              return;
            }

            if (task.period === "daily") {
              render();
              return;
            }

            if (task.period === "custom") {
              if (!task.placements) task.placements = [];
              const year = currentYear();
              const month = currentMonth();
              const date = parseInt(event.to.dataset.date, 10);
              const already = task.placements.some(p => p.year === year && p.month === month && p.date === date);
              if (!already) {
                task.placements.push({year, month, date});
              }
              await saveAll(false, false);
              render();
              return;
            }

            if (task.period === "weekly") {
              task.day = event.to.dataset.day;
              delete task.month_date;
            } else if (isCustomPeriod(task.period)) {
              task.month_date = parseMonthDate(event.to.dataset.date);
            } else {
              task.day = event.to.dataset.day;
              task.month_date = parseMonthDate(event.to.dataset.date);
            }

            await saveAll(false, false);
            render();
          }
        });
      });
    }

    function toggleDayField() {
      const frequency = document.getElementById("taskPeriod").value;
      const isCustom = isCustomPeriod(frequency);
      document.getElementById("taskDayWrap").style.display = (frequency === "daily" || frequency === "custom" || isCustom) ? "none" : "block";
    }

    function updateTaskModalState() {
      document.getElementById("taskModalHeading").textContent = taskModalTaskId ? "Edit task" : "Add task";
      document.getElementById("taskModalSubmit").textContent = taskModalTaskId ? "Save task" : "Add task";
    }

    function openCategoryColorPicker(period) {
      const picker = document.getElementById(`categoryColor-${period}`);
      if (!picker) {
        return;
      }
      picker.click();
    }

    async function updateCategoryColor(period, value) {
      if (!PERIODS.includes(period)) {
        return;
      }

      state.settings.category_colors = state.settings.category_colors || {};
      state.settings.category_colors[period] = value;
      applyCategoryColors();

      const saved = await saveAll(false, false);
      if (saved === false) {
        return;
      }

      render();
    }

    function syncModalBodyState() {
      const hasOpenModal = ["taskModal", "settingsModal", "backupModal", "helpModal"].some(id => {
        const modal = document.getElementById(id);
        return modal && !modal.hidden;
      });
      document.body.classList.toggle("modal-open", hasOpenModal);
    }

    function applySettingsFormToState() {
      state.settings.title = document.getElementById("titleInput").value.trim() || "Chore Planner";

      const monthValue = Number.parseInt(document.getElementById("monthSelect").value, 10);
      state.settings.view_month = Number.isFinite(monthValue) ? Math.min(12, Math.max(1, monthValue)) : currentMonth();

      const yearValue = Number.parseInt(document.getElementById("yearInput").value, 10);
      state.settings.view_year = Number.isFinite(yearValue) ? Math.min(2100, Math.max(2000, yearValue)) : currentYear();

      state.settings.week_start = document.getElementById("weekStartSelect").value || "sunday";
    }

    function openSettingsModal() {
      closeTaskModal();
      const modal = document.getElementById("settingsModal");
      modal.hidden = false;
      syncModalBodyState();
      window.requestAnimationFrame(() => document.getElementById("titleInput").focus());
    }

    function closeSettingsModal() {
      const modal = document.getElementById("settingsModal");
      if (modal.hidden) {
        syncModalBodyState();
        return;
      }

      modal.hidden = true;
      renderFields();
      syncModalBodyState();
    }

    function closeSettingsModalOnBackdrop(event) {
      if (event.target.id === "settingsModal") {
        closeSettingsModal();
      }
    }

    function openTaskModal(taskId = null) {
      closeSettingsModal();
      const task = taskId ? findTask(taskId) : null;
      if (taskId && !task) {
        return;
      }
      taskModalTaskId = task ? task.id : null;

      document.getElementById("taskTitle").value = task ? task.title : "";
      document.getElementById("taskIcon").value = task ? (task.icon || "") : "";
      document.getElementById("taskPeriod").value = task ? task.period : "daily";
      document.getElementById("taskDay").value = task && task.day ? task.day : DAYS[0];

      updateTaskModalState();
      toggleDayField();

      const modal = document.getElementById("taskModal");
      modal.hidden = false;
      syncModalBodyState();
      window.requestAnimationFrame(() => document.getElementById("taskTitle").focus());
    }

    function addTaskForPeriod(period) {
      openTaskModal();
      document.getElementById("taskPeriod").value = period;
      toggleDayField();
    }

    function closeTaskModal() {
      const modal = document.getElementById("taskModal");
      if (modal.hidden) {
        taskModalTaskId = null;
        updateTaskModalState();
        syncModalBodyState();
        return;
      }

      modal.hidden = true;
      taskModalTaskId = null;
      updateTaskModalState();
      syncModalBodyState();
    }

    function closeTaskModalOnBackdrop(event) {
      if (event.target.id === "taskModal") {
        closeTaskModal();
      }
    }

    async function submitTaskForm(event) {
      event.preventDefault();

      const title = document.getElementById("taskTitle").value.trim();
      const iconInput = document.getElementById("taskIcon").value.trim();
      const period = document.getElementById("taskPeriod").value;
      const isCustom = isCustomPeriod(period);
      const day = (period === "daily" || period === "custom" || isCustom) ? "" : document.getElementById("taskDay").value;

      if (!title) {
        alert("Please enter a task name.");
        return;
      }

      const existingTask = taskModalTaskId ? findTask(taskModalTaskId) : null;
      if (taskModalTaskId && !existingTask) {
        closeTaskModal();
        render();
        return;
      }

      if (existingTask) {
        existingTask.title = title;
        existingTask.icon = (iconInput || defaultIcon(title)).slice(0, 4);
        existingTask.period = period;
        existingTask.day = day;
        if (period === "daily" || period === "weekly" || period === "custom" || isCustom) {
          delete existingTask.month_date;
        } else {
          const manualDate = parseMonthDate(existingTask.month_date);
          if (manualDate === null) {
            delete existingTask.month_date;
          } else {
            existingTask.month_date = manualDate;
          }
        }
        if (period === "custom" && !existingTask.placements) {
          existingTask.placements = [];
        }
        if (period !== "custom") {
          delete existingTask.placements;
        }
      } else {
        const newTask = {
          id: uid(),
          title,
          period,
          day,
          icon: (iconInput || defaultIcon(title)).slice(0, 4)
        };
        if (period === "custom") {
          newTask.placements = [];
        }
        state.tasks.push(newTask);
      }

      const saved = await saveAll(false, false);
      if (saved === false) {
        return;
      }

      closeTaskModal();
    }

    function nthWeekdayInMonth(year, month, weekday, n) {
      let count = 0;
      const daysInMonth = new Date(year, month, 0).getDate();
      for (let d = 1; d <= daysInMonth; d++) {
        if (new Date(year, month - 1, d).getDay() === weekday) {
          count++;
          if (count === n) return d;
        }
      }
      return null;
    }

    function migrateCustomPlacements(oldYear, oldMonth, newYear, newMonth) {
      if (oldYear === newYear && oldMonth === newMonth) return;
      state.tasks.forEach(task => {
        if (task.period !== "custom" || !task.placements) return;
        const oldPlacements = task.placements.filter(p => p.year === oldYear && p.month === oldMonth);
        if (oldPlacements.length === 0) return;
        const hasNew = task.placements.some(p => p.year === newYear && p.month === newMonth);
        if (hasNew) return;
        oldPlacements.forEach(p => {
          const oldDate = new Date(oldYear, oldMonth - 1, p.date);
          const weekday = oldDate.getDay();
          let nth = 0;
          for (let d = 1; d <= p.date; d++) {
            if (new Date(oldYear, oldMonth - 1, d).getDay() === weekday) nth++;
          }
          const newDate = nthWeekdayInMonth(newYear, newMonth, weekday, nth);
          if (newDate && !task.placements.some(pp => pp.year === newYear && pp.month === newMonth && pp.date === newDate)) {
            task.placements.push({year: newYear, month: newMonth, date: newDate});
          }
        });
      });
    }

    async function submitSettingsForm(event) {
      event.preventDefault();
      const oldYear = currentYear();
      const oldMonth = currentMonth();
      applySettingsFormToState();
      const newYear = currentYear();
      const newMonth = currentMonth();
      migrateCustomPlacements(oldYear, oldMonth, newYear, newMonth);
      const saved = await saveAll(true, false);
      if (saved === false) {
        return;
      }

      closeSettingsModal();
    }

    function editTask(taskId) {
      openTaskModal(taskId);
    }

    function deleteTask(taskId) {
      if (!confirm("Delete this task?")) return;
      state.tasks = state.tasks.filter(task => task.id !== taskId);
      saveAll(false, false);
      render();
    }

    async function saveAll(showAlert = true, syncSettingsForm = true) {
      if (syncSettingsForm) {
        applySettingsFormToState();
      }

      saveToLocalStorage(state);
      render();

      if (showAlert) {
        alert("Saved.");
      }

      return true;
    }

    function resetData() {
      if (!confirm("Reset to the demo planner?")) return;
      state = JSON.parse(JSON.stringify(serverDefaults));
      saveToLocalStorage(state);
      closeSettingsModal();
      closeTaskModal();
      render();
    }

    function shareLink() {
      const link = generateShareLink();
      navigator.clipboard.writeText(link).then(() => {
        alert("Link copied to clipboard!");
      }).catch(() => {
        prompt("Copy this link:", link);
      });
    }

    let activeTooltip = null;

    function toggleHelpTooltip(event, period) {
      event.stopPropagation();
      closeHelpTooltip();
      const btn = event.currentTarget;
      const text = periodHelpText(period);
      const tip = document.createElement("div");
      tip.className = "help-tooltip";
      tip.textContent = text;
      document.body.appendChild(tip);
      const rect = btn.getBoundingClientRect();
      tip.style.top = (rect.bottom + 8 + window.scrollY) + "px";
      tip.style.left = Math.max(8, rect.right - tip.offsetWidth + 10 + window.scrollX) + "px";
      activeTooltip = tip;
      setTimeout(() => document.addEventListener("click", closeHelpTooltip, {once: true}), 10);
    }

    function closeHelpTooltip() {
      if (activeTooltip) {
        activeTooltip.remove();
        activeTooltip = null;
      }
    }

    function openHelpModal() {
      closeSettingsModal();
      closeTaskModal();
      closeBackupModal();
      document.getElementById("helpModal").hidden = false;
      syncModalBodyState();
    }

    function closeHelpModal() {
      document.getElementById("helpModal").hidden = true;
      syncModalBodyState();
    }

    function closeHelpModalOnBackdrop(event) {
      if (event.target.id === "helpModal") closeHelpModal();
    }

    function openBackupModal() {
      closeSettingsModal();
      closeTaskModal();
      document.getElementById("backupModal").hidden = false;
      syncModalBodyState();
    }

    function closeBackupModal() {
      document.getElementById("backupModal").hidden = true;
      syncModalBodyState();
    }

    function closeBackupModalOnBackdrop(event) {
      if (event.target.id === "backupModal") closeBackupModal();
    }

    function downloadBackup() {
      const json = JSON.stringify(state, null, 2);
      const blob = new Blob([json], {type: "application/json"});
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      const now = new Date();
      const stamp = now.toISOString().slice(0, 10);
      a.href = url;
      a.download = `chore-planner-backup-${stamp}.json`;
      a.click();
      URL.revokeObjectURL(url);
    }

    function triggerRestore() {
      document.getElementById("restoreFileInput").value = "";
      document.getElementById("restoreFileInput").click();
    }

    function restoreBackup(event) {
      const file = event.target.files[0];
      if (!file) return;
      const reader = new FileReader();
      reader.onload = function(e) {
        try {
          const parsed = JSON.parse(e.target.result);
          if (!parsed.settings || !parsed.tasks) {
            alert("Invalid backup file.");
            return;
          }
          if (!confirm("This will replace your current calendar data. Continue?")) return;
          state = parsed;
          saveToLocalStorage(state);
          closeBackupModal();
          render();
        } catch (err) {
          alert("Could not read backup file: " + err.message);
        }
      };
      reader.readAsText(file);
    }

    function exportPdf() {
      const board = document.querySelector(".print-sheet");
      const page = document.querySelector(".page");
      const panel = document.querySelector(".panel");
      const title = state.settings.title || "Chore Planner";
      const month = MONTHS[(currentMonth() || 1) - 1];
      const year = currentYear();
      const filename = `${title} - ${month} ${year}.pdf`;

      const saved = {
        page: page.style.cssText,
        board: document.querySelector(".board").style.cssText,
        sheet: board.style.cssText
      };
      panel.style.display = "none";
      page.style.cssText = "display:block;max-width:none;margin:0;padding:0;";
      document.querySelector(".board").style.cssText = "border:0;box-shadow:none;padding:8px;background:white;min-height:0;overflow:visible;border-radius:0;";
      board.style.cssText = "width:1120px;background:white;padding:8px;";
      const hideEls = board.querySelectorAll(".board-intro, .period-switcher, .legend-actions, .legend-head-actions, .help-button, .eyebrow");
      hideEls.forEach(el => el.dataset.pdfHidden = el.style.display || "");
      hideEls.forEach(el => el.style.display = "none");

      const opt = {
        margin: [2, 2, 2, 2],
        filename: filename,
        image: {type: "jpeg", quality: 0.95},
        html2canvas: {
          scale: 2,
          useCORS: true,
          logging: false,
          scrollX: 0,
          scrollY: -window.scrollY
        },
        jsPDF: {unit: "mm", format: "a4", orientation: "landscape"}
      };

      function restore() {
        panel.style.display = "";
        page.style.cssText = saved.page;
        document.querySelector(".board").style.cssText = saved.board;
        board.style.cssText = saved.sheet;
        hideEls.forEach(el => { el.style.display = el.dataset.pdfHidden || ""; delete el.dataset.pdfHidden; });
      }

      html2pdf().set(opt).from(board).save().then(restore).catch(function(err) {
        restore();
        alert("PDF generation failed: " + err.message);
      });
    }

    function openPrintView() {
      saveToLocalStorage(state);
      const params = new URLSearchParams({
        period: activePeriod,
        d: LZString.compressToEncodedURIComponent(JSON.stringify(state)),
      });
      window.open(`/print?${params.toString()}`, "_blank", "noopener,noreferrer");
    }

    function render() {
      renderFields();
      renderHeader();
      renderTaskList();
      renderCalendar();
    }

    render();
    document.addEventListener("keydown", event => {
      if (event.key === "Escape" && !document.getElementById("helpModal").hidden) {
        closeHelpModal();
      } else if (event.key === "Escape" && !document.getElementById("backupModal").hidden) {
        closeBackupModal();
      } else if (event.key === "Escape" && !document.getElementById("settingsModal").hidden) {
        closeSettingsModal();
      } else if (event.key === "Escape" && !document.getElementById("taskModal").hidden) {
        closeTaskModal();
      }
    });

    function generateQrCode() {
      const container = document.getElementById("qrCodeContainer");
      const errorEl = document.getElementById("qrError");
      if (!container) return;
      const link = generateShareLink();
      if (link.length > 2950) {
        container.style.display = "none";
        errorEl.style.display = "block";
        return;
      }
      try {
        const qr = qrcode(0, "L");
        qr.addData(link);
        qr.make();
        container.innerHTML = qr.createSvgTag(4, 0);
      } catch (e) {
        container.style.display = "none";
        errorEl.style.display = "block";
      }
    }

    if (document.body.classList.contains("print-mode")) {
      const requestedPeriod = new URLSearchParams(window.location.search).get("period");
      if (requestedPeriod && ["all", ...PERIODS].includes(requestedPeriod)) {
        activePeriod = requestedPeriod;
        render();
      }
      generateQrCode();
      window.setTimeout(() => window.print(), 250);
    }
  </script>
</body>
</html>
"""


if __name__ == "__main__":
    app.run(debug=True, host="127.0.0.1", port=5050)
