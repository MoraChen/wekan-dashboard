"""
update_dashboard.py
===================
Wekan 週報儀表板更新腳本
用法：每次 Wekan JSON 更新後，請叫 Claude 執行這支腳本，
      或直接在終端機執行：python update_dashboard.py

腳本會自動：
  1. 找出 "wekan json" 資料夾中最新的 .json 檔
  2. 解析資料（cards、lists、swimlanes、checklists 等）
  3. 產生新的 週報儀表板_YYYYMMDD.html（以今日日期命名）

注意：每次執行都會產生新的 HTML 檔，舊的不會被覆蓋。
"""

import json, os, glob
from datetime import datetime, timezone, timedelta
from collections import defaultdict

# ── 設定 ────────────────────────────────────────────────
BASE_DIR  = os.path.dirname(os.path.abspath(__file__))
JSON_DIR  = os.path.join(BASE_DIR, "wekan json")
OUT_DIR   = BASE_DIR
TODAY_STR = datetime.now().strftime("%Y%m%d")
OUT_FILE  = os.path.join(OUT_DIR, f"週報儀表板_{TODAY_STR}.html")

# ── Wekan 卡片連結設定（填入你的 Wekan 位址）────────────
# 格式：https://your-wekan/b/{boardId}/{slug}
# 空字串 = 不顯示卡片連結
WEKAN_CARD_URL_BASE = "https://wekan.maxlai.com/b/2cTqkd2koHCht3EXt/ai"

# ── 找最新 JSON ─────────────────────────────────────────
json_files = sorted(glob.glob(os.path.join(JSON_DIR, "*.json")), key=os.path.getmtime, reverse=True)
if not json_files:
    raise FileNotFoundError(f"在 '{JSON_DIR}' 中找不到任何 .json 檔案，請確認 Wekan 匯出檔已放入該資料夾。")

JSON_PATH = json_files[0]
print(f"📂 使用 JSON：{os.path.basename(JSON_PATH)}")

with open(JSON_PATH, "r", encoding="utf-8") as f:
    data = json.load(f)

# ── 時間基準（以今日為準）───────────────────────────────
NOW = datetime.now(timezone.utc).replace(hour=23, minute=59, second=59)
NOW_STR = NOW.strftime("%Y-%m-%d")
WEEK_START = (NOW - timedelta(days=7)).replace(hour=0, minute=0, second=0)
STALE_DAYS = 14
DUE_SOON_DAYS = 7
DUE_SOON_END  = (NOW + timedelta(days=DUE_SOON_DAYS)).replace(hour=23, minute=59, second=59)
TODAY_DISPLAY       = f"{NOW.month}/{NOW.day}"
DUE_SOON_END_DISPLAY = f"{DUE_SOON_END.month}/{DUE_SOON_END.day}"

def parse_dt(s):
    if not s: return None
    try: return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except: return None

# ── Lookup maps ─────────────────────────────────────────
users         = {u["_id"]: u["username"] for u in data["users"]}
labels_map    = {l["_id"]: l["name"] for l in data["labels"]}
lists_map     = {l["_id"]: l["title"] for l in data["lists"]}
swimlanes_map = {s["_id"]: s["title"] for s in data["swimlanes"]}

# ── 讀取 team_config.json ──────────────────────────────────────────
TEAM_CONFIG_PATH = os.path.join(BASE_DIR, "team_config.json")
_cfg = {}
fullname_map         = {}
swim_order_cfg       = []   # 主題排序（空 = 依 JSON 原始順序）
default_swim_sel_cfg = []   # 篩選器預設勾選（空 = 全選）

if os.path.exists(TEAM_CONFIG_PATH):
    with open(TEAM_CONFIG_PATH, "r", encoding="utf-8") as _f:
        _cfg = json.load(_f)
    for uid, info in _cfg.get("members", {}).items():
        fn = info.get("fullname") or info.get("username") or uid
        fullname_map[uid] = fn
    _board = _cfg.get("board", {})
    swim_order_cfg       = _board.get("swimlanes_order", [])
    default_swim_sel_cfg = _board.get("default_swim_selections", [])

# 合併：以 fullname_map 覆蓋 users（無對應則保留 username）
display_users = {uid: fullname_map.get(uid, uname) for uid, uname in users.items()}

# ── List 角色對應（從 team_config.json 讀取，有預設值）─────────────
# 每個角色對應一組 List 標題；其他部門只需在 team_config.json 填自己的欄位名稱
_default_roles = {
    "done":    ["DONE"],
    "closed":  ["Closed"],
    "doing":   ["Doing"],
    "waiting": ["Waiting"],
    "review":  ["Review / 使用者Test"],
    "backlog": ["Backlog"],
    "ready":   ["Ready to GO"],
    "info":    ["Goal＆專案資訊"],
}
_roles_cfg = _cfg.get("board", {}).get("lists_roles", {})
_roles = {k: _roles_cfg.get(k, v) for k, v in _default_roles.items()}

def _ids_for_names(names):
    return [lid for lid, t in lists_map.items() if t in names]

DONE_IDS     = _ids_for_names(_roles["done"])
DOING_IDS    = _ids_for_names(_roles["doing"])
WAIT_IDS     = _ids_for_names(_roles["waiting"])
REVIEW_IDS   = _ids_for_names(_roles["review"])
BACKLOG_IDS  = _ids_for_names(_roles["backlog"])
READY_IDS    = _ids_for_names(_roles["ready"])
PIPELINE_IDS = set(DOING_IDS + WAIT_IDS + REVIEW_IDS)

# ── JS 注入用：各排除清單與顯示順序（使用 List 標題）──────────────
# 排除清單由角色自動推導，無需手動維護
_risk_exclude  = _roles["done"]    + _roles["closed"] + _roles["info"]
_act_exclude   = _roles["done"]    + _roles["closed"] + _roles["backlog"] + _roles["info"]
_focus_exclude = _roles["backlog"] + _roles["info"]

TODAY_DISPLAY_JSON    = json.dumps(TODAY_DISPLAY,        ensure_ascii=False)
DUE_SOON_END_JSON     = json.dumps(DUE_SOON_END_DISPLAY, ensure_ascii=False)
SWIM_ORDER_JSON       = json.dumps(swim_order_cfg,       ensure_ascii=False)
DEFAULT_SWIM_SEL_JSON = json.dumps(default_swim_sel_cfg, ensure_ascii=False)
RISK_EXCLUDE_JSON     = json.dumps(_risk_exclude,        ensure_ascii=False)
ACT_EXCLUDE_JSON      = json.dumps(_act_exclude,         ensure_ascii=False)
FOCUS_EXCLUDE_JSON    = json.dumps(_focus_exclude,       ensure_ascii=False)
LIST_ORDER_JSON       = json.dumps(
    _cfg.get("board", {}).get("lists_order", []), ensure_ascii=False)

# ── 父子任務關係 ─────────────────────────────────────────
child_parent_ids = set(c.get("parentId","") for c in data["cards"] if c.get("parentId",""))

# ── Checklist 彙整 ──────────────────────────────────────
cl_items_by_cl = defaultdict(list)
for item in data["checklistItems"]:
    cl_items_by_cl[item["checklistId"]].append(item)

card_cl = defaultdict(lambda: {"total": 0, "done": 0, "count": 0})
for cl in data["checklists"]:
    cid = cl["cardId"]
    card_cl[cid]["count"] += 1
    items = cl_items_by_cl[cl["_id"]]
    card_cl[cid]["total"] += len(items)
    card_cl[cid]["done"]  += sum(1 for i in items if i.get("isFinished"))

# ── 建立 card records ────────────────────────────────────
card_records = []
for c in data["cards"]:
    cid      = c["_id"]
    last_act = parse_dt(c.get("dateLastActivity"))
    due_dt   = parse_dt(c.get("dueAt"))
    archived = c.get("archived", False)
    list_id  = c.get("listId", "")

    stale_days = (NOW - last_act).days if last_act else None
    is_done    = list_id in DONE_IDS or archived
    in_pipeline= list_id in PIPELINE_IDS
    is_overdue  = bool(due_dt and due_dt < NOW and not is_done)
    is_stale    = bool(in_pipeline and stale_days is not None and stale_days > STALE_DAYS)
    is_due_soon = bool(due_dt and NOW <= due_dt <= DUE_SOON_END and not is_done)

    cl = card_cl.get(cid, {"total": 0, "done": 0, "count": 0})
    cl_pct = round(cl["done"] * 100 / cl["total"]) if cl["total"] > 0 else None

    card_records.append({
        "id":               cid,
        "title":            c.get("title", ""),
        "list":             lists_map.get(list_id, "未知"),
        "listId":           list_id,
        "swimlane":         swimlanes_map.get(c.get("swimlaneId", ""), "未知"),
        "swimlaneId":       c.get("swimlaneId", ""),
        "labels":           [labels_map.get(lid, lid) for lid in (c.get("labelIds") or [])],
        "members":          [display_users.get(m, users.get(m, m)) for m in (c.get("members") or [])],
        "createdAt":        c.get("createdAt", ""),
        "endAt":            c.get("endAt", ""),
        "dueAt":            c.get("dueAt", ""),
        "dateLastActivity": c.get("dateLastActivity", ""),
        # archivedAt 已移除（JS 未使用）
        "archived":         archived,
        "isDone":           is_done,
        "isDoing":          list_id in DOING_IDS,
        "isWaiting":        list_id in WAIT_IDS,
        "isReview":         list_id in REVIEW_IDS,
        "inPipeline":       in_pipeline,
        "isOverdue":        is_overdue,
        "isStale":          is_stale,
        "isDueSoon":        is_due_soon,
        "staleDays":        stale_days,
        "dueAtDisplay":     f"{due_dt.month}/{due_dt.day}" if due_dt else "",
        "noMember":         len(c.get("members") or []) == 0,
        "hasChecklist":     cl["total"] > 0,
        "clTotal":          cl["total"],
        "clDone":           cl["done"],
        "clPct":            cl_pct,
        # hasParent / hasChildren 已移除（isChildTask / isParentTask 已涵蓋，JS 未直接使用）
        "parentId":         c.get("parentId", ""),
        "isParentTask":     cid in child_parent_ids and not bool(c.get("parentId","")),
        "isChildTask":      bool(c.get("parentId","")),
        "isStandalone":     cid not in child_parent_ids and not bool(c.get("parentId","")),
        # cardNumber 已移除（JS 未使用）
    })

# ── 每週完成趨勢（近 12 週）────────────────────────────
weekly_trend = []
for w in range(11, -1, -1):  # 從 11 週前到本週
    w_end   = NOW - timedelta(days=w * 7)
    w_start = w_end - timedelta(days=7)
    label   = w_start.strftime("%-m/%-d") + "~" + w_end.strftime("%-m/%-d")
    count   = sum(
        1 for c in card_records
        if c.get("endAt") and c.get("isDone")
        and w_start <= parse_dt(c["endAt"]) < w_end
    )
    new_count = sum(
        1 for c in card_records
        if c.get("createdAt")
        and w_start <= parse_dt(c["createdAt"]) < w_end
    )
    weekly_trend.append({"label": label, "completed": count, "new": new_count})

dashboard_data = {
    "boardTitle":     data["title"],
    "exportedAt":     data.get("modifiedAt", ""),
    "analysisDate":   NOW.isoformat(),
    "nowStr":         NOW_STR,
    "users":          display_users,
    "listsMap":       lists_map,
    "swimlanesMap":   swimlanes_map,
    "labelsMap":      labels_map,
    "listCategories": {
        "DONE":    DONE_IDS,    "DOING":   DOING_IDS,
        "WAIT":    WAIT_IDS,    "REVIEW":  REVIEW_IDS,
        "BACKLOG": BACKLOG_IDS, "READY":   READY_IDS,
    },
    "cards":        card_records,
    "weeklyTrend":  weekly_trend,
}

data_json = json.dumps(dashboard_data, ensure_ascii=False)
print(f"✅ 資料解析完成，共 {len(card_records)} 張卡片")

# ── 提取標題用變數（需求 #6）────────────────────────
board_title      = data.get("title", "Wekan 看板")
now_str          = NOW.strftime("%Y-%m-%d")
json_fname       = os.path.basename(JSON_PATH)
today_display    = TODAY_DISPLAY
due_soon_end_display = DUE_SOON_END_DISPLAY

# ── 產生 HTML ────────────────────────────────────────────
DEFAULT_START = (NOW - timedelta(days=7)).strftime("%Y-%m-%d")
DEFAULT_END   = NOW_STR

html = f"""<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>週報儀表板 - {board_title}</title>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/3.9.1/chart.min.js"></script>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}

        :root {{
            --brand: #1d4ed8;
            --text: #333;
            --bg-light: #f8f9fa;
            --border: #e0e0e0;
            --ok: #4caf50;
            --warn: #ff9800;
            --error: #f44336;
        }}

        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            color: var(--text);
            background: var(--bg-light);
            padding: 20px;
        }}

        .header {{
            background: var(--brand);
            color: white;
            padding: 20px;
            border-radius: 8px;
            margin-bottom: 20px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}

        .header h1 {{ font-size: 24px; margin-bottom: 5px; }}
        .header p {{ font-size: 13px; opacity: 0.9; }}

        .main-tab-bar {{
            background: var(--brand);
            padding: 0 20px;
            border-radius: 8px 8px 0 0;
            display: flex;
            gap: 0;
            margin-top: -1px;
        }}

        .main-tab-btn {{
            color: white;
            border: none;
            background: transparent;
            padding: 12px 20px;
            font-size: 14px;
            cursor: pointer;
            border-bottom: 3px solid transparent;
            transition: border-color 0.3s;
        }}

        .main-tab-btn.active {{
            border-bottom-color: white;
        }}

        .main-tab-btn:hover {{ opacity: 0.8; }}

        .main-panel {{
            display: none;
            background: white;
            padding: 20px;
            border-radius: 0 0 8px 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}

        .main-panel.active {{
            display: block;
        }}

        .filter-bar {{
            background: #f5f5f5;
            padding: 15px;
            border-radius: 6px;
            margin-bottom: 15px;
            display: flex;
            gap: 15px;
            flex-wrap: wrap;
            align-items: center;
        }}

        .filter-item {{
            display: flex;
            flex-direction: column;
            gap: 5px;
            font-size: 12px;
        }}

        .filter-item label {{
            font-weight: 600;
            color: #666;
        }}

        .filter-item input[type="date"] {{
            padding: 6px;
            border: 1px solid var(--border);
            border-radius: 4px;
            font-size: 12px;
        }}

        .picker-container {{
            position: relative;
            display: inline-block;
        }}

        .picker-btn {{
            background: white;
            border: 1px solid var(--border);
            padding: 6px 10px;
            border-radius: 4px;
            cursor: pointer;
            font-size: 12px;
            color: var(--text);
            min-width: 120px;
            text-align: left;
        }}

        .picker-btn:hover {{
            background: #f0f0f0;
        }}

        .picker-dropdown {{
            position: absolute;
            background: white;
            border: 1px solid var(--border);
            border-radius: 4px;
            min-width: 150px;
            max-height: 300px;
            overflow-y: auto;
            z-index: 1000;
            display: none;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }}

        .picker-dropdown.open {{
            display: block;
        }}

        .picker-item {{
            padding: 8px 12px;
            cursor: pointer;
            border-bottom: 1px solid #f0f0f0;
            font-size: 12px;
        }}

        .picker-item:hover {{
            background: #f0f0f0;
        }}

        .picker-item input[type="checkbox"] {{
            margin-right: 8px;
        }}

        .kpi-row {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 15px;
            margin-bottom: 20px;
        }}

        .kpi-card {{
            background: white;
            border: 1px solid var(--border);
            border-radius: 6px;
            padding: 15px;
            text-align: center;
            box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        }}

        .kpi-label {{
            font-size: 12px;
            color: #666;
            margin-bottom: 8px;
            font-weight: 600;
        }}

        .kpi-value {{
            font-size: 28px;
            font-weight: bold;
            color: var(--brand);
        }}

        .kpi-card.alert {{ border-left: 4px solid var(--error); }}
        .kpi-card.alert .kpi-value {{ color: var(--error); }}

        .kpi-card.warn {{ border-left: 4px solid var(--warn); }}
        .kpi-card.warn .kpi-value {{ color: var(--warn); }}

        .charts-container {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            margin-bottom: 20px;
        }}

        .chart-box {{
            background: white;
            border: 1px solid var(--border);
            border-radius: 6px;
            padding: 15px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        }}

        .chart-title {{
            font-size: 14px;
            font-weight: bold;
            margin-bottom: 12px;
            color: var(--text);
        }}

        .chart-wrapper {{
            position: relative;
            height: 250px;
        }}

        .sub-tab-bar {{
            display: flex;
            gap: 0;
            margin: 20px 0 15px 0;
            border-bottom: 2px solid var(--border);
        }}

        .sub-tab-btn {{
            background: transparent;
            border: none;
            padding: 10px 15px;
            font-size: 13px;
            cursor: pointer;
            color: #666;
            border-bottom: 2px solid transparent;
            margin-bottom: -2px;
            transition: all 0.3s;
        }}

        .sub-tab-btn.active {{
            color: var(--brand);
            border-bottom-color: var(--brand);
        }}

        .sub-tab-btn:hover {{ color: var(--brand); }}

        .sub-panel {{
            display: none;
        }}

        .sub-panel.active {{
            display: block;
        }}

        .risk-scope-note {{
            font-size: 0.78em;
            color: #999;
            margin-bottom: 8px;
            padding-left: 4px;
        }}

        .table-wrapper {{
            overflow-x: auto;
        }}

        table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 12px;
        }}

        thead {{
            background: var(--bg-light);
        }}

        th {{
            padding: 10px;
            text-align: left;
            font-weight: 600;
            border-bottom: 2px solid var(--border);
            color: #333;
        }}

        td {{
            padding: 10px;
            border-bottom: 1px solid var(--border);
        }}

        tr:hover {{
            background: #f9f9f9;
        }}

        .swim-group-row {{
            background: var(--brand);
            color: white;
            font-weight: 600;
            cursor: pointer;
            user-select: none;
        }}

        .swim-group-row:hover {{
            background: #1a3aa8;
        }}

        .swim-child {{
            display: none;
            background: #fafafa;
        }}

        .parent-group {{ margin-bottom:12px; border:1px solid #e0e0e0; border-radius:6px; overflow:hidden; }}
        .parent-group-header {{
            background:#f0f4ff; padding:8px 14px; font-weight:600;
            cursor:pointer; color:#3a4a8a; user-select:none;
            display:flex; align-items:center; gap:8px;
        }}
        .parent-group-header:hover {{ background:#e0e8ff; }}
        .parent-group-body table {{ width:100%; border-collapse:collapse; margin:0; }}
        .parent-group-body {{ padding:0; }}

        .badge {{
            display: inline-block;
            padding: 3px 8px;
            border-radius: 3px;
            font-size: 11px;
            font-weight: 600;
            margin-right: 5px;
        }}

        .badge-doing {{
            background: #e3f2fd;
            color: var(--brand);
        }}

        .badge-waiting {{
            background: #fff3e0;
            color: #e65100;
        }}

        .badge-tracking {{
            background: #f3e5f5;
            color: #6a1b9a;
        }}

        .badge-done {{
            background: #e8f5e9;
            color: var(--ok);
        }}

        .badge-stale {{
            background: #ffebee;
            color: var(--error);
        }}
        .badge-due-soon {{
            background: #fff8e1;
            color: #e65100;
            border: 1px solid #ffcc02;
            font-weight: 600;
        }}

        /* 風險摘要卡 */
        .risk-summary {{
            padding: 12px 16px;
            border-radius: 8px;
            margin-bottom: 14px;
            display: flex;
            flex-direction: column;
            gap: 5px;
            font-size: 0.88em;
            line-height: 1.7;
        }}
        .risk-summary.warn {{
            background: #fff8e1;
            border-left: 4px solid #f9a825;
            color: #4e342e;
        }}
        .risk-summary.ok {{
            background: #e8f5e9;
            border-left: 4px solid #43a047;
            color: #2e7d32;
        }}
        .risk-summary-title {{
            font-weight: 700;
            font-size: 0.95em;
            margin-bottom: 2px;
            letter-spacing: 0.02em;
        }}
        .risk-summary-row {{
            display: flex;
            align-items: baseline;
            gap: 6px;
        }}
        .risk-summary-label {{
            color: #8d6e63;
            min-width: 3em;
            font-size: 0.9em;
        }}

        .card-link-icon {{
            opacity: 0;
            display: inline-block;
            margin-left: 6px;
            font-size: 11px;
            color: var(--brand);
            text-decoration: none;
            transition: opacity 0.3s;
        }}

        tr:hover .card-link-icon {{
            opacity: 1;
        }}

        .focus-section {{
            background: white;
            border: 1px solid var(--border);
            border-radius: 6px;
            padding: 15px;
            margin-bottom: 20px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        }}

        .focus-title {{
            font-size: 14px;
            font-weight: bold;
            color: var(--brand);
            margin-bottom: 12px;
        }}

        .focus-row {{
            background: #f5f5f5;
            padding: 10px;
            margin-bottom: 8px;
            border-radius: 4px;
            cursor: pointer;
            border-left: 3px solid var(--brand);
        }}

        .focus-row:hover {{
            background: #eeeeee;
        }}

        .focus-row.expanded {{
            background: white;
            border-left-color: var(--ok);
        }}

        .focus-children {{
            display: none;
            margin-top: 8px;
            margin-left: 20px;
        }}

        .focus-children.open {{
            display: block;
        }}

        .focus-child-row {{
            background: white;
            padding: 8px;
            border: 1px solid var(--border);
            margin-bottom: 6px;
            border-radius: 4px;
            font-size: 11px;
        }}

        /* 通用 info-tip（data-tip 屬性帶入文字）
           原 .stale-tip / .backlog-tip 已統一合併至此 class */
        .info-tip {{
            position: relative;
            cursor: help;
            color: #888;
            font-size: 0.82em;
            margin-left: 3px;
            display: inline-block;
        }}

        .info-tip::after {{
            content: attr(data-tip);
            position: absolute;
            background: #333;
            color: #fff;
            padding: 8px 12px;
            border-radius: 6px;
            font-size: 12px;
            white-space: normal;
            width: 270px;
            left: 50%;
            transform: translateX(-50%);
            bottom: calc(100% + 6px);
            display: none;
            z-index: 100;
            pointer-events: none;
            text-align: center;
            line-height: 1.4;
        }}

        .info-tip:hover::after {{
            display: block;
        }}

        /* 需求 #7: 篩選 Chip 列 */
        .filter-chips-row {{
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
            padding: 10px 0;
            margin-bottom: 10px;
        }}

        .filter-chips-row.hidden {{
            display: none;
        }}

        .filter-chip {{
            background: #e3f2fd;
            border: 1px solid #90caf9;
            border-radius: 16px;
            padding: 4px 12px;
            font-size: 0.82em;
            display: flex;
            align-items: center;
            gap: 6px;
            color: #1565c0;
        }}

        .filter-chip-btn {{
            background: none;
            border: none;
            cursor: pointer;
            color: #1565c0;
            font-weight: bold;
            padding: 0;
            margin-left: 4px;
            font-size: 1em;
        }}

        .clear-all-chips-btn {{
            background: #ffebee;
            border: 1px solid #ef9a9a;
            border-radius: 16px;
            padding: 4px 12px;
            font-size: 0.82em;
            cursor: pointer;
            color: #c62828;
            border: none;
        }}

        .clear-all-chips-btn:hover {{
            background: #ffcdd2;
        }}

        /* 卡片計數說明 */
        .card-count-label {{
            color: #999;
            font-size: 0.85em;
            margin-bottom: 12px;
            font-weight: 500;
        }}

        /* 改動 A1: mini-tab 樣式 */
        .mini-tab-bar {{
            display: flex;
            gap: 6px;
            margin-bottom: 12px;
            border-bottom: 2px solid #e0e0e0;
            padding-bottom: 0;
        }}
        .mini-tab-btn {{
            padding: 5px 16px;
            border: 1px solid #ddd;
            border-bottom: none;
            border-radius: 4px 4px 0 0;
            background: #f5f5f5;
            cursor: pointer;
            font-size: 12px;
            color: #555;
        }}
        .mini-tab-btn.active {{
            background: #fff;
            color: #1976d2;
            border-color: #1976d2;
            border-bottom: 2px solid #fff;
            margin-bottom: -2px;
            font-weight: 600;
        }}
        .mini-tab-btn .mini-badge {{
            display: inline-block;
            background: #e3f2fd;
            color: #1565c0;
            border-radius: 10px;
            font-size: 10px;
            padding: 1px 6px;
            margin-left: 4px;
        }}
        .mini-tab-btn.active .mini-badge {{
            background: #1976d2;
            color: #fff;
        }}

        /* 改動 B3: tab-count badge */
        .tab-count {{
            display: inline-block;
            background: rgba(255,255,255,0.25);
            border-radius: 10px;
            font-size: 10px;
            padding: 1px 6px;
            margin-left: 3px;
            min-width: 16px;
            text-align: center;
        }}
        .sub-tab-btn.active .tab-count {{
            background: rgba(255,255,255,0.35);
        }}
    </style>
</head>
<body>

<div class="header">
    <h1>📊 {board_title} — 週報儀表板</h1>
    <p>分析基準日：{now_str} ｜ 資料來源：{json_fname} ｜ ⚡ 即將到期判斷區間：{today_display} – {due_soon_end_display}</p>
</div>

<div class="main-tab-bar">
    <button class="main-tab-btn active" onclick="switchMainTab('overview')">📊 總覽 & 風險管理</button>
    <button class="main-tab-btn" onclick="switchMainTab('personal')">👤 個人 & 細項追蹤</button>
</div>

<!-- ==================== TAB 1: 總覽 & 風險管理 ==================== -->
<div id="main-panel-overview" class="main-panel active">

    <div class="filter-bar">
        <div class="filter-item">
            <label>開始日期</label>
            <input type="date" id="t1-date-start" value="{DEFAULT_START}" onchange="applyFilters1()">
        </div>
        <div class="filter-item">
            <label>結束日期</label>
            <input type="date" id="t1-date-end" value="{DEFAULT_END}" onchange="applyFilters1()">
        </div>
        <div class="filter-item">
            <label>流程欄位</label>
            <div class="picker-container">
                <button class="picker-btn" id="t1-list-picker-btn">全部欄位</button>
                <div class="picker-dropdown" id="t1-list-picker-dropdown">
                    <div id="t1-list-picker-items"></div>
                </div>
            </div>
        </div>
        <div class="filter-item">
            <label>主題</label>
            <div class="picker-container">
                <button class="picker-btn" id="t1-swim-picker-btn">全部主題</button>
                <div class="picker-dropdown" id="t1-swim-picker-dropdown">
                    <div id="t1-swim-picker-items"></div>
                </div>
            </div>
        </div>
        <div class="filter-item">
            <label>標籤</label>
            <div class="picker-container">
                <button class="picker-btn" id="t1-label-picker-btn">全部標籤</button>
                <div class="picker-dropdown" id="t1-label-picker-dropdown">
                    <div id="t1-label-picker-items"></div>
                </div>
            </div>
        </div>
        <div class="filter-item">
            <label>狀態</label>
            <div class="picker-container">
                <button class="picker-btn" id="t1-status-picker-btn">全部狀態</button>
                <div class="picker-dropdown" id="t1-status-picker-dropdown">
                    <div id="t1-status-picker-items"></div>
                </div>
            </div>
        </div>
        <div class="filter-item">
            <label>封存狀態</label>
            <div class="picker-container">
                <button class="picker-btn" id="t1-archived-picker-btn">封存狀態</button>
                <div class="picker-dropdown" id="t1-archived-picker-dropdown">
                    <div id="t1-archived-picker-items"></div>
                </div>
            </div>
        </div>
    </div>

    <!-- 需求 #7: 篩選 Chip 列 -->

    <!-- 需求 #7: 卡片計數說明 -->
    <div class="card-count-label" id="t1-card-count-label"></div>

    <div class="kpi-row" id="t1-kpi-row"></div>

    <!-- 改動 B1: Tab 1 子分頁按鈕加 badge -->
    <div class="sub-tab-bar">
        <button class="sub-tab-btn active" onclick="switchTab1('newdone')">📅 本週動態 <span class="tab-count" id="t1-cnt-newdone"></span></button>
        <button class="sub-tab-btn" onclick="switchTab1('doing')">▶️ Doing 明細 <span class="tab-count" id="t1-cnt-doing"></span></button>
        <button class="sub-tab-btn" onclick="switchTab1('risk')">🔴 風險與停滯 <span class="tab-count" id="t1-cnt-risk"></span></button>
        <button class="sub-tab-btn" onclick="switchTab1('parent')">🌳 父子結構 <span class="tab-count" id="t1-cnt-parent"></span></button>
        <button class="sub-tab-btn" onclick="switchTab1('all')">📋 全部明細 <span class="tab-count" id="t1-cnt-all"></span></button>
    </div>

    <!-- 需求 #1: 風險與停滯拆為兩子分頁 -->
    <div id="t1-panel-risk" class="sub-panel">
        <!-- 風險摘要卡（A-1）：自動產生，跟篩選器同步 -->
        <div id="risk-summary-box"></div>
        <div class="sub-tab-bar" style="margin-top:0; margin-bottom:15px; border-bottom:1px solid var(--border);">
            <button class="sub-tab-btn active" onclick="switchRiskSubTab('overview')">總覽風險</button>
            <button class="sub-tab-btn" onclick="switchRiskSubTab('swim')">泳道篩選</button>
            <button class="sub-tab-btn" onclick="switchRiskSubTab('duesoon')">⚡ 即將到期</button>
        </div>
        <div class="risk-scope-note">＊資料範圍：排除 DONE / Closed / 過往卡片 / 過往卡片待青 / Goal＆專案資訊 / 封存卡片</div>

        <div id="risk-subpanel-overview" class="sub-panel active">
            <div class="table-wrapper">
                <table id="t1-risk-overview-table">
                    <thead>
                        <tr>
                            <th>專案</th>
                            <th>卡片名稱</th>
                            <th>預計完成日</th>
                            <th>停滯天數 <span class="info-tip" data-tip="停滯定義：卡片在 Pipeline（Doing / Waiting / Review）中，超過 14 天無任何活動（以最後活動日計算）">ℹ️</span></th>
                            <th>所在欄位</th>
                            <th>負責人</th>
                            <th>最後活動日</th>
                            <th>Checklist進度</th>
                            <th>風險標記</th>
                        </tr>
                    </thead>
                    <tbody></tbody>
                </table>
            </div>
        </div>

        <div id="risk-subpanel-swim" class="sub-panel">
            <div style="margin-bottom: 15px;">
                <label>依泳道篩選：</label>
                <select id="t1-risk-swim-filter" onchange="applyRiskSwimFilter()" style="padding:6px; border:1px solid var(--border); border-radius:4px;">
                    <option value="">全部泳道</option>
                </select>
            </div>
            <div class="table-wrapper">
                <table id="t1-risk-swim-table">
                    <thead>
                        <tr>
                            <th>專案</th>
                            <th>卡片名稱</th>
                            <th>預計完成日</th>
                            <th>停滯天數 <span class="info-tip" data-tip="停滯定義：卡片在 Pipeline（Doing / Waiting / Review）中，超過 14 天無任何活動（以最後活動日計算）">ℹ️</span></th>
                            <th>所在欄位</th>
                            <th>負責人</th>
                            <th>最後活動日</th>
                            <th>Checklist進度</th>
                            <th>風險標記</th>
                        </tr>
                    </thead>
                    <tbody></tbody>
                </table>
            </div>
        </div>

        <div id="risk-subpanel-duesoon" class="sub-panel">
            <div style="font-size:0.82em;color:#888;margin-bottom:10px;">⚡ 即將到期：dueAt 在 {today_display} – {due_soon_end_display} 之間（排除 DONE / Closed；以本儀表板產出日為基準）｜<strong style="color:#e65100;">全看板顯示，不受左側篩選器影響</strong></div>
            <div class="table-wrapper">
                <table id="t1-risk-duesoon-table">
                    <thead>
                        <tr>
                            <th>專案</th>
                            <th>卡片名稱</th>
                            <th>預計完成日</th>
                            <th>所在欄位</th>
                            <th>負責人</th>
                            <th>最後活動日</th>
                            <th>風險標記</th>
                        </tr>
                    </thead>
                    <tbody></tbody>
                </table>
            </div>
        </div>
    </div>

    <div id="t1-panel-doing" class="sub-panel">
        <div class="table-wrapper">
            <table id="t1-doing-table">
                <thead>
                    <tr>
                        <th>專案</th>
                        <th>卡片名稱</th>
                        <th>停滯天數 <span class="info-tip" data-tip="停滯定義：卡片在 Pipeline（Doing / Waiting / Review）中，超過 14 天無任何活動（以最後活動日計算）">ℹ️</span></th>
                        <th>所在欄位</th>
                        <th>負責人</th>
                        <th>最後活動日</th>
                        <th>狀態</th>
                    </tr>
                </thead>
                <tbody></tbody>
            </table>
        </div>
    </div>

    <!-- 改動 A2: 本週動態改為 mini-tab 三切換 -->
    <div id="t1-panel-newdone" class="sub-panel active">
        <div class="mini-tab-bar">
            <button class="mini-tab-btn active" id="t1-nd-btn-new" onclick="switchNewDone('t1','new')">
                本週新增 <span class="info-tip" data-tip="過去 7 天內新建立的卡片（以 createdAt 計算）">ℹ️</span><span class="mini-badge" id="t1-nd-badge-new">0</span>
            </button>
            <button class="mini-tab-btn" id="t1-nd-btn-done" onclick="switchNewDone('t1','done')">
                本週完成 <span class="info-tip" data-tip="過去 7 天內移入 DONE 欄位的卡片（以 endAt 計算）">ℹ️</span><span class="mini-badge" id="t1-nd-badge-done">0</span>
            </button>
            <button class="mini-tab-btn" id="t1-nd-btn-activity" onclick="switchNewDone('t1','activity')">
                本週有異動 <span class="info-tip" data-tip="過去 7 天內 dateLastActivity 有更新的卡片（排除 DONE / Closed / Backlog / Goal＆專案資訊）">ℹ️</span><span class="mini-badge" id="t1-nd-badge-activity">0</span>
            </button>
        </div>
        <div id="t1-nd-new">
            <div style="overflow-x:auto">
            <table id="t1-newdone-new-table" style="width:100%">
                <thead><tr>
                    <th>專案</th><th>卡片名稱</th><th>欄位</th><th>負責人</th><th>建立日</th>
                </tr></thead>
                <tbody></tbody>
            </table>
            </div>
        </div>
        <div id="t1-nd-done" style="display:none">
            <div style="overflow-x:auto">
            <table id="t1-newdone-done-table" style="width:100%">
                <thead><tr>
                    <th>專案</th><th>卡片名稱</th><th>負責人</th><th>完成日</th>
                </tr></thead>
                <tbody></tbody>
            </table>
            </div>
        </div>
        <div id="t1-nd-activity" style="display:none">
            <div style="overflow-x:auto">
            <table id="t1-newdone-activity-table" style="width:100%">
                <thead><tr>
                    <th>專案</th><th>卡片名稱</th><th>欄位</th><th>負責人</th><th>最後活動日</th>
                </tr></thead>
                <tbody></tbody>
            </table>
            </div>
        </div>
    </div>

    <!-- 需求 #3: 全部明細扁平 -->
    <div id="t1-panel-all" class="sub-panel">
        <div style="margin-bottom:12px;">
            <label>依泳道篩選：</label>
            <select id="t1-all-swim-filter" onchange="applyAllSwimFilter('t1')" style="padding:6px; border:1px solid var(--border); border-radius:4px;">
                <option value="">全部泳道</option>
            </select>
        </div>
        <div class="table-wrapper" style="max-height:70vh;overflow-y:auto;border:1px solid #e0e0e0;border-radius:4px;">
            <table id="t1-all-table">
                <thead>
                    <tr>
                        <th>專案</th>
                        <th>卡片名稱</th>
                        <th>負責人</th>
                        <th>建立日</th>
                        <th>最後活動日</th>
                        <th>停滯 <span class="info-tip" data-tip="停滯定義：卡片在 Pipeline（Doing / Waiting / Review）中，超過 14 天無任何活動（以最後活動日計算）">ℹ️</span></th>
                        <th>Checklist進度</th>
                        <th>標籤</th>
                    </tr>
                </thead>
                <tbody></tbody>
            </table>
        </div>
        <!-- 改動 3: 全部明細分頁容器 -->
        <div id="t1-all-pager"></div>
    </div>

    <!-- 需求 #3: 父子結構加泳道篩選 -->
    <div id="t1-panel-parent" class="sub-panel">
        <div style="font-size:0.78em; color:#888; margin-bottom:8px;">＊資料範圍：依目前篩選條件顯示，僅列出「父任務」（有子任務的卡片），點擊可展開子任務；含所有欄位（包含 DONE / Closed）</div>
        <div style="margin-bottom:10px">
            <label>依泳道篩選：</label>
            <select id="t1-parent-swim-filter" onchange="applyParentSwimFilter('t1')" style="padding:4px 8px;border-radius:4px;border:1px solid #ddd">
                <option value="">全部泳道</option>
            </select>
        </div>
        <div id="t1-parent-container"></div>
    </div>

    <!-- 需求 #3b: 圖表移到最底部 -->
    <div class="charts-container" id="t1-charts-container"></div>

    <div class="chart-box">
        <div class="chart-title">每週完成趨勢（近 12 週）</div>
        <div style="font-size:0.75em;color:#888;margin-bottom:6px;">＊全看板資料，不受篩選器影響；以 endAt 計算完成，以 createdAt 計算新增</div>
        <div class="chart-wrapper">
            <canvas id="chart-weekly-trend"></canvas>
        </div>
    </div>

</div>

<!-- ==================== TAB 2: 個人 & 細項追蹤 ==================== -->
<div id="main-panel-personal" class="main-panel">

    <div class="filter-bar">
        <div class="filter-item">
            <label>開始日期</label>
            <input type="date" id="t2-date-start" value="{DEFAULT_START}" onchange="applyFilters2()">
        </div>
        <div class="filter-item">
            <label>結束日期</label>
            <input type="date" id="t2-date-end" value="{DEFAULT_END}" onchange="applyFilters2()">
        </div>
        <div class="filter-item">
            <label>主題</label>
            <div class="picker-container">
                <button class="picker-btn" id="t2-swim-picker-btn">全部主題</button>
                <div class="picker-dropdown" id="t2-swim-picker-dropdown">
                    <div id="t2-swim-picker-items"></div>
                </div>
            </div>
        </div>
        <div class="filter-item">
            <label>標籤</label>
            <div class="picker-container">
                <button class="picker-btn" id="t2-label-picker-btn">全部標籤</button>
                <div class="picker-dropdown" id="t2-label-picker-dropdown">
                    <div id="t2-label-picker-items"></div>
                </div>
            </div>
        </div>
        <div class="filter-item">
            <label>成員</label>
            <div class="picker-container">
                <button class="picker-btn" id="t2-member-picker-btn">全部成員</button>
                <div class="picker-dropdown" id="t2-member-picker-dropdown">
                    <div id="t2-member-picker-items"></div>
                </div>
            </div>
        </div>
        <div class="filter-item">
            <label>狀態</label>
            <div class="picker-container">
                <button class="picker-btn" id="t2-status-picker-btn">全部狀態</button>
                <div class="picker-dropdown" id="t2-status-picker-dropdown">
                    <div id="t2-status-picker-items"></div>
                </div>
            </div>
        </div>
        <div class="filter-item">
            <label>封存狀態</label>
            <div class="picker-container">
                <button class="picker-btn" id="t2-archived-picker-btn">封存狀態</button>
                <div class="picker-dropdown" id="t2-archived-picker-dropdown">
                    <div id="t2-archived-picker-items"></div>
                </div>
            </div>
        </div>
        <div class="filter-item">
            <label>任務結構</label>
            <div class="picker-container">
                <button class="picker-btn" id="t2-tasktype-picker-btn">全部類型</button>
                <div class="picker-dropdown" id="t2-tasktype-picker-dropdown">
                    <div id="t2-tasktype-picker-items"></div>
                </div>
            </div>
        </div>
    </div>

    <!-- 需求 #7: 篩選 Chip 列 -->

    <!-- 需求 #7: 卡片計數說明 -->
    <div class="card-count-label" id="t2-card-count-label"></div>
    <div style="font-size:0.78em; color:#888; margin-top:4px; margin-bottom:2px;">* 停滯 = Pipeline 中（Doing / Waiting / Review / 使用者Test）超過 14 天無活動</div>

    <!-- 需求 #4: 個人泳道改為受篩選器控制 -->
    <div id="t2-focus-section" class="focus-section" style="display: none;">
        <div class="focus-title">👤 個人泳道專注分析</div>
        <div style="font-size:0.78em; color:#888; margin-bottom:8px;">＊資料範圍：包含 DONE / Closed（完成工作一併呈現），排除 Backlog / Goal＆專案資訊</div>
        <div id="t2-focus-content"></div>
    </div>

    <div id="t2-focus-placeholder" style="text-align: center; color: #999; padding: 40px;">
        💡 請在上方選擇「恰好 1 位成員」即可查看該成員的泳道專注分析
    </div>

    <!-- 改動 B2: Tab 2 子分頁按鈕加 badge -->
    <div class="sub-tab-bar">
        <button class="sub-tab-btn active" onclick="switchTab2('newdone')">📅 本週動態 <span class="tab-count" id="t2-cnt-newdone"></span></button>
        <button class="sub-tab-btn" onclick="switchTab2('all')">📋 全部明細 <span class="tab-count" id="t2-cnt-all"></span></button>
        <button class="sub-tab-btn" onclick="switchTab2('parent')">🌳 父子結構 <span class="tab-count" id="t2-cnt-parent"></span></button>
    </div>

    <!-- 改動 A3: 本週動態改為 mini-tab 三切換 -->
    <div id="t2-panel-newdone" class="sub-panel active">
        <div class="mini-tab-bar">
            <button class="mini-tab-btn active" id="t2-nd-btn-new" onclick="switchNewDone('t2','new')">
                本週新增 <span class="info-tip" data-tip="過去 7 天內新建立的卡片（以 createdAt 計算）">ℹ️</span><span class="mini-badge" id="t2-nd-badge-new">0</span>
            </button>
            <button class="mini-tab-btn" id="t2-nd-btn-done" onclick="switchNewDone('t2','done')">
                本週完成 <span class="info-tip" data-tip="過去 7 天內移入 DONE 欄位的卡片（以 endAt 計算）">ℹ️</span><span class="mini-badge" id="t2-nd-badge-done">0</span>
            </button>
            <button class="mini-tab-btn" id="t2-nd-btn-activity" onclick="switchNewDone('t2','activity')">
                本週有異動 <span class="info-tip" data-tip="過去 7 天內 dateLastActivity 有更新的卡片（排除 DONE / Closed / Backlog / Goal＆專案資訊）">ℹ️</span><span class="mini-badge" id="t2-nd-badge-activity">0</span>
            </button>
        </div>
        <div id="t2-nd-new">
            <div style="overflow-x:auto">
            <table id="t2-newdone-new-table" style="width:100%">
                <thead><tr>
                    <th>專案</th><th>卡片名稱</th><th>欄位</th><th>負責人</th><th>建立日</th>
                </tr></thead>
                <tbody></tbody>
            </table>
            </div>
        </div>
        <div id="t2-nd-done" style="display:none">
            <div style="overflow-x:auto">
            <table id="t2-newdone-done-table" style="width:100%">
                <thead><tr>
                    <th>專案</th><th>卡片名稱</th><th>負責人</th><th>完成日</th>
                </tr></thead>
                <tbody></tbody>
            </table>
            </div>
        </div>
        <div id="t2-nd-activity" style="display:none">
            <div style="overflow-x:auto">
            <table id="t2-newdone-activity-table" style="width:100%">
                <thead><tr>
                    <th>專案</th><th>卡片名稱</th><th>欄位</th><th>負責人</th><th>最後活動日</th>
                </tr></thead>
                <tbody></tbody>
            </table>
            </div>
        </div>
    </div>

    <div id="t2-panel-all" class="sub-panel">
        <div class="table-wrapper" style="max-height:70vh;overflow-y:auto;border:1px solid #e0e0e0;border-radius:4px;">
            <table id="t2-all-table">
                <thead>
                    <tr>
                        <th>專案</th>
                        <th>卡片名稱</th>
                        <th>負責人</th>
                        <th>建立日</th>
                        <th>最後活動日</th>
                        <th>停滯</th>
                        <th>Checklist進度</th>
                        <th>標籤</th>
                    </tr>
                </thead>
                <tbody></tbody>
            </table>
        </div>
        <!-- 改動 3: 全部明細分頁容器 -->
        <div id="t2-all-pager"></div>
    </div>

    <!-- 需求 #3: 父子結構加泳道篩選 -->
    <div id="t2-panel-parent" class="sub-panel">
        <div style="font-size:0.78em; color:#888; margin-bottom:8px;">＊資料範圍：依目前篩選條件顯示，僅列出「父任務」（有子任務的卡片），點擊可展開子任務；含所有欄位（包含 DONE / Closed）</div>
        <div id="t2-parent-container"></div>
    </div>

</div>

<script>
const WEKAN_URL_BASE = "{WEKAN_CARD_URL_BASE}";
const RAW = {data_json};

let filteredCards1 = [];
let filteredCards2 = [];

let chartListInstance = null;
let chartSwimInstance = null;
let chartMemberInstance = null;
let chartTrendInstance = null;

// 需求 #1 & #3: 子分頁控制
let riskSubTab = 'overview';
let t1SubTab = 'risk';
let t2SubTab = 'newdone';
let riskSwimFilter = '';

// 改動 1: Tab 2 Lazy Init
let tab2Initialized = false;

// 改動 2: 子分頁 Lazy Render
let t1DirtyPanels = new Set(['newdone','doing','risk','all','parent']);
let t2DirtyPanels = new Set(['newdone','all','parent']);
let t1FilterDates = {{ startDt: null, endDt: null }};
let t2FilterDates = {{ startDt: null, endDt: null }};

// 改動 3: 全部明細分頁
let t1AllPage = 1;
let t2AllPage = 1;
const PAGE_SIZE = 100;

// 改動 4: 父子結構 Lazy Expand
const parentGroupData = {{}};

// ==================== 初始化 ====================

function initFilters() {{
    // Tab 1 pickers
    const t1ListPicker = makePicker('t1-list-picker-dropdown','t1-list-picker-btn','t1-list-picker-items','全部欄位');
    const t1SwimPicker = makePicker('t1-swim-picker-dropdown','t1-swim-picker-btn','t1-swim-picker-items','全部主題');
    const t1LabelPicker = makePicker('t1-label-picker-dropdown','t1-label-picker-btn','t1-label-picker-items','全部標籤');
    const t1StatusPicker = makePicker('t1-status-picker-dropdown','t1-status-picker-btn','t1-status-picker-items','全部狀態');
    const t1ArchivedPicker = makePicker('t1-archived-picker-dropdown','t1-archived-picker-btn','t1-archived-picker-items','封存狀態');

    // Tab 2 pickers
    const t2SwimPicker = makePicker('t2-swim-picker-dropdown','t2-swim-picker-btn','t2-swim-picker-items','全部主題');
    const t2LabelPicker = makePicker('t2-label-picker-dropdown','t2-label-picker-btn','t2-label-picker-items','全部標籤');
    const t2MemberPicker = makePicker('t2-member-picker-dropdown','t2-member-picker-btn','t2-member-picker-items','全部成員');
    const t2StatusPicker = makePicker('t2-status-picker-dropdown','t2-status-picker-btn','t2-status-picker-items','全部狀態');
    const t2ArchivedPicker = makePicker('t2-archived-picker-dropdown','t2-archived-picker-btn','t2-archived-picker-items','封存狀態');
    const t2TaskTypePicker = makePicker('t2-tasktype-picker-dropdown','t2-tasktype-picker-btn','t2-tasktype-picker-items','全部類型');

    // Populate list picker (Tab 1 only)
    const DEFAULT_LIST_SELECTIONS = ['Goal＆專案資訊','Backlog','Ready to GO','Doing','Waiting','Review / 使用者Test','DONE','Closed'];
    const listsHtml = Object.entries(RAW.listsMap)
        .map(([id,name]) => {{
            const checked = DEFAULT_LIST_SELECTIONS.includes(name) ? 'checked' : '';
            return `<div class="picker-item"><input type="checkbox" value="${{id}}" ${{checked}} onchange="applyFilters1()"> ${{name}}</div>`;
        }})
        .join('');
    document.getElementById('t1-list-picker-items').innerHTML = listsHtml;

    // Populate swim pickers
    // DEFAULT_SWIM_SELECTIONS 從 team_config.json board.default_swim_selections 讀取
    // 空陣列 = 全選；有值 = 只預先勾選指定主題
    const DEFAULT_SWIM_SELECTIONS = {DEFAULT_SWIM_SEL_JSON};
    const swimsHtml = Object.entries(RAW.swimlanesMap)
        .map(([id,name]) => {{
            const checked = (DEFAULT_SWIM_SELECTIONS.length === 0 || DEFAULT_SWIM_SELECTIONS.includes(name)) ? 'checked' : '';
            return `<div class="picker-item"><input type="checkbox" value="${{id}}" ${{checked}} onchange="applyFilters1();applyFilters2()"> ${{name}}</div>`;
        }})
        .join('');
    document.getElementById('t1-swim-picker-items').innerHTML = swimsHtml;
    document.getElementById('t2-swim-picker-items').innerHTML = swimsHtml;

    // Populate label pickers（預設全選）
    const labelsHtml = Object.entries(RAW.labelsMap)
        .map(([id,name]) => `<div class="picker-item"><input type="checkbox" value="${{id}}" checked onchange="applyFilters1();applyFilters2()"> ${{name}}</div>`)
        .join('');
    document.getElementById('t1-label-picker-items').innerHTML = labelsHtml;
    document.getElementById('t2-label-picker-items').innerHTML = labelsHtml;

    // Populate member picker (Tab 2 only)
    const membersHtml = Object.entries(RAW.users)
        .map(([id,name]) => `<div class="picker-item"><input type="checkbox" value="${{id}}" onchange="applyFilters2()"> ${{name}}</div>`)
        .join('');
    document.getElementById('t2-member-picker-items').innerHTML = membersHtml;

    // Populate status pickers
    const statusOptions = [
        {{ key: 'doing',    label: 'Doing' }},
        {{ key: 'waiting',  label: 'Waiting' }},
        {{ key: 'review',   label: 'Review' }},
        {{ key: 'done',     label: 'DONE' }},
        {{ key: 'stale',    label: '停滯' }},
        {{ key: 'overdue',  label: '逾期' }},
        {{ key: 'nomember', label: '無負責人' }},
    ];
    const statusHtml = statusOptions
        .map(opt => `<div class="picker-item"><input type="checkbox" value="${{opt.key}}" checked onchange="applyFilters1();applyFilters2()"> ${{opt.label}}</div>`)
        .join('');
    document.getElementById('t1-status-picker-items').innerHTML = statusHtml;
    document.getElementById('t2-status-picker-items').innerHTML = statusHtml;

    // Populate archived pickers
    const archivedHtml = `
        <div class="picker-item"><input type="checkbox" id="t1-ack-active" value="active" onchange="applyFilters1()"> 未封存</div>
        <div class="picker-item"><input type="checkbox" id="t1-ack-archived" value="archived" onchange="applyFilters1()"> 已封存</div>
        <div class="picker-item"><input type="checkbox" id="t1-ack-all" value="all" onchange="applyFilters1()"> 全部</div>
    `;
    document.getElementById('t1-archived-picker-items').innerHTML = archivedHtml;
    document.getElementById('t1-ack-active').checked = true;

    const archivedHtml2 = `
        <div class="picker-item"><input type="checkbox" id="t2-ack-active" value="active" onchange="applyFilters2()"> 未封存</div>
        <div class="picker-item"><input type="checkbox" id="t2-ack-archived" value="archived" onchange="applyFilters2()"> 已封存</div>
        <div class="picker-item"><input type="checkbox" id="t2-ack-all" value="all" onchange="applyFilters2()"> 全部</div>
    `;
    document.getElementById('t2-archived-picker-items').innerHTML = archivedHtml2;
    document.getElementById('t2-ack-active').checked = true;

    // Populate task type picker (Tab 2 only)
    const taskTypeHtml = `
        <div class="picker-item"><input type="checkbox" value="parent" checked onchange="applyFilters2()"> 父任務</div>
        <div class="picker-item"><input type="checkbox" value="child" checked onchange="applyFilters2()"> 子任務</div>
        <div class="picker-item"><input type="checkbox" value="standalone" checked onchange="applyFilters2()"> 獨立任務</div>
    `;
    document.getElementById('t2-tasktype-picker-items').innerHTML = taskTypeHtml;

    // 需求 #3: 初始化父子結構泳道篩選下拉
    const swimOptions = Object.entries(RAW.swimlanesMap)
        .map(([id, name]) => `<option value="${{id}}">${{name}}</option>`)
        .join('');
    document.getElementById('t1-risk-swim-filter').innerHTML = '<option value="">全部泳道</option>' + swimOptions;
    document.getElementById('t1-parent-swim-filter').innerHTML = '<option value="">全部泳道</option>' + swimOptions;
    document.getElementById('t1-all-swim-filter').innerHTML = '<option value="">全部泳道</option>' + swimOptions;
    const t2ParentSwimEl = document.getElementById('t2-parent-swim-filter');
    if (t2ParentSwimEl) t2ParentSwimEl.innerHTML = '<option value="">全部泳道</option>' + swimOptions;

    // Close-outside-click handler for all dropdowns
    document.addEventListener('click', (e) => {{
        const dropdownIds = [
            't1-list-picker-dropdown', 't1-swim-picker-dropdown', 't1-label-picker-dropdown',
            't1-status-picker-dropdown', 't1-archived-picker-dropdown',
            't2-swim-picker-dropdown', 't2-label-picker-dropdown', 't2-member-picker-dropdown',
            't2-status-picker-dropdown', 't2-archived-picker-dropdown', 't2-tasktype-picker-dropdown'
        ];
        for (let id of dropdownIds) {{
            const el = document.getElementById(id);
            if (el && !el.contains(e.target) && !e.target.closest('.picker-btn')) {{
                el.classList.remove('open');
            }}
        }}
    }});

    // Initial apply (改動 1: Tab 2 延遲初始化)
    applyFilters1();
}}

// ==================== Picker Utility ====================

function makePicker(dropdownId, btnId, itemsId, placeholder) {{
    const dropdown = document.getElementById(dropdownId);
    const btn = document.getElementById(btnId);

    btn.addEventListener('click', (e) => {{
        e.stopPropagation();
        dropdown.classList.toggle('open');
    }});

    return {{ dropdown, btn }};
}}

// ==================== Main Tab Switch ====================

function switchMainTab(name) {{
    const tabs = document.querySelectorAll('.main-panel');
    const btns = document.querySelectorAll('.main-tab-btn');

    tabs.forEach(t => t.classList.remove('active'));
    btns.forEach(b => b.classList.remove('active'));

    if (name === 'overview') {{
        document.getElementById('main-panel-overview').classList.add('active');
        btns[0].classList.add('active');
    }} else {{
        document.getElementById('main-panel-personal').classList.add('active');
        btns[1].classList.add('active');
        // 改動 1: Tab 2 首次點擊時執行 applyFilters2
        if (!tab2Initialized) {{
            tab2Initialized = true;
            applyFilters2();
        }}
    }}
}}

// ==================== Sub-Tab Switch ====================

// 需求 #4: 展開/折疊父任務組
// 改動 4: toggleGroup 新增 Lazy Expand 支援
function toggleGroup(el, groupKey) {{
    const body = el.nextElementSibling;
    const isOpen = body.style.display !== 'none';
    if (!isOpen && body.innerHTML === '') {{
        // Lazy render children
        const children = parentGroupData[groupKey] || [];
        children.sort((a, b) => {{
            const sA = a.swimlane || ''; const sB = b.swimlane || '';
            if (sA !== sB) return sA.localeCompare(sB, 'zh-Hant');
            return new Date(a.createdAt) - new Date(b.createdAt);
        }});
        const rows = children.map(c => {{
            const staleClass = c.isStale ? 'stale-badge' : 'active-badge';
            const staleLabel = c.isDone ? '完成' : (c.isStale ? `停滯${{c.staleDays}}天` : '活躍');
            return `<tr>
                <td>${{c.swimlane || '—'}}</td>
                <td>${{cardLink(c.id, c.title)}}</td>
                <td><span class="badge">${{c.list}}</span></td>
                <td>${{c.members.join(', ') || '—'}}</td>
                <td>${{(c.dateLastActivity || '').slice(0, 10)}}</td>
                <td>${{c.staleDays != null ? c.staleDays : '—'}}</td>
                <td><span class="badge ${{staleClass}}">${{staleLabel}}</span></td>
            </tr>`;
        }}).join('');
        body.innerHTML = `<table><thead><tr>
            <th>專案</th><th>卡片名稱</th><th>欄位</th><th>負責人</th>
            <th>最後活動日</th><th>停滯天數</th><th>狀態</th>
        </tr></thead><tbody>${{rows}}</tbody></table>`;
    }}
    body.style.display = isOpen ? 'none' : '';
    const arrow = el.querySelector('.pg-arrow');
    if(arrow) arrow.textContent = isOpen ? '▶' : '▼';
}}

// 改動 A4: switchNewDone 函式
function switchNewDone(tab, name) {{
    ['new','done','activity'].forEach(n => {{
        const panel = document.getElementById(tab + '-nd-' + n);
        const btn = document.getElementById(tab + '-nd-btn-' + n);
        if (panel) panel.style.display = n === name ? '' : 'none';
        if (btn) btn.classList.toggle('active', n === name);
    }});
}}

// 改動 C5: switchTab1 - 只對 lazy 的分頁呼叫 renderT1Panel
function switchTab1(name) {{
    const panels = ['newdone', 'doing', 'risk', 'parent', 'all'];
    document.querySelectorAll('#main-panel-overview .sub-panel').forEach(p => p.classList.remove('active'));
    document.querySelectorAll('#main-panel-overview .sub-tab-btn').forEach(b => b.classList.remove('active'));

    if (panels.includes(name)) {{
        t1SubTab = name;
        document.getElementById(`t1-panel-${{name}}`).classList.add('active');
        event.target.classList.add('active');
        if (name === 'all' || name === 'parent') {{
            renderT1Panel(name);
        }}
    }}
}}

// 改動 C6: switchTab2 - 只對 lazy 的分頁呼叫 renderT2Panel
function switchTab2(name) {{
    const panels = ['newdone', 'all', 'parent'];
    document.querySelectorAll('#main-panel-personal .sub-panel').forEach(p => p.classList.remove('active'));
    document.querySelectorAll('#main-panel-personal .sub-tab-btn').forEach(b => b.classList.remove('active'));

    if (panels.includes(name)) {{
        t2SubTab = name;
        document.getElementById(`t2-panel-${{name}}`).classList.add('active');
        event.target.classList.add('active');
        if (name === 'all' || name === 'parent') {{
            renderT2Panel(name);
        }}
    }}
}}

// ==================== 改動 2: 子分頁 Lazy Render 函式 ====================

// 改動 C3: renderT1Panel - 只對 lazy 的分頁渲染
function renderT1Panel(name) {{
    if (!t1DirtyPanels.has(name)) return;
    const {{ startDt, endDt }} = t1FilterDates;
    if (!startDt) return;
    t1DirtyPanels.delete(name);
    if (name === 'all') renderAll1(filteredCards1);
    else if (name === 'parent') renderParentGroups('t1', filteredCards1);
}}

// 改動 C4: renderT2Panel - 只對 lazy 的分頁渲染
function renderT2Panel(name) {{
    if (!t2DirtyPanels.has(name)) return;
    const {{ startDt, endDt }} = t2FilterDates;
    if (!startDt) return;
    t2DirtyPanels.delete(name);
    if (name === 'all') renderAll2(filteredCards2);
    else if (name === 'parent') renderParentGroups('t2', filteredCards2);
}}

// 需求 #1: 風險分頁子分頁切換
function switchRiskSubTab(name) {{
    riskSubTab = name;
    const panels = document.querySelectorAll('#t1-panel-risk .sub-panel');
    const btns = document.querySelectorAll('#t1-panel-risk .sub-tab-btn');

    panels.forEach(p => p.classList.remove('active'));
    btns.forEach(b => b.classList.remove('active'));

    if (name === 'overview') {{
        document.getElementById('risk-subpanel-overview').classList.add('active');
    }} else if (name === 'swim') {{
        document.getElementById('risk-subpanel-swim').classList.add('active');
    }} else if (name === 'duesoon') {{
        document.getElementById('risk-subpanel-duesoon').classList.add('active');
    }}
    if (event && event.target) event.target.classList.add('active');
}}

function jumpToDueSoon() {{
    // 切到 Tab1 → 風險與停滯 → 即將到期 sub-tab
    switchMainTab('overview');
    switchTab1('risk');
    // 略過 event，直接操作
    const btns = document.querySelectorAll('#t1-panel-risk .sub-tab-btn');
    btns.forEach(b => b.classList.remove('active'));
    const dueSoonBtn = [...btns].find(b => b.textContent.includes('即將到期'));
    if (dueSoonBtn) dueSoonBtn.classList.add('active');
    document.querySelectorAll('#t1-panel-risk .sub-panel').forEach(p => p.classList.remove('active'));
    const panel = document.getElementById('risk-subpanel-duesoon');
    if (panel) panel.classList.add('active');
}}

// 需求 #1 & #3: 風險泳道篩選
function applyRiskSwimFilter() {{
    riskSwimFilter = document.getElementById('t1-risk-swim-filter').value;
    updateRiskTables(filteredCards1);
}}

// 全部明細泳道篩選
function applyAllSwimFilter(tabName) {{
    const swimId = document.getElementById(`${{tabName}}-all-swim-filter`).value;
    const cards = tabName === 't1' ? filteredCards1 : filteredCards2;
    const filtered = swimId ? cards.filter(c => c.swimlaneId === swimId) : cards;
    const tableId = `${{tabName}}-all-table`;
    const tbody = document.getElementById(tableId).querySelector('tbody');
    const sortedAll = sortBySwim(filtered);
    let html = '';
    sortedAll.forEach(c => {{
        const staleBadge = c.isStale
            ? `<span class="badge badge-stale">停滯${{c.staleDays}}天</span>`
            : '<span class="badge" style="background:#e8f5e9;color:#2e7d32;">活躍</span>';
        const clProgress = c.hasChecklist ? `${{c.clDone}}/${{c.clTotal}} (${{c.clPct}}%)` : '-';
        html += `<tr>
            <td>${{cardLink(c.id, c.title)}}</td>
            <td>${{c.swimlane}}</td>
            <td>${{c.members.join(', ') || '無'}}</td>
            <td>${{c.createdAt.split('T')[0]}}</td>
            <td>${{c.dateLastActivity.split('T')[0] || '-'}}</td>
            <td>${{staleBadge}}</td>
            <td>${{clProgress}}</td>
            <td>${{c.labels.join(', ') || '-'}}</td>
        </tr>`;
    }});
    tbody.innerHTML = html;
}}

// 需求 #3: 父子結構泳道篩選
function applyParentSwimFilter(tabName) {{
    const swimSel = document.getElementById(tabName+'-parent-swim-filter');
    const swimVal = swimSel ? swimSel.value : '';
    const cards = tabName==='t1' ? filteredCards1 : filteredCards2;
    const filtered = swimVal ? cards.filter(c=>c.swimlane===swimVal) : cards;
    renderParentGroups(tabName, filtered);
}}

// ==================== Swimlane Ordering ====================

// SWIM_ORDER 從 team_config.json board.swimlanes_order 讀取
// 空陣列 = 依 Wekan JSON 原始順序；有值 = 依指定順序排列
const SWIM_ORDER = {SWIM_ORDER_JSON};

function swimRank(name) {{
    if (SWIM_ORDER.length === 0) return 9999;   // 空 = 不強制排序
    const i = SWIM_ORDER.indexOf(name);
    return i >= 0 ? i : 9999;
}}

function sortBySwim(cards) {{
    return [...cards].sort((a,b) => {{
        const rA = swimRank(a.swimlane||'');
        const rB = swimRank(b.swimlane||'');
        if(rA !== rB) return rA - rB;
        return new Date(a.createdAt) - new Date(b.createdAt);
    }});
}}

// ==================== Filtering ====================

function getChecked(selector) {{
    return Array.from(document.querySelectorAll(selector))
        .filter(cb => cb.checked)
        .map(cb => cb.value);
}}

function applyFilters1() {{
    const startDt = new Date(document.getElementById('t1-date-start').value);
    const endDt = new Date(document.getElementById('t1-date-end').value);
    endDt.setHours(23, 59, 59, 999);

    const checkedLists = getChecked('#t1-list-picker-items input[type="checkbox"]');
    const checkedSwims = getChecked('#t1-swim-picker-items input[type="checkbox"]');
    const checkedLabels = getChecked('#t1-label-picker-items input[type="checkbox"]');
    const checkedStatuses = getChecked('#t1-status-picker-items input[type="checkbox"]');
    const checkedArchived = getChecked('#t1-archived-picker-items input[type="checkbox"]');

    filteredCards1 = RAW.cards.filter(c => {{
        // List filter
        if (checkedLists.length > 0 && !checkedLists.includes(c.listId)) return false;

        // Swim filter
        if (checkedSwims.length > 0 && !checkedSwims.includes(c.swimlaneId)) return false;

        // Label filter（有標籤的卡片才比對；全選=不限）
        if (checkedLabels.length > 0 && c.labels.length > 0) {{
            const hasLabel = c.labels.some(lbl => checkedLabels.some(lid => RAW.labelsMap[lid] === lbl));
            if (!hasLabel) return false;
        }}

        // Status filter（全選7項=不限）
        if (checkedStatuses.length > 0 && checkedStatuses.length < 7) {{
            const hasStatus = checkedStatuses.some(st => {{
                if (st === 'doing') return c.isDoing;
                if (st === 'waiting') return c.isWaiting;
                if (st === 'review') return c.isReview;
                if (st === 'done') return c.isDone;
                if (st === 'stale') return c.isStale;
                if (st === 'overdue') return c.isOverdue;
                if (st === 'nomember') return c.noMember;
                return false;
            }});
            if (!hasStatus) return false;
        }}

        // Archived filter
        if (checkedArchived.length > 0) {{
            const hasArch = checkedArchived.some(a => {{
                if (a === 'active') return !c.archived;
                if (a === 'archived') return c.archived;
                if (a === 'all') return true;
                return false;
            }});
            if (!hasArch) return false;
        }} else {{
            return !c.archived;
        }}

        return true;
    }});

    updateKPI(filteredCards1, startDt, endDt);
    updateCharts(filteredCards1, startDt, endDt);

    // 改動 C1: 輕量子分頁即時渲染（Method Y）
    t1FilterDates = {{ startDt, endDt }};
    renderNewDone1(filteredCards1, startDt, endDt);
    renderDoing1(filteredCards1);
    updateRiskTables(filteredCards1);
    updateTabBadges1(filteredCards1, startDt, endDt);
    // 重量子分頁標記 dirty，等使用者點擊再渲染
    t1DirtyPanels = new Set(['all', 'parent']);
    t1AllPage = 1;
    // 若目前在重量子分頁，立即渲染
    if (t1DirtyPanels.has(t1SubTab)) {{
        renderT1Panel(t1SubTab);
    }}
    renderFilterChips1(startDt, endDt, checkedLists, checkedSwims, checkedLabels, checkedStatuses);
}}

function applyFilters2() {{
    const startDt = new Date(document.getElementById('t2-date-start').value);
    const endDt = new Date(document.getElementById('t2-date-end').value);
    endDt.setHours(23, 59, 59, 999);

    const checkedSwims = getChecked('#t2-swim-picker-items input[type="checkbox"]');
    const checkedLabels = getChecked('#t2-label-picker-items input[type="checkbox"]');
    const checkedMembers = getChecked('#t2-member-picker-items input[type="checkbox"]');
    const checkedStatuses = getChecked('#t2-status-picker-items input[type="checkbox"]');
    const checkedArchived = getChecked('#t2-archived-picker-items input[type="checkbox"]');
    const checkedTaskTypes = getChecked('#t2-tasktype-picker-items input[type="checkbox"]');

    filteredCards2 = RAW.cards.filter(c => {{
        // Swim filter
        if (checkedSwims.length > 0 && !checkedSwims.includes(c.swimlaneId)) return false;

        // Label filter（有標籤的卡片才比對；全選=不限）
        if (checkedLabels.length > 0 && c.labels.length > 0) {{
            const hasLabel = c.labels.some(lbl => checkedLabels.some(lid => RAW.labelsMap[lid] === lbl));
            if (!hasLabel) return false;
        }}

        // Member filter
        if (checkedMembers.length > 0) {{
            const hasMember = c.members.some(m => checkedMembers.some(mid => RAW.users[mid] === m));
            if (!hasMember) return false;
        }}

        // Status filter（全選7項=不限）
        if (checkedStatuses.length > 0 && checkedStatuses.length < 7) {{
            const hasStatus = checkedStatuses.some(st => {{
                if (st === 'doing') return c.isDoing;
                if (st === 'waiting') return c.isWaiting;
                if (st === 'review') return c.isReview;
                if (st === 'done') return c.isDone;
                if (st === 'stale') return c.isStale;
                if (st === 'overdue') return c.isOverdue;
                if (st === 'nomember') return c.noMember;
                return false;
            }});
            if (!hasStatus) return false;
        }}

        // Archived filter
        if (checkedArchived.length > 0) {{
            const hasArch = checkedArchived.some(a => {{
                if (a === 'active') return !c.archived;
                if (a === 'archived') return c.archived;
                if (a === 'all') return true;
                return false;
            }});
            if (!hasArch) return false;
        }} else {{
            return !c.archived;
        }}

        // Task type filter（全選3項=不限）
        if (checkedTaskTypes.length > 0 && checkedTaskTypes.length < 3) {{
            const hasType = checkedTaskTypes.some(tt => {{
                if (tt === 'parent') return c.isParentTask;
                if (tt === 'child') return c.isChildTask;
                if (tt === 'standalone') return c.isStandalone;
                return false;
            }});
            if (!hasType) return false;
        }}

        return true;
    }});

    const focusMembers = checkedMembers;
    if (focusMembers.length === 1) {{
        updatePersonalFocus(focusMembers[0], filteredCards2, startDt, endDt);
    }} else {{
        document.getElementById('t2-focus-section').style.display = 'none';
        document.getElementById('t2-focus-placeholder').style.display = 'block';
    }}

    // 改動 C2: 輕量子分頁即時渲染（Method Y）
    t2FilterDates = {{ startDt, endDt }};
    renderNewDone2(filteredCards2, startDt, endDt);
    updateTabBadges2(filteredCards2, startDt, endDt);
    t2DirtyPanels = new Set(['all', 'parent']);
    t2AllPage = 1;
    if (t2DirtyPanels.has(t2SubTab)) {{
        renderT2Panel(t2SubTab);
    }}
    renderFilterChips2(startDt, endDt, checkedSwims, checkedLabels, checkedMembers, checkedStatuses);
}}

// ==================== Card Link Helper ====================

function cardLink(id, title) {{
    if (!WEKAN_URL_BASE) {{
        return `<span style="font-weight:500">${{title}}</span>`;
    }}
    return `<span style="font-weight:500">${{title}}<a href="${{WEKAN_URL_BASE}}/${{id}}" target="_blank" class="card-link-icon" onclick="event.stopPropagation()">🔗</a></span>`;
}}

// 改動 B4: updateTabBadges1 和 updateTabBadges2
function updateTabBadges1(cards, startDt, endDt) {{
    const newCount = cards.filter(c => {{ const d=new Date(c.createdAt); return d>=startDt&&d<=endDt; }}).length;
    const doneCount = cards.filter(c => {{ const d=c.endAt?new Date(c.endAt):null; return c.isDone&&d&&d>=startDt&&d<=endDt; }}).length;
    const ACT_EX1 = ['DONE','Closed','Backlog','Goal＆專案資訊'];
    const actCount = cards.filter(c => {{
        const d=c.dateLastActivity?new Date(c.dateLastActivity):null;
        if(!d||d<startDt||d>endDt) return false;
        if(ACT_EX1.includes(c.list)) return false;
        const isNew = new Date(c.createdAt)>=startDt;
        const isDoneW = c.isDone&&c.endAt&&new Date(c.endAt)>=startDt;
        return !isNew&&!isDoneW;
    }}).length;
    const setBadge = (id, n) => {{ const el=document.getElementById(id); if(el) el.textContent=n>0?n:''; }};
    setBadge('t1-nd-badge-new', newCount);
    setBadge('t1-nd-badge-done', doneCount);
    setBadge('t1-nd-badge-activity', actCount);
    const ndTotal = newCount + doneCount + actCount;
    setBadge('t1-cnt-newdone', ndTotal > 0 ? ndTotal : '');
    setBadge('t1-cnt-doing', cards.filter(c=>c.isDoing).length || '');
    const riskCount = cards.filter(c=>!['DONE','Closed','過往卡片','過往卡片待青','Goal＆專案資訊'].includes(c.list)&&!c.archived&&c.isStale).length;
    setBadge('t1-cnt-risk', riskCount || '');
    setBadge('t1-cnt-parent', cards.filter(c=>c.isParentTask).length || '');
    setBadge('t1-cnt-all', cards.length || '');
}}

function updateTabBadges2(cards, startDt, endDt) {{
    const newCount = cards.filter(c => {{ const d=new Date(c.createdAt); return d>=startDt&&d<=endDt; }}).length;
    const doneCount = cards.filter(c => {{ const d=c.endAt?new Date(c.endAt):null; return c.isDone&&d&&d>=startDt&&d<=endDt; }}).length;
    const ACT_EX2 = ['DONE','Closed','Backlog','Goal＆專案資訊'];
    const actCount = cards.filter(c => {{
        const d=c.dateLastActivity?new Date(c.dateLastActivity):null;
        if(!d||d<startDt||d>endDt) return false;
        if(ACT_EX2.includes(c.list)) return false;
        const isNew = new Date(c.createdAt)>=startDt;
        const isDoneW = c.isDone&&c.endAt&&new Date(c.endAt)>=startDt;
        return !isNew&&!isDoneW;
    }}).length;
    const setBadge = (id, n) => {{ const el=document.getElementById(id); if(el) el.textContent=n>0?n:''; }};
    setBadge('t2-nd-badge-new', newCount);
    setBadge('t2-nd-badge-done', doneCount);
    setBadge('t2-nd-badge-activity', actCount);
    const ndTotal = newCount + doneCount + actCount;
    setBadge('t2-cnt-newdone', ndTotal > 0 ? ndTotal : '');
    setBadge('t2-cnt-all', cards.length || '');
    setBadge('t2-cnt-parent', cards.filter(c=>c.isParentTask).length || '');
}}

// ==================== KPI Update ====================

function updateKPI(cards, startDt, endDt) {{
    const newCount = cards.filter(c => {{
        const ct = new Date(c.createdAt);
        return ct >= startDt && ct <= endDt;
    }}).length;

    const doneCount = cards.filter(c => {{
        const et = c.endAt ? new Date(c.endAt) : null;
        return c.isDone && et && et >= startDt && et <= endDt;
    }}).length;

    const doingCount = cards.filter(c => c.isDoing).length;
    const waitingCount = cards.filter(c => c.isWaiting).length;
    const reviewCount = cards.filter(c => c.isReview).length;
    const staleCount = cards.filter(c => c.isStale).length;
    const noMemberCount = cards.filter(c => c.noMember && c.inPipeline).length;

    const backlogCount = RAW.cards.filter(c =>
        (RAW.listCategories.BACKLOG.includes(c.listId) || RAW.listCategories.READY.includes(c.listId)) && !c.archived
    ).length;

    const dueSoonCount = RAW.cards.filter(c => c.isDueSoon && !c.archived).length;

    const kpiHtml = `
        <div class="kpi-card">
            <div class="kpi-label">本週新增 <span class="info-tip" data-tip="過去 7 天內新建立的卡片（以 createdAt 計算）">ℹ️</span></div>
            <div class="kpi-value">${{newCount}}</div>
        </div>
        <div class="kpi-card">
            <div class="kpi-label">本週完成 <span class="info-tip" data-tip="過去 7 天內移入 DONE 欄位的卡片（以 endAt 計算）">ℹ️</span></div>
            <div class="kpi-value">${{doneCount}}</div>
        </div>
        <div class="kpi-card">
            <div class="kpi-label">Doing</div>
            <div class="kpi-value">${{doingCount}}</div>
        </div>
        <div class="kpi-card">
            <div class="kpi-label">Waiting</div>
            <div class="kpi-value">${{waitingCount}}</div>
        </div>
        <div class="kpi-card">
            <div class="kpi-label">Review</div>
            <div class="kpi-value">${{reviewCount}}</div>
        </div>
        <div class="kpi-card alert">
            <div class="kpi-label">停滯卡片 <span class="info-tip" data-tip="停滯定義：卡片在 Pipeline（Doing / Waiting / Review）中，超過 14 天無任何活動（以最後活動日計算）">ℹ️</span></div>
            <div class="kpi-value">${{staleCount}}</div>
        </div>
        <div class="kpi-card alert">
            <div class="kpi-label">無負責人</div>
            <div class="kpi-value">${{noMemberCount}}</div>
        </div>
        <div class="kpi-card warn">
            <div class="kpi-label">待辦積壓 <span class="info-tip" data-tip="待辦積壓 = Backlog + Ready to GO 中尚未封存的卡片數，代表尚未進入執行流程的需求量">ℹ️</span></div>
            <div class="kpi-value">${{backlogCount}}</div>
        </div>
        <div class="kpi-card" style="border-top:3px solid #f57f17; cursor:pointer;" onclick="jumpToDueSoon()" title="點擊查看明細">
            <div class="kpi-label">⚡ 即將到期 <span class="info-tip" data-tip="dueAt 在 {TODAY_DISPLAY} – {DUE_SOON_END_DISPLAY} 之間的卡片（排除 DONE / Closed；全看板計算，不受篩選器影響；以本儀表板產出日為基準）">ℹ️</span></div>
            <div class="kpi-value">${{dueSoonCount}}</div>
        </div>
    `;

    document.getElementById('t1-kpi-row').innerHTML = kpiHtml;
}}

// ==================== Charts Update ====================

function updateCharts(cards, startDt, endDt) {{
    // Chart 1: List Distribution（含所有欄位，包含 DONE / Closed）
    const listCounts = {{}};
    cards.forEach(c => {{
        listCounts[c.list] = (listCounts[c.list] || 0) + 1;
    }});

    // 依流程順序排列（從 team_config.json board.lists_order 讀取；空陣列 = 依 Wekan JSON 原始順序）
    const LIST_ORDER = {LIST_ORDER_JSON};
    const sortedLists = Object.keys(listCounts).sort((a, b) => {{
        const ia = LIST_ORDER.indexOf(a);
        const ib = LIST_ORDER.indexOf(b);
        return (ia === -1 ? 999 : ia) - (ib === -1 ? 999 : ib);
    }});
    const listLabels = sortedLists;
    const listData = sortedLists.map(l => listCounts[l]);

    // Chart 2: Swimlane Completion
    const swimStats = {{}};
    RAW.cards.forEach(c => {{
        if (!swimStats[c.swimlane]) {{
            swimStats[c.swimlane] = {{ total: 0, done: 0, stale: 0 }};
        }}
        swimStats[c.swimlane].total++;
        if (c.isDone) swimStats[c.swimlane].done++;
        if (c.isStale) swimStats[c.swimlane].stale++;
    }});

    const swimLabels = Object.keys(swimStats);
    const swimDoneData = swimLabels.map(s => Math.round(swimStats[s].done * 100 / swimStats[s].total));
    const swimStaleData = swimLabels.map(s => swimStats[s].stale);

    // Chart 3: Member Workload
    const memberStats = {{}};
    cards.forEach(c => {{
        c.members.forEach(m => {{
            if (!memberStats[m]) {{
                memberStats[m] = {{ total: 0, doing: 0, stale: 0 }};
            }}
            memberStats[m].total++;
            if (c.isDoing) memberStats[m].doing++;
            if (c.isStale) memberStats[m].stale++;
        }});
    }});

    const memberLabels = Object.keys(memberStats).slice(0, 10);
    const memberTotalData = memberLabels.map(m => memberStats[m].total);
    const memberDoingData = memberLabels.map(m => memberStats[m].doing);
    const memberStaleData = memberLabels.map(m => memberStats[m].stale);

    const chartsHtml = `
        <div class="chart-box">
            <div class="chart-title">流程欄位分布</div>
            <div style="font-size:0.75em;color:#888;margin-bottom:6px;">＊依目前篩選條件，含所有欄位（包含 DONE / Closed）</div>
            <div class="chart-wrapper">
                <canvas id="chart-list"></canvas>
            </div>
        </div>
        <div class="chart-box">
            <div class="chart-title">主題完成率 vs 停滯率</div>
            <div style="font-size:0.75em;color:#888;margin-bottom:6px;">＊全看板資料，不受篩選器影響</div>
            <div class="chart-wrapper">
                <canvas id="chart-swim"></canvas>
            </div>
        </div>
        <div class="chart-box">
            <div class="chart-title">成員工作量分布</div>
            <div style="font-size:0.75em;color:#888;margin-bottom:6px;">＊依目前篩選條件（持有 = 所有未封存卡片；Doing / 停滯 依同篩選條件）</div>
            <div class="chart-wrapper">
                <canvas id="chart-member"></canvas>
            </div>
        </div>
    `;

    document.getElementById('t1-charts-container').innerHTML = chartsHtml;

    setTimeout(() => {{
        // List chart
        const ctxList = document.getElementById('chart-list')?.getContext('2d');
        if (ctxList) {{
            if (chartListInstance) chartListInstance.destroy();
            chartListInstance = new Chart(ctxList, {{
                type: 'bar',
                data: {{
                    labels: listLabels,
                    datasets: [{{
                        label: '卡片數',
                        data: listData,
                        backgroundColor: '#1d4ed8'
                    }}]
                }},
                options: {{
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {{ legend: {{ display: false }} }},
                    scales: {{ y: {{ beginAtZero: true }} }}
                }}
            }});
        }}

        // Swim chart
        const ctxSwim = document.getElementById('chart-swim')?.getContext('2d');
        if (ctxSwim) {{
            if (chartSwimInstance) chartSwimInstance.destroy();
            chartSwimInstance = new Chart(ctxSwim, {{
                type: 'bar',
                data: {{
                    labels: swimLabels,
                    datasets: [
                        {{
                            label: '完成率 (%)',
                            data: swimDoneData,
                            backgroundColor: '#4caf50',
                            yAxisID: 'y'
                        }},
                        {{
                            label: '停滯數',
                            data: swimStaleData,
                            backgroundColor: '#f44336',
                            yAxisID: 'y1'
                        }}
                    ]
                }},
                options: {{
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {{ legend: {{ display: true }} }},
                    scales: {{
                        y: {{ type: 'linear', position: 'left' }},
                        y1: {{ type: 'linear', position: 'right' }}
                    }}
                }}
            }});
        }}

        // Member chart
        const ctxMember = document.getElementById('chart-member')?.getContext('2d');
        if (ctxMember) {{
            if (chartMemberInstance) chartMemberInstance.destroy();
            chartMemberInstance = new Chart(ctxMember, {{
                type: 'bar',
                data: {{
                    labels: memberLabels,
                    datasets: [
                        {{ label: '持有', data: memberTotalData, backgroundColor: '#1d4ed8' }},
                        {{ label: 'Doing', data: memberDoingData, backgroundColor: '#ff9800' }},
                        {{ label: '停滯', data: memberStaleData, backgroundColor: '#f44336' }}
                    ]
                }},
                options: {{
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {{ legend: {{ display: true }} }},
                    scales: {{ y: {{ beginAtZero: true }} }}
                }}
            }});
        }}

        // Weekly trend
        const ctxTrend = document.getElementById('chart-weekly-trend')?.getContext('2d');
        if (ctxTrend) {{
            if (chartTrendInstance) chartTrendInstance.destroy();
            chartTrendInstance = new Chart(ctxTrend, {{
                type: 'line',
                data: {{
                    labels: RAW.weeklyTrend.map(w => w.label),
                    datasets: [
                        {{
                            label: '完成',
                            data: RAW.weeklyTrend.map(w => w.completed),
                            borderColor: '#4caf50',
                            backgroundColor: 'rgba(76,175,80,0.1)',
                            tension: 0.3
                        }},
                        {{
                            label: '新增',
                            data: RAW.weeklyTrend.map(w => w.new),
                            borderColor: '#ff9800',
                            backgroundColor: 'rgba(255,152,0,0.1)',
                            tension: 0.3
                        }}
                    ]
                }},
                options: {{
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {{ legend: {{ display: true }} }},
                    scales: {{ y: {{ beginAtZero: true }} }}
                }}
            }});
        }}
    }}, 100);
}}

// ==================== Swimlane Grouping ====================

function toggleSwimGroup(gid) {{
    const children = document.querySelectorAll(`.swim-child-${{gid}}`);
    children.forEach(row => {{
        row.style.display = row.style.display === 'none' ? 'table-row' : 'none';
    }});
}}

// ==================== Table 1 (Overview) ====================

// 風險分析排除 List（從 team_config.json lists_roles 推導：done + closed + info）
const RISK_EXCLUDE_LISTS = {RISK_EXCLUDE_JSON};
function isRiskCard(c) {{
    if (RISK_EXCLUDE_LISTS.includes(c.list)) return false;
    if (c.archived) return false;
    return true;
}}

// ── 風險摘要卡（Feature A-1）─────────────────────────────
function buildRiskSummary(riskCards) {{
    const total = riskCards.length;
    if (total === 0) {{
        return '<div class="risk-summary ok"><span class="risk-summary-title">✅ 目前篩選範圍內無風險卡片</span></div>';
    }}

    const n0 = riskCards.filter(c => c.isOverdue).length;
    const n1 = riskCards.filter(c => c.isDueSoon).length;
    const n2 = riskCards.filter(c => c.isStale).length;
    const n3 = riskCards.filter(c => c.noMember).length;

    // 主題集中度（top 2）
    const swimCount = {{}};
    riskCards.forEach(c => {{ swimCount[c.swimlane] = (swimCount[c.swimlane] || 0) + 1; }});
    const topSwims = Object.entries(swimCount).sort((a, b) => b[1] - a[1]).slice(0, 2);

    // 成員集中度（top 2，排除「無負責人」卡片）
    const memberCount = {{}};
    riskCards.forEach(c => {{
        c.members.forEach(m => {{ memberCount[m] = (memberCount[m] || 0) + 1; }});
    }});
    const topMembers = Object.entries(memberCount).sort((a, b) => b[1] - a[1]).slice(0, 2);

    const swimStr = topSwims.map(([s, n]) => `<strong>${{s}}</strong>（${{n}} 張）`).join('、');
    const memberStr = topMembers.length
        ? topMembers.map(([m, n]) => `<strong>${{m}}</strong>（${{n}} 張）`).join('、') + ' 有最多待處理風險'
        : '所有風險卡片皆有負責人';

    return `<div class="risk-summary warn">
        <span class="risk-summary-title">⚠️ 風險摘要 <span style="font-weight:400;font-size:0.88em;color:#8d6e63;">（依目前篩選條件）</span></span>
        <div class="risk-summary-row">
            <span class="risk-summary-label">總計</span>
            <span>共 <strong>${{total}}</strong> 個風險卡片（逾期 ${{n0}} ｜ 即將到期 ${{n1}} ｜ 停滯 ${{n2}} ｜ 無負責人 ${{n3}}）</span>
        </div>
        ${{topSwims.length ? `<div class="risk-summary-row"><span class="risk-summary-label">集中在</span><span>${{swimStr}}</span></div>` : ''}}
        <div class="risk-summary-row"><span class="risk-summary-label">成員</span><span>${{memberStr}}</span></div>
    </div>`;
}}

function updateRiskTables(cards) {{
    const riskCards = cards.filter(c => isRiskCard(c) && (c.isStale || c.isOverdue || c.noMember || c.isDueSoon));

    // 更新風險摘要卡
    const summaryEl = document.getElementById('risk-summary-box');
    if (summaryEl) summaryEl.innerHTML = buildRiskSummary(riskCards);

    // 總覽風險：逾期(0) → 即將到期(1) → 停滯(2,天數遞減) → 無負責人(3)
    const riskTypeRank = c => c.isOverdue ? 0 : c.isDueSoon ? 1 : c.isStale ? 2 : 3;
    const sortedRisk = riskCards.sort((a, b) => {{
        const rankDiff = riskTypeRank(a) - riskTypeRank(b);
        if (rankDiff !== 0) return rankDiff;
        // 同為即將到期：dueAt 由近到遠
        if (a.isDueSoon && b.isDueSoon) return new Date(a.dueAt) - new Date(b.dueAt);
        // 同為停滯：天數由多到少
        if (a.isStale && b.isStale) return (b.staleDays || 0) - (a.staleDays || 0);
        return 0;
    }});

    function buildRiskBadges(c) {{
        const badges = [];
        if (c.isOverdue)  badges.push('<span class="badge" style="background:#ffebee;color:#c62828;">逾期</span>');
        if (c.isDueSoon)  badges.push(`<span class="badge badge-due-soon">⚡ ${{c.dueAtDisplay}}</span>`);
        if (c.isStale)    badges.push('<span class="badge badge-stale">停滯</span>');
        if (c.noMember)   badges.push('<span class="badge" style="background:#fff3e0;color:#e65100;">無負責</span>');
        return badges.join(' ') || '-';
    }}

    let riskOverviewHtml = '';
    sortedRisk.forEach(c => {{
        const clProgress = c.hasChecklist ? `${{c.clDone}}/${{c.clTotal}} (${{c.clPct}}%)` : '-';
        riskOverviewHtml += `<tr>
            <td>${{c.swimlane}}</td>
            <td>${{cardLink(c.id, c.title)}}</td>
            <td>${{c.dueAtDisplay || '-'}}</td>
            <td>${{c.staleDays || '-'}}</td>
            <td><span class="badge">${{c.list}}</span></td>
            <td>${{c.members.join(', ') || '無'}}</td>
            <td>${{c.dateLastActivity.split('T')[0] || '-'}}</td>
            <td>${{clProgress}}</td>
            <td>${{buildRiskBadges(c)}}</td>
        </tr>`;
    }});
    document.getElementById('t1-risk-overview-table').querySelector('tbody').innerHTML = riskOverviewHtml;

    // 泳道篩選：依 riskSwimFilter，排序同上
    const swimmingRisk = riskSwimFilter ? sortedRisk.filter(c => c.swimlaneId === riskSwimFilter) : sortedRisk;
    let riskSwimHtml = '';
    swimmingRisk.forEach(c => {{
        const clProgress = c.hasChecklist ? `${{c.clDone}}/${{c.clTotal}} (${{c.clPct}}%)` : '-';
        riskSwimHtml += `<tr>
            <td>${{c.swimlane}}</td>
            <td>${{cardLink(c.id, c.title)}}</td>
            <td>${{c.dueAtDisplay || '-'}}</td>
            <td>${{c.staleDays || '-'}}</td>
            <td><span class="badge">${{c.list}}</span></td>
            <td>${{c.members.join(', ') || '無'}}</td>
            <td>${{c.dateLastActivity.split('T')[0] || '-'}}</td>
            <td>${{clProgress}}</td>
            <td>${{buildRiskBadges(c)}}</td>
        </tr>`;
    }});
    document.getElementById('t1-risk-swim-table').querySelector('tbody').innerHTML = riskSwimHtml;

    // 即將到期分頁：使用全看板 RAW.cards（不受篩選器影響），與 KPI 9 對齊
    const dueSoonCards = RAW.cards.filter(c => isRiskCard(c) && c.isDueSoon && !c.archived)
        .sort((a, b) => new Date(a.dueAt) - new Date(b.dueAt));
    let dueSoonHtml = '';
    dueSoonCards.forEach(c => {{
        dueSoonHtml += `<tr>
            <td>${{c.swimlane}}</td>
            <td>${{cardLink(c.id, c.title)}}</td>
            <td><strong>${{c.dueAtDisplay || '-'}}</strong></td>
            <td><span class="badge">${{c.list}}</span></td>
            <td>${{c.members.join(', ') || '無'}}</td>
            <td>${{c.dateLastActivity.split('T')[0] || '-'}}</td>
            <td>${{buildRiskBadges(c)}}</td>
        </tr>`;
    }});
    if (!dueSoonHtml) dueSoonHtml = '<tr><td colspan="7" style="text-align:center;color:#999">目前無即將到期的卡片</td></tr>';
    const dueSoonTbl = document.getElementById('t1-risk-duesoon-table');
    if (dueSoonTbl) dueSoonTbl.querySelector('tbody').innerHTML = dueSoonHtml;
}}

// ==================== 改動 2: updateTables1 拆解函式 ====================

function renderNewDone1(cards, startDt, endDt) {{
    // 本週新增／完成／有異動：三欄並排
    const newCards = sortBySwim(cards.filter(c => {{
        const ct = new Date(c.createdAt);
        return ct >= startDt && ct <= endDt;
    }}));
    let newHtml = '';
    newCards.forEach(c => {{
        newHtml += `<tr>
            <td>${{c.swimlane||'—'}}</td>
            <td>${{cardLink(c.id, c.title)}}</td>
            <td><span class="badge">${{c.list}}</span></td>
            <td>${{c.members.join(', ') || '無'}}</td>
            <td>${{c.createdAt.split('T')[0]}}</td>
        </tr>`;
    }});
    document.getElementById('t1-newdone-new-table').querySelector('tbody').innerHTML = newHtml;

    const doneCards = sortBySwim(cards.filter(c => {{
        const et = c.endAt ? new Date(c.endAt) : null;
        return c.isDone && et && et >= startDt && et <= endDt;
    }}));
    let doneHtml = '';
    doneCards.forEach(c => {{
        const et = new Date(c.endAt);
        doneHtml += `<tr>
            <td>${{c.swimlane||'—'}}</td>
            <td>${{cardLink(c.id, c.title)}}</td>
            <td>${{c.members.join(', ') || '無'}}</td>
            <td>${{et.toISOString().split('T')[0]}}</td>
        </tr>`;
    }});
    document.getElementById('t1-newdone-done-table').querySelector('tbody').innerHTML = doneHtml;

    // 本週有異動（排除 done + closed + backlog + info），依最後活動日由新到舊
    const ACT_EXCLUDE = {ACT_EXCLUDE_JSON};
    const actCards = cards.filter(c => {{
        if (!c.dateLastActivity) return false;
        if (ACT_EXCLUDE.includes(c.list)) return false;
        const dt = new Date(c.dateLastActivity);
        return dt >= startDt && dt <= endDt;
    }}).sort((a, b) => new Date(b.dateLastActivity) - new Date(a.dateLastActivity));
    const actHtml = actCards.map(c => `<tr>
        <td>${{c.swimlane||'—'}}</td>
        <td>${{cardLink(c.id,c.title)}}</td>
        <td><span class="badge">${{c.list}}</span></td>
        <td>${{c.members.join(', ')||'—'}}</td>
        <td>${{(c.dateLastActivity||'').slice(0,10)}}</td>
    </tr>`).join('') || '<tr><td colspan="5" style="text-align:center;color:#999">本週無異動卡片</td></tr>';
    const actTbl = document.getElementById('t1-newdone-activity-table');
    if(actTbl) actTbl.querySelector('tbody').innerHTML = actHtml;
}}

function renderDoing1(cards) {{
    // Doing 明細：扁平清單
    const doingCards = cards.filter(c => c.isDoing);
    let doingHtml = '';
    doingCards.forEach(c => {{
        const staleBadge = c.isStale ? `<span class="badge badge-stale">停滯${{c.staleDays}}天</span>` :
                          '<span class="badge" style="background:#e8f5e9;color:#2e7d32;">活躍</span>';
        const dueSoonBadge = c.isDueSoon ? `<span class="badge badge-due-soon">⚡ ${{c.dueAtDisplay}}</span>` : '';
        doingHtml += `<tr>
            <td>${{c.swimlane}}</td>
            <td>${{cardLink(c.id, c.title)}}</td>
            <td>${{c.staleDays || '-'}}</td>
            <td><span class="badge badge-doing">${{c.list}}</span></td>
            <td>${{c.members.join(', ') || '無'}}</td>
            <td>${{c.dateLastActivity.split('T')[0] || '-'}}</td>
            <td>${{dueSoonBadge}}${{staleBadge}}</td>
        </tr>`;
    }});
    document.getElementById('t1-doing-table').querySelector('tbody').innerHTML = doingHtml;
}}

function renderAll1(cards) {{
    // 改動 3: 分頁邏輯
    const total = cards.length;
    const totalPages = Math.ceil(total / PAGE_SIZE) || 1;
    if (t1AllPage > totalPages) t1AllPage = totalPages;
    const pageCards = cards.slice((t1AllPage - 1) * PAGE_SIZE, t1AllPage * PAGE_SIZE);

    const sortedAll = sortBySwim(pageCards);
    let allHtml = '';
    sortedAll.forEach(c => {{
        const staleBadge = c.isStale ? `<span class="badge badge-stale">停滯${{c.staleDays}}天</span>` :
                          '<span class="badge" style="background:#e8f5e9;color:#2e7d32;">活躍</span>';
        const clProgress = c.hasChecklist ? `${{c.clDone}}/${{c.clTotal}} (${{c.clPct}}%)` : '-';
        const labelsStr = c.labels.length > 0 ? c.labels.join(', ') : '-';
        allHtml += `<tr>
            <td>${{c.swimlane}}</td>
            <td>${{cardLink(c.id, c.title)}}</td>
            <td>${{c.members.join(', ') || '無'}}</td>
            <td>${{c.createdAt.split('T')[0]}}</td>
            <td>${{c.dateLastActivity.split('T')[0] || '-'}}</td>
            <td>${{staleBadge}}</td>
            <td>${{clProgress}}</td>
            <td>${{labelsStr}}</td>
        </tr>`;
    }});

    const pageHtml = `<div style="display:flex;align-items:center;gap:12px;padding:8px 0;font-size:13px;">
        <button onclick="t1AllPage=Math.max(1,t1AllPage-1);renderAll1(filteredCards1)" ${{t1AllPage<=1?'disabled':''}}>‹ 上一頁</button>
        <span>第 ${{t1AllPage}} / ${{totalPages}} 頁（共 ${{total}} 筆）</span>
        <button onclick="t1AllPage=Math.min(${{totalPages}},t1AllPage+1);renderAll1(filteredCards1)" ${{t1AllPage>=totalPages?'disabled':''}}>下一頁 ›</button>
    </div>`;

    document.getElementById('t1-all-table').querySelector('tbody').innerHTML = allHtml;
    const pagerEl = document.getElementById('t1-all-pager');
    if (pagerEl) pagerEl.innerHTML = pageHtml;
}}

function updateTables1(cards, startDt, endDt) {{
    // 舊邏輯已移至各函式，此函式已不被調用（由 renderT1Panel 替代）
}}

// 改動 4: renderParentGroups 懶加載展開式群組
function renderParentGroups(tabName, cards) {{
    const containerId = tabName + '-parent-container';
    const container = document.getElementById(containerId);
    if(!container) return;

    // 找出所有父任務（有子卡片且自身無 parentId）
    const parentCards = cards.filter(c => c.isParentTask);
    const childrenOf = {{}};
    cards.filter(c => c.isChildTask && c.parentId).forEach(c => {{
        if(!childrenOf[c.parentId]) childrenOf[c.parentId] = [];
        childrenOf[c.parentId].push(c);
    }});

    // 無父任務的卡片
    const standaloneCards = cards.filter(c => c.isStandalone);

    let html = '';
    parentCards.forEach(p => {{
        const children = childrenOf[p.id] || [];
        if(children.length === 0) return;
        const groupKey = tabName + '__' + p.id;
        parentGroupData[groupKey] = children;
        const done = children.filter(c => c.isDone).length;
        html += `<div class="parent-group">
            <div class="parent-group-header" onclick="toggleGroup(this,'${{groupKey}}')" style="cursor:pointer">
                <span class="pg-arrow">▶</span>
                父任務：${{p.title}}（${{children.length}} 項）[完成率：${{done}}/${{children.length}}]
            </div>
            <div class="parent-group-body" style="display:none"></div>
        </div>`;
    }});

    // 獨立卡片群組
    if(standaloneCards.length > 0) {{
        const groupKey = tabName + '__standalone';
        parentGroupData[groupKey] = standaloneCards;
        const done = standaloneCards.filter(c => c.isDone).length;
        html += `<div class="parent-group">
            <div class="parent-group-header" onclick="toggleGroup(this,'${{groupKey}}')" style="cursor:pointer">
                <span class="pg-arrow">▶</span>
                獨立卡片（${{standaloneCards.length}} 項）[完成率：${{done}}/${{standaloneCards.length}}]
            </div>
            <div class="parent-group-body" style="display:none"></div>
        </div>`;
    }}

    if(!html) html = '<p style="color:#999;padding:16px">無資料</p>';
    container.innerHTML = html;
}}

function updateT1ParentTable(cards, swimFilter) {{
    renderParentGroups('t1', cards);
}}

// ==================== Personal Focus ====================

// 需求 #4: 個人泳道改為受篩選器控制 + 完成率
function updatePersonalFocus(memberId, filteredCards, startDt, endDt) {{
    const memberName = RAW.users[memberId] || memberId;
    const memberSwims = {{}};

    // 只顯示在選取時間範圍內有異動（dateLastActivity 落在區間）的卡片
    // 個人泳道專注分析：包含 DONE / Closed（完成工作需要呈現），排除 backlog + info
    const FOCUS_EXCLUDE = {FOCUS_EXCLUDE_JSON};
    const hasDateFilter = !isNaN(startDt) && !isNaN(endDt);
    filteredCards.forEach(c => {{
        const hasMem = c.members.some(m => RAW.users[memberId] === m);
        if (!hasMem) return;
        if (FOCUS_EXCLUDE.includes(c.list)) return;
        if (hasDateFilter) {{
            const at = c.dateLastActivity ? new Date(c.dateLastActivity) : null;
            if (!at || at < startDt || at > endDt) return;
        }}
        if (!memberSwims[c.swimlane]) memberSwims[c.swimlane] = [];
        memberSwims[c.swimlane].push(c);
    }});

    let focusHtml = '';
    Object.entries(memberSwims).forEach(([swim, swCards]) => {{
        // 計算完成率
        const done = swCards.filter(c => c.isDone).length;
        const total = swCards.length;
        focusHtml += `<div class="focus-row" onclick="toggleFocusRow(this)"><strong>泳道：${{swim}}</strong> (${{total}} 項) [完成率：${{done}}/${{total}}]</div>`;
        focusHtml += `<div class="focus-children">`;
        swCards.forEach(c => {{
            const statusBadge = c.isDone ? '<span class="badge badge-done">DONE</span>' :
                               c.isDoing ? '<span class="badge badge-doing">Doing</span>' :
                               c.isWaiting ? '<span class="badge" style="background:#fff3e0;color:#e65100">Waiting</span>' :
                               c.isReview ? '<span class="badge" style="background:#f3e5f5;color:#6a1b9a">Review</span>' : '';
            focusHtml += `<div class="focus-child-row"><strong>${{cardLink(c.id, c.title)}}</strong> | ${{c.list}} | 停${{c.staleDays || '0'}}天 ${{statusBadge}}</div>`;
        }});
        focusHtml += `</div>`;
    }});

    document.getElementById('t2-focus-section').style.display = 'block';
    document.getElementById('t2-focus-placeholder').style.display = 'none';
    document.querySelector('.focus-title').textContent = `👤 個人泳道專注分析 — ${{memberName}}（本期有異動卡片）`;
    document.getElementById('t2-focus-content').innerHTML = focusHtml;
}}

function toggleFocusRow(el) {{
    const children = el.nextElementSibling;
    if (children && children.classList.contains('focus-children')) {{
        children.classList.toggle('open');
        el.classList.toggle('expanded');
    }}
}}

// ==================== Table 2 (Personal) ====================

// ==================== 改動 2: updateTables2 拆解函式 ====================

function renderNewDone2(cards, startDt, endDt) {{
    // 需求 #5: 本週新增／完成：左右並排扁平，按專案排序
    const newCards = sortBySwim(cards.filter(c => {{
        const ct = new Date(c.createdAt);
        return ct >= startDt && ct <= endDt;
    }}));
    let newHtml = '';
    newCards.forEach(c => {{
        newHtml += `<tr>
            <td>${{c.swimlane}}</td>
            <td>${{cardLink(c.id, c.title)}}</td>
            <td><span class="badge">${{c.list}}</span></td>
            <td>${{c.members.join(', ') || '無'}}</td>
            <td>${{c.createdAt.split('T')[0]}}</td>
        </tr>`;
    }});
    document.getElementById('t2-newdone-new-table').querySelector('tbody').innerHTML = newHtml;

    const doneCards = sortBySwim(cards.filter(c => {{
        const et = c.endAt ? new Date(c.endAt) : null;
        return c.isDone && et && et >= startDt && et <= endDt;
    }}));
    let doneHtml = '';
    doneCards.forEach(c => {{
        const et = new Date(c.endAt);
        doneHtml += `<tr>
            <td>${{c.swimlane}}</td>
            <td>${{cardLink(c.id, c.title)}}</td>
            <td>${{c.members.join(', ') || '無'}}</td>
            <td>${{et.toISOString().split('T')[0]}}</td>
        </tr>`;
    }});
    document.getElementById('t2-newdone-done-table').querySelector('tbody').innerHTML = doneHtml;

    // 本週有異動：dateLastActivity 落在本週區間，排除本週新增／完成 及 done + closed + backlog + info，依最後活動日由新到舊
    const ACT_EXCLUDE2 = {ACT_EXCLUDE_JSON};
    const actCards = cards.filter(c => {{
        const at = c.dateLastActivity ? new Date(c.dateLastActivity) : null;
        if (!at || at < startDt || at > endDt) return false;
        if (ACT_EXCLUDE2.includes(c.list)) return false;
        const ct = new Date(c.createdAt);
        const isNew = ct >= startDt && ct <= endDt;
        const et = c.endAt ? new Date(c.endAt) : null;
        const isDoneThisWeek = c.isDone && et && et >= startDt && et <= endDt;
        return !isNew && !isDoneThisWeek;
    }}).sort((a, b) => new Date(b.dateLastActivity) - new Date(a.dateLastActivity));
    let actHtml = '';
    actCards.forEach(c => {{
        actHtml += `<tr>
            <td>${{c.swimlane}}</td>
            <td>${{cardLink(c.id, c.title)}}</td>
            <td><span class="badge">${{c.list}}</span></td>
            <td>${{c.members.join(', ') || '無'}}</td>
            <td>${{c.dateLastActivity.split('T')[0]}}</td>
        </tr>`;
    }});
    document.getElementById('t2-newdone-activity-table').querySelector('tbody').innerHTML = actHtml;
}}

function renderAll2(cards) {{
    // 改動 3: 分頁邏輯
    const total = cards.length;
    const totalPages = Math.ceil(total / PAGE_SIZE) || 1;
    if (t2AllPage > totalPages) t2AllPage = totalPages;
    const pageCards = cards.slice((t2AllPage - 1) * PAGE_SIZE, t2AllPage * PAGE_SIZE);

    const sortedAll = sortBySwim(pageCards);
    let allHtml = '';
    sortedAll.forEach(c => {{
        const staleBadge = c.isStale ? `<span class="badge badge-stale">停滯${{c.staleDays}}天</span>` :
                          '<span class="badge" style="background:#e8f5e9;color:#2e7d32;">活躍</span>';
        const clProgress = c.hasChecklist ? `${{c.clDone}}/${{c.clTotal}} (${{c.clPct}}%)` : '-';
        const labelsStr = c.labels.length > 0 ? c.labels.join(', ') : '-';
        allHtml += `<tr>
            <td>${{c.swimlane}}</td>
            <td>${{cardLink(c.id, c.title)}}</td>
            <td>${{c.members.join(', ') || '無'}}</td>
            <td>${{c.createdAt.split('T')[0]}}</td>
            <td>${{c.dateLastActivity.split('T')[0] || '-'}}</td>
            <td>${{staleBadge}}</td>
            <td>${{clProgress}}</td>
            <td>${{labelsStr}}</td>
        </tr>`;
    }});

    const pageHtml = `<div style="display:flex;align-items:center;gap:12px;padding:8px 0;font-size:13px;">
        <button onclick="t2AllPage=Math.max(1,t2AllPage-1);renderAll2(filteredCards2)" ${{t2AllPage<=1?'disabled':''}}>‹ 上一頁</button>
        <span>第 ${{t2AllPage}} / ${{totalPages}} 頁（共 ${{total}} 筆）</span>
        <button onclick="t2AllPage=Math.min(${{totalPages}},t2AllPage+1);renderAll2(filteredCards2)" ${{t2AllPage>=totalPages?'disabled':''}}>下一頁 ›</button>
    </div>`;

    document.getElementById('t2-all-table').querySelector('tbody').innerHTML = allHtml;
    const pagerEl = document.getElementById('t2-all-pager');
    if (pagerEl) pagerEl.innerHTML = pageHtml;
}}

function updateTables2(cards, startDt, endDt) {{
    // 舊邏輯已移至各函式，此函式已不被調用（由 renderT2Panel 替代）
}}

function updateT2ParentTable(cards, swimFilter) {{
    renderParentGroups('t2', cards);
}}

// ==================== 需求 #7: 篩選狀態提示列 ====================

function renderFilterChips1(startDt, endDt, lists, swims, labels, statuses) {{
    // 只顯示灰色計數文字，不顯示 Chip 標籤列
    const parts = [];
    if (startDt && endDt) {{
        parts.push(`${{startDt.toISOString().split('T')[0]}} ~ ${{endDt.toISOString().split('T')[0]}}`);
    }}
    const listNames = lists.map(lid => RAW.listsMap[lid] || lid);
    const swimNames = swims.map(sid => RAW.swimlanesMap[sid] || sid);
    if (listNames.length) parts.push(`欄位：${{listNames.join('、')}}`);
    if (swimNames.length) parts.push(`主題：${{swimNames.join('、')}}`);
    const label = document.getElementById('t1-card-count-label');
    if (label) {{
        label.textContent = parts.length
            ? `顯示 ${{filteredCards1.length}} 張卡片（${{parts.join('｜')}}）`
            : `顯示全部 ${{filteredCards1.length}} 張卡片`;
    }}
}}

function renderFilterChips2(startDt, endDt, swims, labels, members, statuses) {{
    // 只顯示灰色計數文字，不顯示 Chip 標籤列
    const parts = [];
    if (startDt && endDt) {{
        parts.push(`${{startDt.toISOString().split('T')[0]}} ~ ${{endDt.toISOString().split('T')[0]}}`);
    }}
    const swimNames = swims.map(sid => RAW.swimlanesMap[sid] || sid);
    const memberNames = members.map(mid => RAW.users[mid] || mid);
    if (swimNames.length) parts.push(`主題：${{swimNames.join('、')}}`);
    if (memberNames.length) parts.push(`成員：${{memberNames.join('、')}}`);
    const label = document.getElementById('t2-card-count-label');
    if (label) {{
        label.textContent = parts.length
            ? `顯示 ${{filteredCards2.length}} 張卡片（${{parts.join('｜')}}）`
            : `顯示全部 ${{filteredCards2.length}} 張卡片`;
    }}
}}

function clearChip1(type) {{
    // 實作邏輯：根據 type 清除對應篩選條件
    // 簡化版：直接清除所有篩選並重新套用
    applyFilters1();
}}

function clearChip2(type) {{
    applyFilters2();
}}

function clearAllChips1() {{
    document.querySelectorAll('#t1-list-picker-items input').forEach(cb => cb.checked = false);
    document.querySelectorAll('#t1-swim-picker-items input').forEach(cb => cb.checked = false);
    document.querySelectorAll('#t1-label-picker-items input').forEach(cb => cb.checked = false);
    document.querySelectorAll('#t1-status-picker-items input').forEach(cb => cb.checked = false);
    applyFilters1();
}}

function clearAllChips2() {{
    document.querySelectorAll('#t2-swim-picker-items input').forEach(cb => cb.checked = false);
    document.querySelectorAll('#t2-label-picker-items input').forEach(cb => cb.checked = false);
    document.querySelectorAll('#t2-member-picker-items input').forEach(cb => cb.checked = false);
    document.querySelectorAll('#t2-status-picker-items input').forEach(cb => cb.checked = false);
    applyFilters2();
}}

// ==================== Initialization ====================

document.addEventListener('DOMContentLoaded', () => {{
    initFilters();
}});
</script>

</body>
</html>
"""

with open(OUT_FILE, "w", encoding="utf-8") as f:
    f.write(html)
print(f"🎉 儀表板已產生：{os.path.basename(OUT_FILE)}")
print(f"   路徑：{OUT_FILE}")
