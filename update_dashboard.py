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

# ── 讀取 AI 分析設定（ai_analysis_config.yaml） ──────────
_ai_cfg_path = os.path.join(BASE_DIR, "ai_analysis_config.yaml")
AI_SAVE_FOLDER   = "AI分析結果"
AI_FILENAME_PREFIX = "AI分析"
if os.path.exists(_ai_cfg_path):
    try:
        import yaml
        with open(_ai_cfg_path, "r", encoding="utf-8") as _f:
            _cfg = yaml.safe_load(_f) or {}
        AI_SAVE_FOLDER     = _cfg.get("save_folder", AI_SAVE_FOLDER)
        AI_FILENAME_PREFIX = _cfg.get("filename_prefix", AI_FILENAME_PREFIX)
    except Exception as _e:
        print(f"⚠️  ai_analysis_config.yaml 讀取失敗，使用預設值：{_e}")

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
    milestone_label_cfg  = _board.get("milestone_label", "里程碑")
else:
    _board = {}
    milestone_label_cfg = "里程碑"

# ── Wekan 卡片連結設定（從 team_config.json 的 board.wekan_card_url_base 讀取）─
# 格式：https://your-wekan/b/{boardId}/{slug}
# 空字串 = 不顯示卡片連結
WEKAN_CARD_URL_BASE = _board.get("wekan_card_url_base", "")

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
_risk_exclude  = _roles["done"]    + _roles["closed"] + _roles["info"] + _roles["backlog"]
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
READY_NAMES_JSON      = json.dumps(_roles["ready"],          ensure_ascii=False)

# 本週有異動分群順序：review → doing → 未分類欄位（如「準備中」）→ waiting → ready
_known_role_lists = set(
    _roles["done"] + _roles["closed"] + _roles["doing"] + _roles["waiting"] +
    _roles["review"] + _roles["backlog"] + _roles["ready"] + _roles["info"]
)
_lists_in_order   = _cfg.get("board", {}).get("lists_order", [])
_unclassified     = [l for l in _lists_in_order if l not in _known_role_lists]
_act_group_order  = _roles["review"] + _roles["doing"] + _unclassified + _roles["waiting"] + _roles["ready"]
ACT_GROUP_ORDER_JSON = json.dumps(_act_group_order, ensure_ascii=False)

# ── 卡片描述段落擷取（AI 用）────────────────────────────
def extract_desc_sections(desc):
    """從 Wekan 卡片描述的 Markdown 中擷取「現況描述」與「交付物」段落"""
    if not desc:
        return ""
    target = {"現況描述", "交付物"}
    result = []
    current_sec = None
    current_lines = []
    for line in desc.splitlines():
        stripped = line.strip()
        if stripped.startswith("## "):
            # flush previous section
            if current_sec and current_lines:
                joined = " ".join(l.strip() for l in current_lines if l.strip())
                if joined:
                    result.append(f"[{current_sec}] {joined}")
            current_sec = None
            current_lines = []
            sec_name = stripped[3:].strip()
            if sec_name in target:
                current_sec = sec_name
        elif current_sec:
            current_lines.append(line)
    # flush last section
    if current_sec and current_lines:
        joined = " ".join(l.strip() for l in current_lines if l.strip())
        if joined:
            result.append(f"[{current_sec}] {joined}")
    return " | ".join(result) if result else ""

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
    # 本週新出現的風險：本週才逾期 OR 本週才停滯（staleDays 14~20）OR 即將到期
    is_new_risk = bool(
        (is_overdue and due_dt and (NOW - due_dt).days <= 7) or
        (is_stale and stale_days is not None and STALE_DAYS < stale_days <= STALE_DAYS + 7) or
        is_due_soon
    ) and not is_done

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
        "isNewRisk":        is_new_risk,
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
        "description_summary": extract_desc_sections(c.get("description", "")),
    })

# ── AI 分析 Tab 資料（本週新增 / 完成 / 風險 / Doing）────
_risk_exclude_set = set(_risk_exclude)

_ai_new = [
    {"swimlane": r["swimlane"], "title": r["title"],
     "members": r["members"], "list": r["list"],
     "desc": r["description_summary"]}
    for r in card_records
    if r["createdAt"] and parse_dt(r["createdAt"]) and parse_dt(r["createdAt"]) >= WEEK_START
    and not r["archived"]
]
_ai_done = [
    {"swimlane": r["swimlane"], "title": r["title"],
     "members": r["members"],
     "desc": r["description_summary"]}
    for r in card_records
    if r["isDone"] and r["endAt"] and parse_dt(r["endAt"]) and parse_dt(r["endAt"]) >= WEEK_START
]
_ai_risk = [
    {"swimlane": r["swimlane"], "title": r["title"],
     "isStale": r["isStale"], "staleDays": r["staleDays"] or 0,
     "isOverdue": r["isOverdue"], "isDueSoon": r["isDueSoon"],
     "dueAtDisplay": r["dueAtDisplay"],
     "desc": r["description_summary"]}
    for r in card_records
    if r["list"] not in _risk_exclude_set
    and not r["archived"]
    and (r["isStale"] or r["isOverdue"] or r["isDueSoon"])
]
_ai_doing = [
    {"swimlane": r["swimlane"], "title": r["title"],
     "members": r["members"], "isStale": r["isStale"], "staleDays": r["staleDays"] or 0,
     "desc": r["description_summary"]}
    for r in card_records
    if r["isDoing"] and not r["archived"]
]
AI_NEW_JSON   = json.dumps(_ai_new,   ensure_ascii=False)
AI_DONE_JSON  = json.dumps(_ai_done,  ensure_ascii=False)
AI_RISK_JSON  = json.dumps(_ai_risk,  ensure_ascii=False)
AI_DOING_JSON = json.dumps(_ai_doing, ensure_ascii=False)

# ── 成果亮點 Tab 資料（里程碑卡片）───────────────────────
MILESTONE_LABEL     = milestone_label_cfg
MILESTONE_LABEL_IDS = {
    l["_id"] for l in data.get("labels", [])
    if l.get("name") == MILESTONE_LABEL
}
# cardId → [labelId, ...] 快查表
_card_label_ids = {
    c["_id"]: (c.get("labelIds") or [])
    for c in data.get("cards", [])
}

def _fmt_end_display(end_at):
    dt = parse_dt(end_at)
    if not dt:
        return "—"
    return f"{dt.year}/{dt.month:02d}/{dt.day:02d}"

_ai_milestones = [
    {
        "id":              r["id"],
        "title":           r["title"],
        "swimlane":        r["swimlane"],
        "members":         r["members"],
        "labels":          r["labels"],
        "list":            r["list"],
        "isDone":          r["isDone"],
        "isStale":         r["isStale"],
        "staleDays":       r["staleDays"] or 0,
        "endAt":           r["endAt"],
        "endAtDisplay":    _fmt_end_display(r["endAt"]),
        "lastActivity":    r["dateLastActivity"],
        "lastActDisplay":  _fmt_end_display(r["dateLastActivity"]),
        "dueAt":           r["dueAt"],
        "dueAtDisplay":    r["dueAtDisplay"],
        "desc":            r["description_summary"],
    }
    for r in card_records
    if not r["archived"]
    and any(lid in MILESTONE_LABEL_IDS
            for lid in _card_label_ids.get(r["id"], []))
]
# 排序：進行中（非 DONE）優先（依 lastActivity 降冪），DONE 在後（依 endAt 降冪）
_in_progress = sorted(
    [x for x in _ai_milestones if not x["isDone"]],
    key=lambda x: x["lastActivity"] or "", reverse=True
)
_done_ms = sorted(
    [x for x in _ai_milestones if x["isDone"]],
    key=lambda x: x["endAt"] or "", reverse=True
)
_ai_milestones = _in_progress + _done_ms
MILESTONES_JSON = json.dumps(_ai_milestones, ensure_ascii=False)
MILESTONE_LABEL_JSON = json.dumps(MILESTONE_LABEL, ensure_ascii=False)

# ── 里程碑補充資料（milestone_notes.json）────────────────
MILESTONE_NOTES_PATH = os.path.join(BASE_DIR, "milestone_notes.json")
_milestone_notes = {}
if os.path.exists(MILESTONE_NOTES_PATH):
    try:
        with open(MILESTONE_NOTES_PATH, "r", encoding="utf-8") as _f:
            _milestone_notes = json.load(_f)
    except Exception:
        _milestone_notes = {}
MILESTONE_NOTES_JSON     = json.dumps(_milestone_notes, ensure_ascii=False)
MILESTONE_NOTES_DIR_JSON = json.dumps(os.path.basename(BASE_DIR), ensure_ascii=False)

# ── 每週完成趨勢（近 12 週）────────────────────────────
weekly_trend = []
for w in range(11, -1, -1):  # 從 11 週前到本週
    w_end   = NOW - timedelta(days=w * 7)
    w_start = w_end - timedelta(days=7)
    label   = f"{w_start.month}/{w_start.day}~{w_end.month}/{w_end.day}"
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

        .kpi-card.kpi-clickable {{ cursor: pointer; transition: box-shadow 0.15s, transform 0.1s; }}
        .kpi-card.kpi-clickable:hover {{ box-shadow: 0 4px 12px rgba(0,0,0,0.13); transform: translateY(-2px); }}

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
        .child-list-group-header td {{
            background:#f5f5f5; color:#555; font-size:0.8em; font-weight:600;
            border-top:1px solid #e0e0e0; border-bottom:1px solid #e8e8e8;
            padding:4px 8px; letter-spacing:0.03em;
        }}
        .child-depth-marker {{ color:#bbb; margin-right:2px; font-size:0.85em; }}
        /* 父任務狀態 Tab（Feature C-3）*/
        .parent-status-panel {{ display:none; }}
        .parent-status-panel.active {{ display:block; }}
        .sub-tab-btn.pst-done {{ color:#aaa; }}
        .sub-tab-btn.pst-done.active {{ color:#888; border-bottom-color:#888; }}
        .sub-tab-btn.pst-zero {{ color:#ccc; cursor:default; pointer-events:none; }}

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

        /* 主題交替底色（方案 A：依 SWIM_ORDER 奇偶） */
        .row-alt-bg {{ background-color: #e8f4fd !important; }}

        /* 📊 主題對照 逐列式（同主題同高 + 拖曳排序） */
        .nd-cmp-table {{ border:1px solid #d0e4f5; border-radius:6px; overflow:hidden; }}
        .nd-cmp-hdr-row {{ display:flex; background:#f0f6fc; border-bottom:2px solid #c2d8ef; }}
        .nd-cmp-hdr-drag {{ width:28px; flex-shrink:0; }}
        .nd-cmp-hdr-cell {{ flex:1; padding:8px 14px; font-weight:700; font-size:0.88em; color:#fff; text-align:center; }}
        .nd-cmp-hdr-cell.new-hdr  {{ background:#1a73b5; }}
        .nd-cmp-hdr-cell.done-hdr {{ background:#2e7d32; }}
        .nd-cmp-row {{ border-bottom:1px solid #e4eff9; transition:background 0.12s; }}
        .nd-cmp-row:last-child {{ border-bottom:none; }}
        .nd-cmp-row.drag-over {{ background:#ddeeff; outline:2px dashed #1a73b5; outline-offset:-2px; }}
        .nd-cmp-row-head {{
            display:flex; align-items:center; gap:6px;
            background:#eaf3fb; padding:5px 10px;
            cursor:pointer; user-select:none;
        }}
        .nd-cmp-drag-handle {{ color:#bbb; font-size:1em; flex-shrink:0; cursor:grab; }}
        .nd-cmp-drag-handle:active {{ cursor:grabbing; }}
        .nd-cmp-swim-name {{ font-size:0.82em; font-weight:700; color:#1a4f7a; }}
        .nd-cmp-pipe-badges {{ display:flex; gap:4px; align-items:center; flex-shrink:0; }}
        .nd-cmp-pipe-badge {{ font-size:0.73em; padding:1px 7px; border-radius:10px; font-weight:600; white-space:nowrap; border:1px solid transparent; }}
        .nd-cmp-pipe-badge.doing   {{ background:#e3f2fd; color:#1565c0; border-color:#90caf9; }}
        .nd-cmp-pipe-badge.waiting {{ background:#fff3e0; color:#e65100; border-color:#ffcc80; }}
        .nd-cmp-pipe-badge.review  {{ background:#f3e5f5; color:#6a1b9a; border-color:#ce93d8; }}
        .nd-cmp-pipe-badge.zero    {{ opacity:0.28; }}
        .nd-cmp-expand-arrow {{ margin-left:auto; color:#888; font-size:0.78em; flex-shrink:0; transition:transform 0.15s; }}
        /* Pipeline 展開區 */
        .nd-cmp-pipeline {{ background:#f6faff; border-top:1px solid #d8eaf8; border-bottom:1px solid #d8eaf8; }}
        .nd-cmp-pipe-cols {{ display:flex; }}
        .nd-cmp-pipe-col {{ flex:1; min-width:0; padding:6px 10px; border-right:1px solid #e4eff9; }}
        .nd-cmp-pipe-col:last-child {{ border-right:none; }}
        .nd-cmp-pipe-col-hdr {{ font-size:0.78em; font-weight:700; padding:3px 0 5px; margin-bottom:4px; border-bottom:1px solid #e4eff9; }}
        .nd-cmp-pipe-col-hdr.doing-hdr   {{ color:#1565c0; }}
        .nd-cmp-pipe-col-hdr.waiting-hdr {{ color:#e65100; }}
        .nd-cmp-pipe-col-hdr.review-hdr  {{ color:#6a1b9a; }}
        /* 完成/新增區 */
        .nd-cmp-row-body {{ display:flex; }}
        .nd-cmp-cell {{ flex:1; min-width:0; padding:6px 8px; border-right:1px solid #e4eff9; }}
        .nd-cmp-cell:last-child {{ border-right:none; }}
        .nd-cmp-card {{ font-size:0.84em; padding:3px 4px; color:#333; border-bottom:1px solid #f0f5fa; }}
        .nd-cmp-card:last-child {{ border-bottom:none; }}
        .nd-cmp-card-member {{ color:#888; font-size:0.9em; }}
        .nd-cmp-empty {{ font-size:0.82em; color:#ccc; font-style:italic; padding:4px 4px; }}

        /* 本週有異動 欄位分群（可折疊卡片） */
        .act-group-card {{ border: 1px solid #cce0f5; border-radius: 6px; margin-bottom: 8px; overflow: hidden; }}
        .act-group-hdr {{
            background: #ddeaf6; color: #1a4f7a; font-weight: 600;
            padding: 8px 14px; cursor: pointer; display: flex; align-items: center; gap: 8px;
            font-size: 0.87em; letter-spacing: 0.03em; user-select: none;
        }}
        .act-group-hdr:hover {{ background: #c8d8ec; }}
        .act-group-arrow {{ display:inline-block; transition: transform 0.2s; font-size: 0.8em; }}
        .act-group-card.collapsed .act-group-arrow {{ transform: rotate(-90deg); }}
        .act-group-body {{ overflow-x: auto; }}
        .act-group-card.collapsed .act-group-body {{ display: none; }}
        .act-group-table {{ width: 100%; border-collapse: collapse; }}
        .act-group-table th {{ background: #f5f8fc; color: #555; font-size: 0.84em; padding: 6px 10px; border-bottom: 1px solid #dde6f0; text-align:left; }}
        .act-group-table td {{ padding: 6px 10px; border-bottom: 1px solid #edf1f5; }}

        /* AI 分析 Tab 左右佈局 */
        .ai-layout {{ display:flex; gap:18px; align-items:flex-start; }}
        .ai-left {{ flex:0 0 52%; min-width:0; display:flex; flex-direction:column; }}
        .ai-right {{ flex:1; min-width:0; display:flex; flex-direction:column; }}
        /* 面板 header：左標題 + 右按鈕區，永遠固定顯示 */
        .ai-panel-header {{
            font-weight:700; font-size:0.9em; color:#1a4f7a;
            background:#e8f2fc; border:1px solid #b8d4ef;
            border-radius:6px 6px 0 0; padding:7px 12px;
            display:flex; align-items:center; justify-content:space-between; gap:8px;
            flex-shrink:0;
        }}
        .ai-panel-header-title {{ display:flex; align-items:center; gap:6px; }}
        .ai-panel-header-actions {{ display:flex; align-items:center; gap:6px; flex-shrink:0; }}
        .ai-panel-body {{
            border:1px solid #b8d4ef; border-top:none;
            border-radius:0 0 6px 6px; padding:12px 14px;
            background:#fff;
        }}
        /* 複製按鈕（在 header 右側） */
        #ai-copy-btn {{
            background:var(--primary); color:white; border:none;
            padding:5px 14px; border-radius:5px; font-size:0.82em;
            cursor:pointer; letter-spacing:0.03em; white-space:nowrap;
        }}
        #ai-copy-btn:hover {{ background:#1565c0; }}
        /* 模式切換按鈕（檢視 / 編輯） */
        .ai-mode-btn {{
            background:#fff; color:#1a4f7a; border:1px solid #b8d4ef;
            padding:4px 11px; border-radius:5px; font-size:0.8em;
            cursor:pointer; white-space:nowrap;
        }}
        .ai-mode-btn.active {{
            background:#1a4f7a; color:#fff; border-color:#1a4f7a;
        }}
        .ai-preview-scroll {{ max-height:520px; overflow-y:auto; }}
        .ai-section {{ background:#f8fbff; border:1px solid #ddeeff; border-radius:5px; padding:11px 13px; margin-bottom:10px; }}
        .ai-section-title {{ font-weight:600; font-size:0.88em; color:#1a4f7a; margin-bottom:7px; }}
        .ai-swim-group {{ margin-bottom:5px; }}
        .ai-swim-name {{ font-size:0.8em; color:#555; font-weight:600; }}
        .ai-card-row {{ font-size:0.84em; padding:2px 0 2px 10px; color:#333; }}
        .ai-card-meta {{ color:#888; font-size:0.9em; }}
        .ai-card-desc {{ font-size:0.80em; color:#5a7fa8; padding:1px 0 3px 20px; line-height:1.4; }}
        .ai-empty {{ font-size:0.82em; color:#aaa; padding:3px 0; }}
        /* 右側編輯框 */
        #ai-notes {{
            width:100%; min-height:520px;
            padding:12px; border:1px solid #b8d4ef;
            border-radius:0 0 6px 6px; border-top:none;
            font-size:0.88em; line-height:1.65; resize:vertical;
            font-family:inherit; box-sizing:border-box;
            display:block;
        }}
        /* 右側檢視框（Markdown 渲染） */
        #ai-notes-view {{
            width:100%; min-height:520px;
            padding:14px 16px; border:1px solid #b8d4ef;
            border-radius:0 0 6px 6px; border-top:none;
            font-size:0.88em; line-height:1.75;
            box-sizing:border-box; overflow-y:auto;
            background:#fafcff; display:none;
            color:#222;
        }}
        #ai-notes-view h1,#ai-notes-view h2,#ai-notes-view h3 {{
            color:#1a4f7a; margin:10px 0 4px; font-size:1em;
        }}
        #ai-notes-view p {{ margin:4px 0 8px; }}
        #ai-notes-view ul {{ margin:4px 0 8px; padding-left:20px; }}
        #ai-notes-view strong {{ color:#1a4f7a; }}
        #ai-notes-view hr {{ border:none; border-top:1px solid #d0e4f7; margin:10px 0; }}
        #ai-notes-placeholder {{
            color:#bbb; font-size:0.88em; padding:12px 16px;
            border:1px solid #b8d4ef; border-radius:0 0 6px 6px;
            border-top:none; min-height:520px; box-sizing:border-box;
            background:#fafcff; display:none;
        }}
        @media (max-width:900px) {{
            .ai-layout {{ flex-direction:column; }}
            .ai-left, .ai-right {{ flex:unset; width:100%; }}
        }}

        /* ── 🏆 成果亮點 Tab ── */
        .ms-filter-bar {{
            display:flex; align-items:center; gap:10px; flex-wrap:wrap;
            background:#f5fbf5; border:1px solid #c3dfc3; border-radius:6px;
            padding:9px 14px; margin-bottom:16px;
        }}
        .ms-filter-bar label {{ font-size:0.82em; color:#2e7d32; font-weight:600; white-space:nowrap; }}
        .ms-filter-bar input[type=date] {{
            font-size:0.82em; padding:3px 7px; border:1px solid #c3dfc3;
            border-radius:4px; color:#333;
        }}
        .ms-filter-swim {{
            font-size:0.82em; padding:3px 8px; border:1px solid #c3dfc3;
            border-radius:4px; min-width:140px;
        }}
        .ms-count {{
            font-size:0.82em; color:#555; margin-left:auto; white-space:nowrap;
        }}
        .ms-swim-header {{
            font-size:0.9em; font-weight:700; color:#1a4f7a;
            border-bottom:2px solid #c8dff0; margin:18px 0 8px;
            padding-bottom:4px;
        }}
        .ms-empty {{
            color:#aaa; font-size:0.88em; padding:30px 0; text-align:center;
        }}
        .ms-card {{
            background:#fff; border:1px solid #ddeeff; border-radius:7px;
            padding:12px 14px; margin-bottom:10px;
            box-shadow:0 1px 3px rgba(0,0,0,0.05);
            transition:box-shadow 0.15s;
        }}
        .ms-card:hover {{ box-shadow:0 2px 8px rgba(26,79,122,0.10); }}
        .ms-card-done {{ border-left:4px solid #43a047; background:#fafffe; }}
        .ms-card-meta-row {{
            display:flex; align-items:center; justify-content:space-between;
            gap:8px; margin-bottom:6px; flex-wrap:wrap;
        }}
        .ms-status-badge {{
            font-size:0.75em; padding:2px 9px; border-radius:10px;
            font-weight:600; white-space:nowrap; flex-shrink:0;
        }}
        .ms-status-badge.ms-done    {{ background:#e8f5e9; color:#2e7d32; border:1px solid #a5d6a7; }}
        .ms-status-badge.ms-doing   {{ background:#e3f2fd; color:#1565c0; border:1px solid #90caf9; }}
        .ms-status-badge.ms-waiting {{ background:#fff3e0; color:#e65100; border:1px solid #ffcc80; }}
        .ms-status-badge.ms-review  {{ background:#f3e5f5; color:#6a1b9a; border:1px solid #ce93d8; }}
        .ms-status-badge.ms-other   {{ background:#f5f5f5; color:#555;    border:1px solid #ddd; }}
        .ms-card-title {{
            display:flex; align-items:flex-start; justify-content:space-between;
            gap:8px; margin-bottom:5px;
        }}
        .ms-card-title-left {{
            font-size:0.92em; font-weight:600; color:#1a4f7a; flex:1; min-width:0;
        }}
        .ms-card-date {{
            font-size:0.82em; color:#888; white-space:nowrap; flex-shrink:0;
        }}
        .ms-card-members {{
            font-size:0.82em; color:#666; margin-bottom:7px;
        }}
        .ms-card-desc {{
            font-size:0.80em; color:#5a7fa8; margin-bottom:6px;
            padding:4px 8px; background:#f4f9ff; border-radius:4px;
            border-left:3px solid #90c0e8; line-height:1.45;
        }}
        /* 補充說明 */
        .ms-note-area {{ margin-top:6px; }}
        .ms-note-placeholder {{
            font-size:0.82em; color:#bbb; cursor:pointer; padding:3px 0;
            display:flex; align-items:center; gap:4px;
        }}
        .ms-note-placeholder:hover {{ color:#1a73b5; }}
        .ms-note-text {{
            font-size:0.84em; color:#444; cursor:pointer; padding:4px 8px;
            background:#fafcff; border-radius:4px; border:1px solid #e4eff9;
            line-height:1.5;
        }}
        .ms-note-text:hover {{ border-color:#90c0e8; background:#f0f7ff; }}
        .ms-note-input {{
            width:100%; font-size:0.84em; padding:5px 8px;
            border:1px solid #90c0e8; border-radius:4px;
            font-family:inherit; resize:vertical; min-height:52px;
            box-sizing:border-box; color:#333; line-height:1.5;
        }}
        /* 簡報連結 */
        .ms-link-area {{ margin-top:6px; display:flex; align-items:center; gap:6px; }}
        .ms-link-input {{
            font-size:0.82em; padding:4px 8px; border:1px solid #ddd;
            border-radius:4px; flex:1; color:#555; min-width:0;
        }}
        .ms-link-input:focus {{ border-color:#90c0e8; outline:none; }}
        .ms-link-btn {{
            font-size:0.82em; color:#1a73b5; text-decoration:none; white-space:nowrap;
            padding:3px 10px; border:1px solid #90c0e8; border-radius:4px;
            background:#f0f7ff; display:inline-flex; align-items:center; gap:4px;
        }}
        .ms-link-btn:hover {{ background:#ddeeff; text-decoration:underline; }}
        .ms-link-clear {{
            font-size:0.8em; color:#bbb; cursor:pointer; padding:2px 6px;
            border:1px solid #ddd; border-radius:3px; background:#fafafa;
            flex-shrink:0;
        }}
        .ms-link-clear:hover {{ color:#c00; border-color:#f99; }}

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

        .card-link {{
            font-weight: 500;
            color: inherit;
            text-decoration: none;
        }}
        .card-link:hover {{
            color: #1a4f7a;
            text-decoration: underline;
            text-underline-offset: 2px;
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
    <button class="main-tab-btn" onclick="switchMainTab('ai')">🤖 AI 分析</button>
    <button class="main-tab-btn" onclick="switchMainTab('milestones')">🏆 成果亮點</button>
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
            <button class="sub-tab-btn" onclick="switchRiskSubTab('swim')">主題篩選</button>
            <button class="sub-tab-btn" id="risk-subtab-btn-newrisk" onclick="switchRiskSubTab('newrisk')">🆕 本週新風險</button>
            <button class="sub-tab-btn" onclick="switchRiskSubTab('duesoon')">⚡ 即將到期</button>
        </div>
        <div class="risk-scope-note">＊資料範圍：排除 DONE / Closed / 過往卡片 / 過往卡片待青 / Goal＆專案資訊 / 封存卡片</div>

        <div id="risk-subpanel-overview" class="sub-panel active">
            <div class="table-wrapper">
                <table id="t1-risk-overview-table">
                    <thead>
                        <tr>
                            <th>主題</th>
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
                <label>依主題篩選：</label>
                <select id="t1-risk-swim-filter" onchange="applyRiskSwimFilter()" style="padding:6px; border:1px solid var(--border); border-radius:4px;">
                    <option value="">全部主題</option>
                </select>
            </div>
            <div class="table-wrapper">
                <table id="t1-risk-swim-table">
                    <thead>
                        <tr>
                            <th>主題</th>
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

        <div id="risk-subpanel-newrisk" class="sub-panel">
            <div style="font-size:0.82em;color:#888;margin-bottom:10px;">🆕 本週新風險：本週才出現的風險卡（本週新逾期 ＋ 本週才停滯 ＋ 即將到期）｜受左側篩選器影響</div>
            <div class="table-wrapper">
                <table id="t1-risk-newrisk-table">
                    <thead><tr>
                        <th>主題</th><th>卡片名稱</th><th>預計完成日</th>
                        <th>所在欄位</th><th>負責人</th><th>最後活動日</th><th>風險標記</th>
                    </tr></thead>
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
                            <th>主題</th>
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
                        <th>主題</th>
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
            <button class="mini-tab-btn" id="t1-nd-btn-compare" onclick="switchNewDone('t1','compare')">
                📊 主題對照
            </button>
        </div>
        <div id="t1-nd-new">
            <div style="overflow-x:auto">
            <table id="t1-newdone-new-table" style="width:100%">
                <thead><tr>
                    <th>主題</th><th>卡片名稱</th><th>欄位</th><th>負責人</th><th>建立日</th>
                </tr></thead>
                <tbody></tbody>
            </table>
            </div>
        </div>
        <div id="t1-nd-done" style="display:none">
            <div style="overflow-x:auto">
            <table id="t1-newdone-done-table" style="width:100%">
                <thead><tr>
                    <th>主題</th><th>卡片名稱</th><th>負責人</th><th>完成日</th>
                </tr></thead>
                <tbody></tbody>
            </table>
            </div>
        </div>
        <div id="t1-nd-activity" style="display:none">
            <div id="t1-nd-act-wrap" style="padding:4px 0"></div>
        </div>
        <div id="t1-nd-compare" style="display:none">
            <div id="t1-nd-cmp-wrap"></div>
        </div>
    </div>

    <!-- 需求 #3: 全部明細扁平 -->
    <div id="t1-panel-all" class="sub-panel">
        <div style="font-size:0.78em; color:#888; margin-bottom:8px;">＊資料範圍：依左側篩選器條件顯示（日期、流程欄位、主題、標籤、狀態等）</div>
        <div class="table-wrapper" style="max-height:70vh;overflow-y:auto;border:1px solid #e0e0e0;border-radius:4px;">
            <table id="t1-all-table">
                <thead>
                    <tr>
                        <th>主題</th>
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
            <label>依主題篩選：</label>
            <select id="t1-parent-swim-filter" onchange="applyParentSwimFilter('t1')" style="padding:4px 8px;border-radius:4px;border:1px solid #ddd">
                <option value="">全部主題</option>
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
            <button class="mini-tab-btn" id="t2-nd-btn-compare" onclick="switchNewDone('t2','compare')">
                📊 主題對照
            </button>
        </div>
        <div id="t2-nd-new">
            <div style="overflow-x:auto">
            <table id="t2-newdone-new-table" style="width:100%">
                <thead><tr>
                    <th>主題</th><th>卡片名稱</th><th>欄位</th><th>負責人</th><th>建立日</th>
                </tr></thead>
                <tbody></tbody>
            </table>
            </div>
        </div>
        <div id="t2-nd-done" style="display:none">
            <div style="overflow-x:auto">
            <table id="t2-newdone-done-table" style="width:100%">
                <thead><tr>
                    <th>主題</th><th>卡片名稱</th><th>負責人</th><th>完成日</th>
                </tr></thead>
                <tbody></tbody>
            </table>
            </div>
        </div>
        <div id="t2-nd-activity" style="display:none">
            <div id="t2-nd-act-wrap" style="padding:4px 0"></div>
        </div>
        <div id="t2-nd-compare" style="display:none">
            <div id="t2-nd-cmp-wrap"></div>
        </div>
    </div>

    <div id="t2-panel-all" class="sub-panel">
        <div class="table-wrapper" style="max-height:70vh;overflow-y:auto;border:1px solid #e0e0e0;border-radius:4px;">
            <table id="t2-all-table">
                <thead>
                    <tr>
                        <th>主題</th>
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

<!-- ==================== TAB 4: 成果亮點 ==================== -->
<div id="main-panel-milestones" class="main-panel">
    <div style="max-width:1100px; margin:0 auto;">

        <!-- 篩選列 -->
        <div class="ms-filter-bar">
            <label>完成日期</label>
            <input type="date" id="ms-date-start" onchange="renderMilestones()">
            <span style="color:#888;font-size:0.82em;">～</span>
            <input type="date" id="ms-date-end" onchange="renderMilestones()">
            <label style="margin-left:10px;">主題</label>
            <select id="ms-swim-filter" class="ms-filter-swim" onchange="renderMilestones()">
                <option value="">全部主題</option>
            </select>
            <span class="ms-count" id="ms-count">共 0 個里程碑</span>
            <button id="ms-save-btn" onclick="saveMilestoneNotes()"
                style="margin-left:auto;background:#2e7d32;color:white;border:none;
                       padding:5px 14px;border-radius:5px;font-size:0.82em;
                       cursor:pointer;white-space:nowrap;flex-shrink:0;">
                💾 儲存補充資料
            </button>
        </div>
        <div style="font-size:0.75em;color:#666;margin:-10px 0 14px;padding:4px 6px;
                    background:#f9fff9;border:1px solid #d4edda;border-radius:4px;
                    display:flex;align-items:flex-start;gap:6px;flex-wrap:wrap;">
            <span>💡 儲存後請將檔案放到：</span>
            <code id="ms-path-hint" style="color:#1a4f7a;background:#e8f2fc;
                  padding:1px 7px;border-radius:3px;word-break:break-all;">
                與 update_dashboard.py 同一資料夾
            </code>
            <span style="color:#aaa;">→ 下次更新儀表板即永久保存</span>
        </div>

        <!-- 內容區 -->
        <div id="ms-content"></div>

    </div>
</div>

<!-- ==================== TAB 3: AI 分析 ==================== -->
<div id="main-panel-ai" class="main-panel">
    <div style="max-width:1200px; margin:0 auto;">

        <div class="ai-layout">

            <!-- 左側：資料預覽，複製按鈕固定在 header -->
            <div class="ai-left">
                <div class="ai-panel-header">
                    <span class="ai-panel-header-title">📋 本週看板資料摘要</span>
                    <div class="ai-panel-header-actions">
                        <span style="font-size:0.75em;color:#5a7fa8;font-weight:400;">複製後貼到 Claude 對話視窗</span>
                        <button id="ai-copy-btn" onclick="copyAIData()">📋 複製資料給 AI</button>
                    </div>
                </div>
                <div class="ai-panel-body" style="padding:10px 12px;">
                    <div id="ai-preview-box" class="ai-preview-scroll"></div>
                </div>
            </div>

            <!-- 右側：AI 分析結果，支援檢視 / 編輯切換 -->
            <div class="ai-right">
                <div class="ai-panel-header">
                    <span class="ai-panel-header-title">🤖 AI 分析結果</span>
                    <div class="ai-panel-header-actions">
                        <button class="ai-mode-btn active" id="ai-mode-view" onclick="setAIMode('view')">👁 檢視</button>
                        <button class="ai-mode-btn" id="ai-mode-edit" onclick="setAIMode('edit')">✏️ 編輯</button>
                        <button id="ai-save-btn" onclick="saveAIToFile()"
                            style="background:#2e7d32;color:white;border:none;padding:4px 12px;
                                   border-radius:5px;font-size:0.8em;cursor:pointer;white-space:nowrap;">
                            💾 儲存本週分析
                        </button>
                    </div>
                </div>
                <div id="ai-save-hint"
                    style="font-size:0.75em;color:#888;padding:5px 14px 3px;
                           border:1px solid #b8d4ef;border-top:none;background:#f9fcff;
                           display:flex;align-items:center;gap:6px;flex-wrap:wrap;">
                    <span>📁 儲存位置：</span>
                    <code style="font-size:0.95em;color:#1a4f7a;background:#e8f2fc;
                                 padding:1px 6px;border-radius:3px;">{AI_SAVE_FOLDER}</code>
                    <span style="color:#bbb;">｜檔名範例：</span>
                    <code style="font-size:0.95em;color:#5a7fa8;background:#f0f6ff;
                                 padding:1px 6px;border-radius:3px;">{AI_FILENAME_PREFIX}_{TODAY_STR}_HHMM.md</code>
                    <span id="ai-save-cfg-note" style="color:#c0a000;display:none;">
                        ⚙️ 可修改 ai_analysis_config.yaml 調整路徑與前綴
                    </span>
                </div>
                <!-- 檢視模式：渲染 Markdown -->
                <div id="ai-notes-view"></div>
                <!-- 佔位（無內容時） -->
                <div id="ai-notes-placeholder">將 Claude 的分析回覆貼在右側「編輯」模式中…<br><br>（內容會自動儲存在瀏覽器，下次開啟仍會保留）</div>
                <!-- 編輯模式 -->
                <textarea id="ai-notes" oninput="saveAINotes()"
                    placeholder="將 Claude 的分析回覆貼在這裡…&#10;&#10;（內容會自動儲存在瀏覽器，下次開啟仍會保留）"
                    style="display:none;"></textarea>
            </div>

        </div>
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

// Tab 2 Lazy Init
let tab2Initialized = false;
// Tab 3: AI 分析 Lazy Init
let tab3Initialized = false;
// Tab 4: 成果亮點 Lazy Init
let tab4Initialized = false;

// 成果亮點資料（Python 注入）
const MILESTONES       = {MILESTONES_JSON};
const MILESTONE_LABEL  = {MILESTONE_LABEL_JSON};
const MILESTONE_NOTES  = {MILESTONE_NOTES_JSON};       // 永久補充資料（來自 milestone_notes.json）
const MILESTONE_NOTES_DIR = {MILESTONE_NOTES_DIR_JSON}; // 檔案應存放的資料夾路徑

// AI 分析資料（Python 注入）
const AI_NEW   = {AI_NEW_JSON};
const AI_DONE  = {AI_DONE_JSON};
const AI_RISK  = {AI_RISK_JSON};
const AI_DOING = {AI_DOING_JSON};

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
let currentChildrenMap = {{}}; // 遞迴父子展開用（由 renderParentGroups 更新）

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
    document.getElementById('t1-risk-swim-filter').innerHTML = '<option value="">全部主題</option>' + swimOptions;
    document.getElementById('t1-parent-swim-filter').innerHTML = '<option value="">全部主題</option>' + swimOptions;
    const t2ParentSwimEl = document.getElementById('t2-parent-swim-filter');
    if (t2ParentSwimEl) t2ParentSwimEl.innerHTML = '<option value="">全部主題</option>' + swimOptions;

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

// ==================== 🏆 成果亮點 Tab ====================

function initMilestonesTab() {{
    // 顯示正確存放路徑（資料夾名稱）
    const hint = document.getElementById('ms-path-hint');
    if (hint && MILESTONE_NOTES_DIR)
        hint.textContent = MILESTONE_NOTES_DIR + '/milestone_notes.json';

    // 從 milestone_notes.json（Python 注入）seed localStorage
    // 規則：只在 localStorage 尚未有此 key 時才寫入（不覆蓋使用者已編輯的內容）
    try {{
        Object.entries(MILESTONE_NOTES).forEach(([id, data]) => {{
            if (data.note !== undefined && !localStorage.getItem('ms_note_' + id))
                localStorage.setItem('ms_note_' + id, data.note);
            if (data.link !== undefined && !localStorage.getItem('ms_link_' + id))
                localStorage.setItem('ms_link_' + id, data.link);
        }});
    }} catch(e) {{}}

    // 填入主題下拉選單
    const swimSet = new Set(MILESTONES.map(c => c.swimlane));
    const ordered = SWIM_ORDER.filter(s => swimSet.has(s))
        .concat([...swimSet].filter(s => !SWIM_ORDER.includes(s)));
    const sel = document.getElementById('ms-swim-filter');
    ordered.forEach(s => {{
        const opt = document.createElement('option');
        opt.value = s; opt.textContent = s;
        sel.appendChild(opt);
    }});
    renderMilestones();
}}

function _filterMilestones() {{
    const startVal = document.getElementById('ms-date-start')?.value || '';
    const endVal   = document.getElementById('ms-date-end')?.value   || '';
    const swimVal  = document.getElementById('ms-swim-filter')?.value || '';
    return MILESTONES.filter(c => {{
        if (swimVal && c.swimlane !== swimVal) return false;
        if (startVal && c.endAt && c.endAt.slice(0,10) < startVal) return false;
        if (endVal   && c.endAt && c.endAt.slice(0,10) > endVal)   return false;
        return true;
    }});
}}

function _groupMilestonesBySwim(cards) {{
    // 依 SWIM_ORDER 排序各主題
    const map = {{}};
    cards.forEach(c => {{
        if (!map[c.swimlane]) map[c.swimlane] = [];
        map[c.swimlane].push(c);
    }});
    const ordered = SWIM_ORDER.filter(s => map[s]);
    Object.keys(map).forEach(s => {{ if (!ordered.includes(s)) ordered.push(s); }});
    const result = {{}};
    ordered.forEach(s => {{ result[s] = map[s]; }});
    return result;
}}

function _msGetNote(id) {{
    try {{ return localStorage.getItem('ms_note_' + id) || ''; }} catch(e) {{ return ''; }}
}}
function _msGetLink(id) {{
    try {{ return localStorage.getItem('ms_link_' + id) || ''; }} catch(e) {{ return ''; }}
}}

function msSaveNote(id) {{
    const el = document.getElementById('ms-note-input-' + id);
    if (!el) return;
    try {{ localStorage.setItem('ms_note_' + id, el.value); }} catch(e) {{}}
    _msRefreshNote(id);
}}

function msEditNote(id) {{
    document.getElementById('ms-note-display-' + id).style.display = 'none';
    const inp = document.getElementById('ms-note-input-' + id);
    inp.style.display = '';
    inp.focus();
    inp.setSelectionRange(inp.value.length, inp.value.length);
}}

function msBlurNote(id) {{
    msSaveNote(id);
}}

function _msRefreshNote(id) {{
    const note = _msGetNote(id);
    const inp  = document.getElementById('ms-note-input-' + id);
    const disp = document.getElementById('ms-note-display-' + id);
    if (!inp || !disp) return;
    inp.style.display = 'none';
    if (note) {{
        disp.innerHTML = `<div class="ms-note-text" onclick="msEditNote('${{id}}')">${{note.replace(/\\n/g,'<br>')}}</div>`;
    }} else {{
        disp.innerHTML = `<div class="ms-note-placeholder" onclick="msEditNote('${{id}}')">💬 點擊新增說明</div>`;
    }}
    disp.style.display = '';
}}

function msSaveLink(id) {{
    const inp = document.getElementById('ms-link-input-' + id);
    if (!inp) return;
    let url = inp.value.trim();
    if (url && !url.match(/^https?:\\/\\//)) url = 'https://' + url;
    try {{ localStorage.setItem('ms_link_' + id, url); }} catch(e) {{}}
    _msRefreshLink(id);
}}

function msClearLink(id) {{
    try {{ localStorage.removeItem('ms_link_' + id); }} catch(e) {{}}
    _msRefreshLink(id);
}}

function _msRefreshLink(id) {{
    const link = _msGetLink(id);
    const area = document.getElementById('ms-link-area-' + id);
    if (!area) return;
    if (link) {{
        area.innerHTML = `
            <a href="${{link}}" target="_blank" class="ms-link-btn">🔗 查看簡報 →</a>
            <span class="ms-link-clear" onclick="msClearLink('${{id}}')">✕</span>`;
    }} else {{
        area.innerHTML = `
            <input id="ms-link-input-${{id}}" class="ms-link-input"
                   placeholder="🔗 貼入簡報連結…"
                   onblur="msSaveLink('${{id}}')"
                   onkeydown="if(event.key==='Enter')msSaveLink('${{id}}')">`;
    }}
}}

function _msBuildNotesJSON() {{
    const result = {{}};
    MILESTONES.forEach(c => {{
        const note = _msGetNote(c.id);
        const link = _msGetLink(c.id);
        if (note || link) result[c.id] = {{ note, link, title: c.title }};
    }});
    // 保留歷史資料（不在目前卡片中的 entry）
    Object.entries(MILESTONE_NOTES).forEach(([id, data]) => {{
        if (!result[id]) result[id] = data;
    }});
    return JSON.stringify(result, null, 2);
}}

function _msSaveFeedback() {{
    const btn = document.getElementById('ms-save-btn');
    if (!btn) return;
    btn.textContent = '✅ 已儲存！';
    setTimeout(() => {{ btn.textContent = '💾 儲存補充資料'; }}, 2500);
}}

function _msFallbackDownload(jsonStr) {{
    const blob = new Blob([jsonStr], {{ type: 'application/json;charset=utf-8' }});
    const url  = URL.createObjectURL(blob);
    const a    = document.createElement('a');
    a.href = url; a.download = 'milestone_notes.json';
    document.body.appendChild(a); a.click();
    document.body.removeChild(a); URL.revokeObjectURL(url);
}}

async function saveMilestoneNotes() {{
    const jsonStr = _msBuildNotesJSON();
    if (window.showSaveFilePicker) {{
        try {{
            const handle = await window.showSaveFilePicker({{
                suggestedName: 'milestone_notes.json',
                types: [{{ description: 'JSON 檔案', accept: {{ 'application/json': ['.json'] }} }}]
            }});
            const writable = await handle.createWritable();
            await writable.write(jsonStr);
            await writable.close();
            _msSaveFeedback();
        }} catch(e) {{
            if (e.name !== 'AbortError') _msFallbackDownload(jsonStr);
            // AbortError = 使用者按取消，不做任何事
        }}
    }} else {{
        // 不支援 showSaveFilePicker（Firefox 等）→ 直接下載
        _msFallbackDownload(jsonStr);
        _msSaveFeedback();
    }}
}}

function _msStatusBadge(c) {{
    if (c.isDone) return `<span class="ms-status-badge ms-done">✅ 已完成</span>`;
    if (c.list === 'Doing')   return `<span class="ms-status-badge ms-doing">▶ Doing${{c.isStale ? ` · 停滯${{c.staleDays}}天` : ''}}</span>`;
    if (c.list === 'Waiting') return `<span class="ms-status-badge ms-waiting">⏸ Waiting</span>`;
    if (c.list === 'Review / 使用者Test') return `<span class="ms-status-badge ms-review">🔍 Review</span>`;
    return `<span class="ms-status-badge ms-other">${{c.list}}</span>`;
}}

function _msDateLine(c) {{
    if (c.isDone && c.endAtDisplay !== '—')
        return `完成：${{c.endAtDisplay}}`;
    if (c.dueAtDisplay)
        return `預計：${{c.dueAtDisplay}}`;
    if (c.lastActDisplay !== '—')
        return `最後活動：${{c.lastActDisplay}}`;
    return '';
}}

function renderMilestones() {{
    const filtered = _filterMilestones();
    document.getElementById('ms-count').textContent = `共 ${{filtered.length}} 個里程碑`;

    const content = document.getElementById('ms-content');
    if (!content) return;

    if (filtered.length === 0) {{
        content.innerHTML = `<div class="ms-empty">目前沒有符合條件的里程碑卡片<br><small>請在 Wekan 卡片上加入「${{MILESTONE_LABEL}}」標籤</small></div>`;
        return;
    }}

    const groups = _groupMilestonesBySwim(filtered);
    let html = '';
    Object.entries(groups).forEach(([swim, cards]) => {{
        html += `<div class="ms-swim-header">── 主題：${{swim}}（${{cards.length}} 個里程碑）</div>`;
        cards.forEach(c => {{
            const note    = _msGetNote(c.id);
            const link    = _msGetLink(c.id);
            const membersStr = c.members.length ? '👤 ' + c.members.join('・') : '👤 未指定';
            const dateLine   = _msDateLine(c);

            const noteDisplayHtml = note
                ? `<div class="ms-note-text" onclick="msEditNote('${{c.id}}')">${{note.replace(/\\n/g,'<br>')}}</div>`
                : `<div class="ms-note-placeholder" onclick="msEditNote('${{c.id}}')">💬 點擊新增說明</div>`;

            const linkHtml = link
                ? `<a href="${{link}}" target="_blank" class="ms-link-btn">🔗 查看簡報 →</a>
                   <span class="ms-link-clear" onclick="msClearLink('${{c.id}}')">✕</span>`
                : `<input id="ms-link-input-${{c.id}}" class="ms-link-input"
                          placeholder="🔗 貼入簡報連結…"
                          onblur="msSaveLink('${{c.id}}')"
                          onkeydown="if(event.key==='Enter')msSaveLink('${{c.id}}')">`;

            html += `
            <div class="ms-card${{c.isDone ? ' ms-card-done' : ''}}">
                <div class="ms-card-title">
                    <div class="ms-card-title-left">🏆 ${{cardLink(c.id, c.title)}}</div>
                    ${{_msStatusBadge(c)}}
                </div>
                <div class="ms-card-meta-row">
                    <span class="ms-card-members">${{membersStr}}</span>
                    ${{dateLine ? `<span class="ms-card-date">${{dateLine}}</span>` : ''}}
                </div>
                ${{c.desc ? `<div class="ms-card-desc">↳ ${{c.desc}}</div>` : ''}}
                <div class="ms-note-area">
                    <div id="ms-note-display-${{c.id}}">${{noteDisplayHtml}}</div>
                    <textarea id="ms-note-input-${{c.id}}" class="ms-note-input"
                        style="display:none"
                        onblur="msBlurNote('${{c.id}}')"
                    >${{note}}</textarea>
                </div>
                <div class="ms-link-area" id="ms-link-area-${{c.id}}">${{linkHtml}}</div>
            </div>`;
        }});
    }});

    content.innerHTML = html;
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
    }} else if (name === 'personal') {{
        document.getElementById('main-panel-personal').classList.add('active');
        btns[1].classList.add('active');
        if (!tab2Initialized) {{
            tab2Initialized = true;
            applyFilters2();
        }}
    }} else if (name === 'ai') {{
        document.getElementById('main-panel-ai').classList.add('active');
        btns[2].classList.add('active');
        if (!tab3Initialized) {{
            tab3Initialized = true;
            initAITab();
        }}
    }} else if (name === 'milestones') {{
        document.getElementById('main-panel-milestones').classList.add('active');
        btns[3].classList.add('active');
        if (!tab4Initialized) {{
            tab4Initialized = true;
            initMilestonesTab();
        }}
    }}
}}

// ==================== AI 分析 Tab ====================

function _groupBySwimlane(cards) {{
    const map = {{}};
    cards.forEach(c => {{
        if (!map[c.swimlane]) map[c.swimlane] = [];
        map[c.swimlane].push(c);
    }});
    return map;
}}

function initAITab() {{
    renderAIPreview();
    const saved = localStorage.getItem('ai_analysis_notes');
    if (saved) {{
        document.getElementById('ai-notes').value = saved;
    }}
    // 預設顯示「檢視」模式
    setAIMode('view');
}}

// 簡易 Markdown → HTML 轉換（支援 ##標題、**粗體**、- 列表、--- 分隔線、段落）
function simpleMarkdown(md) {{
    if (!md || !md.trim()) return '';
    let html = md
        .replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;')
        .replace(/^### (.+)$/gm, '<h3>$1</h3>')
        .replace(/^## (.+)$/gm,  '<h2>$1</h2>')
        .replace(/^# (.+)$/gm,   '<h1>$1</h1>')
        .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
        .replace(/\*(.+?)\*/g,    '<em>$1</em>')
        .replace(/^---+$/gm,      '<hr>')
        .replace(/^[-•] (.+)$/gm, '<li>$1</li>')
        .replace(/(<li>[\s\S]*?<\/li>)/g, '<ul>$1</ul>')
        .replace(/<\/ul>\s*<ul>/g, '')
        .split(/\\n{{2,}}/)
        .map(block => {{
            if (/^<(h[123]|ul|hr|li)/.test(block.trim())) return block;
            return `<p>${{block.replace(/\\n/g,'<br>')}}</p>`;
        }})
        .join('');
    return html;
}}

let _currentAIMode = 'view';
function setAIMode(mode) {{
    _currentAIMode = mode;
    const textarea  = document.getElementById('ai-notes');
    const viewDiv   = document.getElementById('ai-notes-view');
    const placeholder = document.getElementById('ai-notes-placeholder');
    const btnView   = document.getElementById('ai-mode-view');
    const btnEdit   = document.getElementById('ai-mode-edit');
    const content   = textarea.value.trim();

    btnView.classList.toggle('active', mode === 'view');
    btnEdit.classList.toggle('active', mode === 'edit');

    if (mode === 'view') {{
        textarea.style.display  = 'none';
        if (content) {{
            viewDiv.innerHTML = simpleMarkdown(textarea.value);
            viewDiv.style.display = 'block';
            placeholder.style.display = 'none';
        }} else {{
            viewDiv.style.display = 'none';
            placeholder.style.display = 'block';
        }}
    }} else {{
        viewDiv.style.display    = 'none';
        placeholder.style.display = 'none';
        textarea.style.display   = 'block';
        textarea.focus();
    }}
}}

function renderAIPreview() {{
    const box = document.getElementById('ai-preview-box');
    if (!box) return;
    const sections = [
        {{ data: AI_DONE,  icon: '✅', label: '本週完成',
           row: c => `${{c.title}}<span class="ai-card-meta">（${{c.members.join('、')||'無負責人'}}）</span>`,
           showDesc: true }},
        {{ data: AI_NEW,   icon: '📥', label: '本週新增',
           row: c => `${{c.title}}<span class="ai-card-meta">（${{c.members.join('、')||'無負責人'}}，${{c.list}}）</span>`,
           showDesc: false }},
        {{ data: AI_RISK,  icon: '⚠️', label: '目前風險',
           row: c => {{
               const t = [];
               if (c.isOverdue) t.push('逾期');
               if (c.isDueSoon) t.push(`⚡ 即將到期：${{c.dueAtDisplay}}`);
               if (c.isStale)   t.push(`停滯${{c.staleDays}}天`);
               return `${{c.title}}<span class="ai-card-meta">（${{t.join('、')}}）</span>`;
           }}, showDesc: false }},
        {{ data: AI_DOING, icon: '▶️', label: 'Doing 中',
           row: c => `${{c.title}}<span class="ai-card-meta">（${{c.members.join('、')||'無負責人'}}，${{c.isStale?`停滯${{c.staleDays}}天`:'活躍'}}）</span>`,
           showDesc: false }},
    ];
    let html = '';
    sections.forEach(s => {{
        const groups = _groupBySwimlane(s.data);
        html += `<div class="ai-section"><div class="ai-section-title">${{s.icon}} ${{s.label}}（${{s.data.length}} 張）</div>`;
        if (s.data.length === 0) {{
            html += `<div class="ai-empty">無資料</div>`;
        }} else {{
            Object.entries(groups).forEach(([swim, cards]) => {{
                html += `<div class="ai-swim-group"><span class="ai-swim-name">主題：${{swim}}</span>`;
                cards.forEach(c => {{
                    html += `<div class="ai-card-row">• ${{s.row(c)}}</div>`;
                    if (s.showDesc && c.desc) {{
                        html += `<div class="ai-card-desc">↳ ${{c.desc}}</div>`;
                    }}
                }});
                html += `</div>`;
            }});
        }}
        html += `</div>`;
    }});
    box.innerHTML = html;
}}

function buildAICopyText() {{
    const fmtDesc = desc => desc ? `\n      └ ${{desc}}` : '';
    const fmt = (cards, rowFn) => {{
        if (cards.length === 0) return '  （無）\\n';
        const groups = _groupBySwimlane(cards);
        let s = '';
        Object.entries(groups).forEach(([swim, items]) => {{
            s += `主題：${{swim}}\n`;
            items.forEach(c => {{ s += `  - ${{rowFn(c)}}${{fmtDesc(c.desc)}}\n`; }});
        }});
        return s;
    }};
    return [
        `【本週完成 ${{AI_DONE.length}} 張】`,
        fmt(AI_DONE,  c => `${{c.title}}（負責人：${{c.members.join('、')||'無'}}）`),
        `【本週新增 ${{AI_NEW.length}} 張】`,
        fmt(AI_NEW,   c => `${{c.title}}（負責人：${{c.members.join('、')||'無'}}，欄位：${{c.list}}）`),
        `【目前風險 ${{AI_RISK.length}} 張】`,
        fmt(AI_RISK,  c => {{
            const t = [];
            if (c.isOverdue) t.push('逾期');
            if (c.isDueSoon) t.push(`⚡ 即將到期：${{c.dueAtDisplay}}`);
            if (c.isStale)   t.push(`停滯${{c.staleDays}}天`);
            return `${{c.title}}（${{t.join('、')}}）`;
        }}),
        `【Doing 中 ${{AI_DOING.length}} 張】`,
        fmt(AI_DOING, c => `${{c.title}}（負責人：${{c.members.join('、')||'無'}}，${{c.isStale?`停滯${{c.staleDays}}天`:'活躍'}}）`),
        '---',
        '請根據以上資料：',
        '1. 總結本週團隊推展的主要方向',
        '2. 說明完成任務的意義與進展',
        '3. 結合風險現況，建議下週應優先推進的方向',
    ].join('\\n');
}}

function copyAIData() {{
    navigator.clipboard.writeText(buildAICopyText()).then(() => {{
        const btn = document.getElementById('ai-copy-btn');
        btn.textContent = '✅ 已複製！';
        setTimeout(() => {{ btn.textContent = '📋 複製 AI 分析資料'; }}, 1500);
    }});
}}

// 從 Python 注入的設定
const AI_SAVE_FOLDER    = "{AI_SAVE_FOLDER}";
const AI_FILENAME_PREFIX = "{AI_FILENAME_PREFIX}";

function _buildAISaveFilename() {{
    const now = new Date();
    const pad = n => String(n).padStart(2,'0');
    const dateStr = `${{now.getFullYear()}}${{pad(now.getMonth()+1)}}${{pad(now.getDate())}}`;
    const timeStr = `${{pad(now.getHours())}}${{pad(now.getMinutes())}}`;
    return `${{AI_FILENAME_PREFIX}}_${{dateStr}}_${{timeStr}}.md`;
}}

function _buildAISaveContent(filename) {{
    const raw = document.getElementById('ai-notes').value;
    // 從檔名解析日期時間顯示
    const m = filename.match(/_(\d{{4}})(\d{{2}})(\d{{2}})_(\d{{2}})(\d{{2}})/);
    const stamp = m ? `${{m[1]}}-${{m[2]}}-${{m[3]}} ${{m[4]}}:${{m[5]}}` : '';
    return `# AI 週報分析  ${{stamp}}\\n\\n${{raw}}`;
}}

async function saveAIToFile() {{
    const content = document.getElementById('ai-notes').value.trim();
    if (!content) {{
        alert('尚無分析內容，請先切換到「✏️ 編輯」模式，貼入 AI 分析結果後再儲存。');
        return;
    }}

    const btn      = document.getElementById('ai-save-btn');
    const filename = _buildAISaveFilename();
    const text     = _buildAISaveContent(filename);

    // 優先使用 File System Access API（Chrome/Edge 支援，會開啟原生另存視窗）
    if (window.showSaveFilePicker) {{
        try {{
            const handle = await window.showSaveFilePicker({{
                suggestedName: filename,
                types: [{{ description: 'Markdown 檔案', accept: {{ 'text/markdown': ['.md'] }} }}]
            }});
            const writable = await handle.createWritable();
            await writable.write(text);
            await writable.close();
            btn.textContent = '✅ 已儲存！';
            setTimeout(() => {{ btn.textContent = '💾 儲存本週分析'; }}, 2000);
            return;
        }} catch(e) {{
            if (e.name === 'AbortError') return; // 使用者取消，不做任何事
            // 其他錯誤則 fallback 到 Blob 下載
        }}
    }}

    // Fallback：Blob 下載（Firefox / Safari / 舊版瀏覽器）
    const blob = new Blob([text], {{ type: 'text/markdown;charset=utf-8' }});
    const url  = URL.createObjectURL(blob);
    const a    = document.createElement('a');
    a.href = url; a.download = filename;
    document.body.appendChild(a); a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);

    btn.textContent = '✅ 已下載！';
    setTimeout(() => {{ btn.textContent = '💾 儲存本週分析'; }}, 2000);
}}

let _aiNoteTimer = null;
function saveAINotes() {{
    clearTimeout(_aiNoteTimer);
    _aiNoteTimer = setTimeout(() => {{
        const val = document.getElementById('ai-notes').value;
        localStorage.setItem('ai_analysis_notes', val);
        // 若切換到檢視模式時即時更新
        if (_currentAIMode === 'view') setAIMode('view');
    }}, 500);
}}

// ==================== Sub-Tab Switch ====================

// 需求 #4: 展開/折疊父任務組
// ==================== 父子結構：遞迴分組排序 ====================

// 父任務狀態 Tab 切換（Feature C-3）
function switchParentStatusTab(tabName, statusIdx) {{
    const container = document.getElementById(tabName + '-parent-container');
    if (!container) return;
    // 切換 tab 按鈕 active
    container.querySelectorAll('.parent-status-tab-bar .sub-tab-btn').forEach((b, i) => {{
        b.classList.toggle('active', i === statusIdx);
    }});
    // 切換 panel
    container.querySelectorAll('.parent-status-panel').forEach((p, i) => {{
        p.classList.toggle('active', i === statusIdx);
    }});
}}

// 欄位分組順序（優先待處理，完成放最下）
const CHILD_LIST_ORDER = ['Doing','Waiting','Review / 使用者Test','Ready to GO','準備中','Backlog','Closed','DONE'];

// 取得欄位排序權重（未知欄位放中間）
function listRank(listName) {{
    const idx = CHILD_LIST_ORDER.indexOf(listName);
    return idx === -1 ? CHILD_LIST_ORDER.length - 2 : idx;
}}

// 組內排序
function sortCardsInGroup(cards, listName) {{
    return [...cards].sort((a, b) => {{
        let da, db;
        if (listName === 'DONE') {{
            da = a.endAt ? new Date(a.endAt) : new Date(a.dateLastActivity || 0);
            db = b.endAt ? new Date(b.endAt) : new Date(b.dateLastActivity || 0);
        }} else {{
            da = new Date(a.dateLastActivity || 0);
            db = new Date(b.dateLastActivity || 0);
        }}
        return db - da; // 新 → 舊
    }});
}}

// 遞迴渲染子任務（帶分組標題，depth 控制縮排）
function renderChildrenRecursive(parentId, childrenMap, depth) {{
    const children = childrenMap[parentId] || [];
    if (children.length === 0) return '';

    // 依欄位分組
    const groups = {{}};
    children.forEach(c => {{
        const key = c.list || '未知';
        if (!groups[key]) groups[key] = [];
        groups[key].push(c);
    }});

    // 依 CHILD_LIST_ORDER 排序分組
    const sortedLists = Object.keys(groups).sort((a, b) => listRank(a) - listRank(b));

    const indentPx = depth * 20;
    const indentStyle = `padding-left:${{indentPx + 8}}px`;
    let html = '';

    sortedLists.forEach(listName => {{
        const groupCards = sortCardsInGroup(groups[listName], listName);

        // 分組標題列
        html += `<tr class="child-list-group-header">
            <td colspan="7" style="${{indentStyle}}">
                <span class="child-depth-marker">${{'│ '.repeat(depth)}}</span>▶ ${{listName}} (${{groupCards.length}})
            </td>
        </tr>`;

        // 組內卡片
        groupCards.forEach(c => {{
            const staleClass = c.isStale ? 'stale-badge' : 'active-badge';
            const staleLabel = c.isDone ? '完成' : (c.isStale ? `停滯${{c.staleDays}}天` : '活躍');
            const hasGrandChildren = (childrenMap[c.id] || []).length > 0;
            const titlePrefix = hasGrandChildren ? '📁 ' : '';
            html += `<tr>
                <td style="padding-left:${{indentPx + 12}}px">${{c.swimlane || '—'}}</td>
                <td>${{titlePrefix}}${{cardLink(c.id, c.title)}}</td>
                <td><span class="badge">${{c.list}}</span></td>
                <td>${{c.members.join(', ') || '—'}}</td>
                <td>${{(c.dateLastActivity || '').slice(0, 10)}}</td>
                <td>${{c.staleDays != null ? c.staleDays : '—'}}</td>
                <td><span class="badge ${{staleClass}}">${{staleLabel}}</span></td>
            </tr>`;
            // 遞迴展開孫任務
            if (hasGrandChildren) {{
                html += renderChildrenRecursive(c.id, childrenMap, depth + 1);
            }}
        }});
    }});

    return html;
}}

// toggleGroup：父任務點擊展開/收合
function toggleGroup(el, groupKey, parentId) {{
    const body = el.nextElementSibling;
    const isOpen = body.style.display !== 'none';

    if (!isOpen && body.innerHTML === '') {{
        if (parentId) {{
            // 父任務群組：遞迴渲染所有後代
            const rows = renderChildrenRecursive(parentId, currentChildrenMap, 0);
            body.innerHTML = `<table><thead><tr>
                <th>主題</th><th>卡片名稱</th><th>欄位</th><th>負責人</th>
                <th>最後活動日</th><th>停滯天數</th><th>狀態</th>
            </tr></thead><tbody>${{rows || '<tr><td colspan="7" style="color:#999;text-align:center">無子任務</td></tr>'}}</tbody></table>`;
        }} else {{
            // 獨立卡片群組：平面渲染（原邏輯）
            const children = parentGroupData[groupKey] || [];
            children.sort((a, b) => new Date(b.dateLastActivity || 0) - new Date(a.dateLastActivity || 0));
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
                <th>主題</th><th>卡片名稱</th><th>欄位</th><th>負責人</th>
                <th>最後活動日</th><th>停滯天數</th><th>狀態</th>
            </tr></thead><tbody>${{rows || '<tr><td colspan="7" style="color:#999;text-align:center">無資料</td></tr>'}}</tbody></table>`;
        }}
    }}

    body.style.display = isOpen ? 'none' : '';
    const arrow = el.querySelector('.pg-arrow');
    if (arrow) arrow.textContent = isOpen ? '▶' : '▼';
}}

// 改動 A4: switchNewDone 函式
function switchNewDone(tab, name) {{
    ['new','done','activity','compare'].forEach(n => {{
        const panel = document.getElementById(tab + '-nd-' + n);
        const btn = document.getElementById(tab + '-nd-btn-' + n);
        if (panel) panel.style.display = n === name ? '' : 'none';
        if (btn) btn.classList.toggle('active', n === name);
    }});
    // 主題對照：lazy render
    if (name === 'compare') {{
        const tabN = tab === 't1' ? 1 : 2;
        _renderNDCompareIfNeeded(tabN);
    }}
}}

// 主題對照 lazy render flag + 排序覆寫（localStorage 持久化）
let _ndCmpDirty = {{ 1: true, 2: true }};
let _ndCmpOrderOverride = (function() {{
    try {{ return JSON.parse(localStorage.getItem('ndCmpSwimOrder') || 'null'); }}
    catch(e) {{ return null; }}
}})();

// ── Drag & Drop handlers ──────────────────────────────────
let _ndDragSrcRow = null;

function _ndDragStart(e) {{
    _ndDragSrcRow = e.currentTarget;
    e.dataTransfer.effectAllowed = 'move';
    setTimeout(() => {{ if (_ndDragSrcRow) _ndDragSrcRow.style.opacity = '0.4'; }}, 0);
}}

function _ndDragEnd(e) {{
    e.currentTarget.style.opacity = '';
    document.querySelectorAll('.nd-cmp-row').forEach(r => r.classList.remove('drag-over'));
    _ndDragSrcRow = null;
}}

function _ndDragOver(e) {{
    e.preventDefault();
    e.dataTransfer.dropEffect = 'move';
    if (_ndDragSrcRow && e.currentTarget !== _ndDragSrcRow) {{
        document.querySelectorAll('.nd-cmp-row').forEach(r => r.classList.remove('drag-over'));
        e.currentTarget.classList.add('drag-over');
    }}
}}

function _ndDragLeave(e) {{
    e.currentTarget.classList.remove('drag-over');
}}

function _ndDrop(e, tabN) {{
    e.preventDefault();
    const tgt = e.currentTarget;
    tgt.classList.remove('drag-over');
    if (!_ndDragSrcRow || _ndDragSrcRow === tgt) return;

    // 讀取目前所有列的主題順序
    const container = _ndDragSrcRow.closest('.nd-cmp-table');
    if (!container) return;
    const rows = Array.from(container.querySelectorAll('.nd-cmp-row[data-swim]'));
    const swims = rows.map(r => r.dataset.swim);

    const srcIdx = rows.indexOf(_ndDragSrcRow);
    const tgtIdx = rows.indexOf(tgt);
    if (srcIdx < 0 || tgtIdx < 0) return;

    // 移動
    swims.splice(tgtIdx, 0, swims.splice(srcIdx, 1)[0]);

    // 儲存並重繪
    _ndCmpOrderOverride = swims;
    try {{ localStorage.setItem('ndCmpSwimOrder', JSON.stringify(swims)); }} catch(ex) {{}}

    _ndCmpDirty[1] = true;
    _ndCmpDirty[2] = true;
    _renderNDCompareIfNeeded(tabN);
}}

// ─────────────────────────────────────────────────────────

function toggleNDPipeline(headEl) {{
    const row = headEl.closest('.nd-cmp-row');
    if (!row) return;
    const pipeline = row.querySelector('.nd-cmp-pipeline');
    const arrow    = headEl.querySelector('.nd-cmp-expand-arrow');
    if (!pipeline) return;
    const isOpen = pipeline.style.display !== 'none';
    pipeline.style.display = isOpen ? 'none' : '';
    if (arrow) arrow.textContent = isOpen ? '▶' : '▼';
}}

function _renderNDCompareIfNeeded(tabN) {{
    if (!_ndCmpDirty[tabN]) return;
    _ndCmpDirty[tabN] = false;
    const cards = tabN === 1 ? filteredCards1 : filteredCards2;
    const dates  = tabN === 1 ? t1FilterDates  : t2FilterDates;
    if (!cards || !dates.startDt) return;
    const {{ startDt, endDt }} = dates;

    const newCards = cards.filter(c => {{
        const ct = c.createdAt ? new Date(c.createdAt) : null;
        return ct && ct >= startDt && ct <= endDt && !c.archived;
    }});
    const doneCards = cards.filter(c => {{
        const et = c.endAt ? new Date(c.endAt) : null;
        return c.isDone && et && et >= startDt && et <= endDt;
    }});

    const wrap = document.getElementById('t' + tabN + '-nd-cmp-wrap');
    if (wrap) wrap.innerHTML = _buildNDCompareHTML(newCards, doneCards, tabN, cards);
}}

function _buildNDCompareHTML(newCards, doneCards, tabN, allCards) {{
    // 取兩側主題聯集
    const swimSet = new Set([...newCards.map(c => c.swimlane), ...doneCards.map(c => c.swimlane)]);
    let swims = Array.from(swimSet);

    // 排序：localStorage 覆寫 > SWIM_ORDER > 字母
    if (_ndCmpOrderOverride && _ndCmpOrderOverride.length > 0) {{
        const ordered = [];
        _ndCmpOrderOverride.forEach(s => {{ if (swims.includes(s)) ordered.push(s); }});
        swims.forEach(s => {{ if (!ordered.includes(s)) ordered.push(s); }});
        swims = ordered;
    }} else if (SWIM_ORDER.length > 0) {{
        swims.sort((a, b) => {{
            const ia = SWIM_ORDER.indexOf(a), ib = SWIM_ORDER.indexOf(b);
            return (ia < 0 ? 9999 : ia) - (ib < 0 ? 9999 : ib);
        }});
    }} else {{
        swims.sort();
    }}

    // 依主題分組
    const bySwimNew  = {{}};
    const bySwimDone = {{}};
    newCards.forEach(c  => {{ (bySwimNew[c.swimlane]  = bySwimNew[c.swimlane]  || []).push(c); }});
    doneCards.forEach(c => {{ (bySwimDone[c.swimlane] = bySwimDone[c.swimlane] || []).push(c); }});

    const cardRow = c => {{
        const members = c.members && c.members.length ? c.members.join('、') : '無負責人';
        return `<div class="nd-cmp-card">${{cardLink(c.id, c.title)}}<span class="nd-cmp-card-member">（${{members}}）</span></div>`;
    }};

    // Pipeline 卡片清單（allCards = 篩選後全部卡片，不限日期）
    const pipeBySwim = {{}};
    if (allCards) {{
        allCards.forEach(c => {{
            if (!pipeBySwim[c.swimlane]) pipeBySwim[c.swimlane] = {{ doing:[], waiting:[], review:[] }};
            if (c.isDoing)   pipeBySwim[c.swimlane].doing.push(c);
            if (c.isWaiting) pipeBySwim[c.swimlane].waiting.push(c);
            if (c.isReview)  pipeBySwim[c.swimlane].review.push(c);
        }});
    }}

    // Pipeline 欄 HTML helper
    const pipeColHTML = (cards, type) => {{
        const hdrClass = type === 'doing' ? 'doing-hdr' : type === 'waiting' ? 'waiting-hdr' : 'review-hdr';
        const icon     = type === 'doing' ? '🔄'        : type === 'waiting' ? '⏳'           : '👁';
        const label    = type === 'doing' ? 'Doing'     : type === 'waiting' ? 'Waiting'      : 'Review';
        const hdr = `<div class="nd-cmp-pipe-col-hdr ${{hdrClass}}">${{icon}} ${{label}} (${{cards.length}})</div>`;
        return hdr + (cards.length ? cards.map(cardRow).join('') : '<div class="nd-cmp-empty">無</div>');
    }};

    let rowsHtml = '';
    swims.forEach(swim => {{
        const nc = bySwimNew[swim]  || [];
        const dc = bySwimDone[swim] || [];
        const newCellHTML  = nc.length ? nc.map(cardRow).join('') : '<div class="nd-cmp-empty">本週無新增</div>';
        const doneCellHTML = dc.length ? dc.map(cardRow).join('') : '<div class="nd-cmp-empty">本週無完成</div>';

        // Pipeline badge（數字）
        const pipe = pipeBySwim[swim] || {{ doing:[], waiting:[], review:[] }};
        const dN = pipe.doing.length, wN = pipe.waiting.length, rN = pipe.review.length;
        const badgeHtml = `<div class="nd-cmp-pipe-badges">
            <span class="nd-cmp-pipe-badge doing${{dN===0?' zero':''}}">Doing ${{dN}}</span>
            <span class="nd-cmp-pipe-badge waiting${{wN===0?' zero':''}}">Waiting ${{wN}}</span>
            <span class="nd-cmp-pipe-badge review${{rN===0?' zero':''}}">Review ${{rN}}</span>
        </div>`;

        // Pipeline 展開區（預設隱藏）
        const pipelineHTML = `<div class="nd-cmp-pipeline" style="display:none">
            <div class="nd-cmp-pipe-cols">
                <div class="nd-cmp-pipe-col">${{pipeColHTML(pipe.doing,   'doing'  )}}</div>
                <div class="nd-cmp-pipe-col">${{pipeColHTML(pipe.waiting, 'waiting')}}</div>
                <div class="nd-cmp-pipe-col">${{pipeColHTML(pipe.review,  'review' )}}</div>
            </div>
        </div>`;

        rowsHtml += `<div class="nd-cmp-row" data-swim="${{swim}}" draggable="true"
            ondragstart="_ndDragStart(event)"
            ondragend="_ndDragEnd(event)"
            ondragover="_ndDragOver(event)"
            ondragleave="_ndDragLeave(event)"
            ondrop="_ndDrop(event,${{tabN}})">
            <div class="nd-cmp-row-head" onclick="toggleNDPipeline(this)">
                <span class="nd-cmp-drag-handle" ondragstart="event.stopPropagation()" onclick="event.stopPropagation()">⠿</span>
                <span class="nd-cmp-swim-name">${{swim}}</span>
                ${{badgeHtml}}
                <span class="nd-cmp-expand-arrow">▶</span>
            </div>
            ${{pipelineHTML}}
            <div class="nd-cmp-row-body">
                <div class="nd-cmp-cell">${{doneCellHTML}}</div>
                <div class="nd-cmp-cell">${{newCellHTML}}</div>
            </div>
        </div>`;
    }});
    if (!rowsHtml) rowsHtml = '<div style="padding:12px;color:#aaa;font-style:italic;text-align:center;">本期無資料</div>';

    return `<div class="nd-cmp-table">
        <div class="nd-cmp-hdr-row">
            <div class="nd-cmp-hdr-drag"></div>
            <div class="nd-cmp-hdr-cell done-hdr">✅ 本週完成（${{doneCards.length}} 張）</div>
            <div class="nd-cmp-hdr-cell new-hdr">📥 本週新增（${{newCards.length}} 張）</div>
        </div>
        ${{rowsHtml}}
    </div>`;
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

    const panelMap = {{ overview: 'risk-subpanel-overview', swim: 'risk-subpanel-swim', newrisk: 'risk-subpanel-newrisk', duesoon: 'risk-subpanel-duesoon' }};
    if (panelMap[name]) document.getElementById(panelMap[name]).classList.add('active');
    if (event && event.target) event.target.classList.add('active');
}}

// KPI 卡片統一跳轉函式
function jumpToKPI(type) {{
    switchMainTab('overview');
    if (type === 'done') {{
        // → 本週動態 > 本週完成 mini-tab
        _switchTab1Direct('newdone');
        _activateNewDoneMiniTab('t1', 'done');
    }} else if (type === 'new') {{
        // → 本週動態 > 本週新增 mini-tab
        _switchTab1Direct('newdone');
        _activateNewDoneMiniTab('t1', 'new');
    }} else if (type === 'newrisk') {{
        // → 風險與停滯 > 本週新風險 sub-panel
        _switchTab1Direct('risk');
        _switchRiskSubTabDirect('newrisk');
    }} else if (type === 'duesoon') {{
        // → 風險與停滯 > 即將到期 sub-panel
        _switchTab1Direct('risk');
        _switchRiskSubTabDirect('duesoon');
    }} else if (type === 'doing') {{
        // → Doing 明細
        _switchTab1Direct('doing');
    }}
    // 捲動到子分頁區域
    setTimeout(() => {{
        const el = document.getElementById('t1-sub-tab-bar') || document.querySelector('#main-panel-overview .sub-tab-bar');
        if (el) el.scrollIntoView({{ behavior: 'smooth', block: 'start' }});
    }}, 50);
}}

// 不依賴 event 的 Tab1 切換（供 jumpToKPI 呼叫）
function _switchTab1Direct(name) {{
    const panels = ['newdone', 'doing', 'risk', 'parent', 'all'];
    document.querySelectorAll('#main-panel-overview .sub-panel').forEach(p => p.classList.remove('active'));
    document.querySelectorAll('#main-panel-overview .sub-tab-btn').forEach(b => b.classList.remove('active'));
    if (panels.includes(name)) {{
        t1SubTab = name;
        document.getElementById(`t1-panel-${{name}}`).classList.add('active');
        // 點亮對應按鈕（依 onclick 內容比對）
        const btn = [...document.querySelectorAll('#main-panel-overview > .sub-tab-bar .sub-tab-btn')]
            .find(b => b.getAttribute('onclick') && b.getAttribute('onclick').includes(`'${{name}}'`));
        if (btn) btn.classList.add('active');
        if (name === 'all' || name === 'parent') renderT1Panel(name);
    }}
}}

// 不依賴 event 的風險子分頁切換
function _switchRiskSubTabDirect(name) {{
    riskSubTab = name;
    document.querySelectorAll('#t1-panel-risk .sub-panel').forEach(p => p.classList.remove('active'));
    document.querySelectorAll('#t1-panel-risk .sub-tab-btn').forEach(b => b.classList.remove('active'));
    const panel = document.getElementById(`risk-subpanel-${{name}}`);
    if (panel) panel.classList.add('active');
    const btn = [...document.querySelectorAll('#t1-panel-risk .sub-tab-btn')]
        .find(b => b.getAttribute('onclick') && b.getAttribute('onclick').includes(`'${{name}}'`));
    if (btn) btn.classList.add('active');
}}

// 不依賴 event 的 mini-tab 切換（供 jumpToKPI 呼叫）
function _activateNewDoneMiniTab(tab, type) {{
    // 觸發 switchNewDone 但不依賴 event
    const btnId = `${{tab}}-nd-btn-${{type}}`;
    const btn = document.getElementById(btnId);
    if (btn) {{
        // 更新 active 樣式
        document.querySelectorAll(`#${{tab}}-panel-newdone .mini-tab-btn`).forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
    }}
    // 觸發渲染（重用 switchNewDone 邏輯，偽造 event）
    const prevEvent = window.event;
    try {{ switchNewDone(tab, type); }} catch(e) {{}}
}}

function jumpToDueSoon() {{
    jumpToKPI('duesoon');
}}

// 需求 #1 & #3: 風險泳道篩選
function applyRiskSwimFilter() {{
    riskSwimFilter = document.getElementById('t1-risk-swim-filter').value;
    updateRiskTables(filteredCards1);
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

// 主題交替底色（方案 A）：依 SWIM_ORDER 位置奇偶決定
// 偶數索引 = 白色（無額外 class），奇數索引 = 淡藍色（row-alt-bg）
const SWIM_COLOR_MAP = {{}};
(SWIM_ORDER.length > 0
    ? SWIM_ORDER
    : [...new Set(RAW.cards.map(c => c.swimlane))]
).forEach((s, i) => {{ SWIM_COLOR_MAP[s] = i % 2; }});
function getSwimRowClass(swimlane) {{
    return SWIM_COLOR_MAP[swimlane] === 1 ? 'row-alt-bg' : '';
}}
function toggleActGroup(el) {{ el.parentElement.classList.toggle('collapsed'); }}

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
    _ndCmpDirty[1] = true;
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
    _ndCmpDirty[2] = true;
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
    return `<a href="${{WEKAN_URL_BASE}}/${{id}}" target="_blank" class="card-link" onclick="event.stopPropagation()">${{title}}</a>`;
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

    // 本週新風險：受篩選器影響（使用 filtered cards）
    const newRiskCount = cards.filter(c =>
        c.isNewRisk && !c.archived &&
        !['DONE','Closed','過往卡片','過往卡片待青','Goal＆專案資訊'].includes(c.list)
    ).length;

    const dueSoonCount = RAW.cards.filter(c => c.isDueSoon && !c.archived).length;

    const kpiHtml = `
        <div class="kpi-card kpi-clickable" style="border-top:3px solid #43a047;" onclick="jumpToKPI('done')" title="點擊查看本週完成明細">
            <div class="kpi-label">本週完成 <span class="info-tip" data-tip="過去 7 天內移入 DONE 欄位的卡片（以 endAt 計算）">ℹ️</span></div>
            <div class="kpi-value">${{doneCount}}</div>
        </div>
        <div class="kpi-card kpi-clickable" style="border-top:3px solid #1976d2;" onclick="jumpToKPI('new')" title="點擊查看本週新增明細">
            <div class="kpi-label">本週新增 <span class="info-tip" data-tip="過去 7 天內新建立的卡片（以 createdAt 計算）">ℹ️</span></div>
            <div class="kpi-value">${{newCount}}</div>
        </div>
        <div class="kpi-card kpi-clickable alert" style="border-top:3px solid #c62828;" onclick="jumpToKPI('newrisk')" title="點擊查看本週新風險明細">
            <div class="kpi-label">本週風險 <span class="info-tip" data-tip="本週才出現的風險卡：本週新逾期（dueAt 在近 7 天到期）＋ 本週才停滯（staleDays 14–20 天）＋ 即將到期；受篩選器影響">ℹ️</span></div>
            <div class="kpi-value">${{newRiskCount}}</div>
        </div>
        <div class="kpi-card kpi-clickable" style="border-top:3px solid #f57f17;" onclick="jumpToKPI('duesoon')" title="點擊查看即將到期明細">
            <div class="kpi-label">⚡ 即將到期 <span class="info-tip" data-tip="dueAt 在 {TODAY_DISPLAY} – {DUE_SOON_END_DISPLAY} 之間的卡片（排除 DONE / Closed；全看板計算，不受篩選器影響；以本儀表板產出日為基準）">ℹ️</span></div>
            <div class="kpi-value">${{dueSoonCount}}</div>
        </div>
        <div class="kpi-card kpi-clickable" style="border-top:3px solid #7b1fa2;" onclick="jumpToKPI('doing')" title="點擊查看 Doing 明細">
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

// 風險分析排除 List（從 team_config.json lists_roles 推導：done + closed + info + backlog）
const RISK_EXCLUDE_LISTS = {RISK_EXCLUDE_JSON};
// Ready to GO 欄位：保留風險，但不顯示「無負責人」badge（尚未接手屬正常）
const READY_LISTS = {READY_NAMES_JSON};
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
    // Ready to GO 卡片不因「無負責人」進入風險（未接手屬正常），但停滯/逾期/即將到期仍保留
    const riskCards = cards.filter(c => {{
        if (!isRiskCard(c)) return false;
        if (c.isStale || c.isOverdue || c.isDueSoon) return true;
        if (c.noMember && !READY_LISTS.includes(c.list)) return true;
        return false;
    }});

    // 更新風險摘要卡
    const summaryEl = document.getElementById('risk-summary-box');
    if (summaryEl) summaryEl.innerHTML = buildRiskSummary(riskCards);

    // 總覽風險：逾期(0) → 即將到期(1) → 停滯(2,天數遞減) → 無負責人(3，Ready to GO 排除)
    const riskTypeRank = c => c.isOverdue ? 0 : c.isDueSoon ? 1 : c.isStale ? 2 :
        (c.noMember && !READY_LISTS.includes(c.list)) ? 3 : 4;
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
        if (c.noMember && !READY_LISTS.includes(c.list))
            badges.push('<span class="badge" style="background:#fff3e0;color:#e65100;">無負責</span>');
        return badges.join(' ') || '-';
    }}

    let riskOverviewHtml = '';
    sortedRisk.forEach(c => {{
        const clProgress = c.hasChecklist ? `${{c.clDone}}/${{c.clTotal}} (${{c.clPct}}%)` : '-';
        riskOverviewHtml += `<tr class="${{getSwimRowClass(c.swimlane)}}">
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
        riskSwimHtml += `<tr class="${{getSwimRowClass(c.swimlane)}}">
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

    // 本週新風險分頁：受篩選器影響（使用 filteredCards1）
    const newRiskCards = cards.filter(c =>
        c.isNewRisk && !c.archived &&
        !['DONE','Closed','過往卡片','過往卡片待青','Goal＆專案資訊'].includes(c.list)
    ).sort((a, b) => {{
        const riskTypeRank = c => c.isOverdue ? 0 : c.isDueSoon ? 1 : c.isStale ? 2 : 3;
        const rankDiff = riskTypeRank(a) - riskTypeRank(b);
        if (rankDiff !== 0) return rankDiff;
        if (a.isDueSoon && b.isDueSoon) return new Date(a.dueAt) - new Date(b.dueAt);
        return 0;
    }});
    let newRiskHtml = '';
    newRiskCards.forEach(c => {{
        newRiskHtml += `<tr class="${{getSwimRowClass(c.swimlane)}}">
            <td>${{c.swimlane}}</td>
            <td>${{cardLink(c.id, c.title)}}</td>
            <td>${{c.dueAtDisplay ? `<strong>${{c.dueAtDisplay}}</strong>` : '-'}}</td>
            <td><span class="badge">${{c.list}}</span></td>
            <td>${{c.members.join(', ') || '無'}}</td>
            <td>${{c.dateLastActivity.split('T')[0] || '-'}}</td>
            <td>${{buildRiskBadges(c)}}</td>
        </tr>`;
    }});
    if (!newRiskHtml) newRiskHtml = '<tr><td colspan="7" style="text-align:center;color:#999">本週目前無新出現的風險卡片</td></tr>';
    const newRiskTbl = document.getElementById('t1-risk-newrisk-table');
    if (newRiskTbl) newRiskTbl.querySelector('tbody').innerHTML = newRiskHtml;

    // 即將到期分頁：使用全看板 RAW.cards（不受篩選器影響），與 KPI 9 對齊
    const dueSoonCards = RAW.cards.filter(c => isRiskCard(c) && c.isDueSoon && !c.archived)
        .sort((a, b) => new Date(a.dueAt) - new Date(b.dueAt));
    let dueSoonHtml = '';
    dueSoonCards.forEach(c => {{
        dueSoonHtml += `<tr class="${{getSwimRowClass(c.swimlane)}}">
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
        newHtml += `<tr class="${{getSwimRowClass(c.swimlane)}}">
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
        doneHtml += `<tr class="${{getSwimRowClass(c.swimlane)}}">
            <td>${{c.swimlane||'—'}}</td>
            <td>${{cardLink(c.id, c.title)}}</td>
            <td>${{c.members.join(', ') || '無'}}</td>
            <td>${{et.toISOString().split('T')[0]}}</td>
        </tr>`;
    }});
    document.getElementById('t1-newdone-done-table').querySelector('tbody').innerHTML = doneHtml;

    // 本週有異動：依欄位分群（Review→Doing→準備中→Waiting→Ready to GO），群組內依 dateLastActivity 由新到舊
    const ACT_EXCLUDE = {ACT_EXCLUDE_JSON};
    const ACT_GROUP_ORDER = {ACT_GROUP_ORDER_JSON};
    const actCards1 = cards.filter(c => {{
        if (!c.dateLastActivity) return false;
        if (ACT_EXCLUDE.includes(c.list)) return false;
        const dt = new Date(c.dateLastActivity);
        return dt >= startDt && dt <= endDt;
    }});
    // 依 list 分群，群組內依 dateLastActivity 由新到舊
    const actByList1 = {{}};
    actCards1.forEach(c => {{
        if (!actByList1[c.list]) actByList1[c.list] = [];
        actByList1[c.list].push(c);
    }});
    Object.values(actByList1).forEach(arr => arr.sort((a, b) => new Date(b.dateLastActivity) - new Date(a.dateLastActivity)));
    let actWrapHtml1 = '';
    if (actCards1.length === 0) {{
        actWrapHtml1 = '<p style="text-align:center;color:#999;padding:16px;">本週無異動卡片</p>';
    }} else {{
        ACT_GROUP_ORDER.forEach(listName => {{
            const gc = actByList1[listName] || [];
            const collapsed = gc.length === 0 ? ' collapsed' : '';
            let rowsHtml = '';
            gc.forEach(c => {{
                rowsHtml += `<tr>
                    <td>${{c.swimlane||'—'}}</td>
                    <td>${{cardLink(c.id,c.title)}}</td>
                    <td><span class="badge">${{c.list}}</span></td>
                    <td>${{c.members.join(', ')||'—'}}</td>
                    <td>${{(c.dateLastActivity||'').slice(0,10)}}</td>
                </tr>`;
            }});
            actWrapHtml1 += `<div class="act-group-card${{collapsed}}">
                <div class="act-group-hdr" onclick="toggleActGroup(this)">
                    <span class="act-group-arrow">▼</span>
                    <span>▌ ${{listName}}（${{gc.length}}）</span>
                </div>
                <div class="act-group-body">
                    <table class="act-group-table">
                        <thead><tr><th>主題</th><th>卡片名稱</th><th>欄位</th><th>負責人</th><th>最後活動日</th></tr></thead>
                        <tbody>${{rowsHtml}}</tbody>
                    </table>
                </div>
            </div>`;
        }});
    }}
    const actWrap1 = document.getElementById('t1-nd-act-wrap');
    if(actWrap1) actWrap1.innerHTML = actWrapHtml1;
}}

function renderDoing1(cards) {{
    // Doing 明細：扁平清單
    const doingCards = cards.filter(c => c.isDoing);
    let doingHtml = '';
    doingCards.forEach(c => {{
        const staleBadge = c.isStale ? `<span class="badge badge-stale">停滯${{c.staleDays}}天</span>` :
                          '<span class="badge" style="background:#e8f5e9;color:#2e7d32;">活躍</span>';
        const dueSoonBadge = c.isDueSoon ? `<span class="badge badge-due-soon">⚡ ${{c.dueAtDisplay}}</span>` : '';
        doingHtml += `<tr class="${{getSwimRowClass(c.swimlane)}}">
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
        allHtml += `<tr class="${{getSwimRowClass(c.swimlane)}}">
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

// 改動 4: renderParentGroups — 遞迴分組排序 + 父任務狀態 Tab 版（Feature C-1 + C-3）
function renderParentGroups(tabName, cards) {{
    const containerId = tabName + '-parent-container';
    const container = document.getElementById(containerId);
    if (!container) return;

    // 建立全域 childrenMap（供 toggleGroup 遞迴使用）
    const childrenMap = {{}};
    cards.forEach(c => {{
        if (c.parentId) {{
            if (!childrenMap[c.parentId]) childrenMap[c.parentId] = [];
            childrenMap[c.parentId].push(c);
        }}
    }});
    currentChildrenMap = childrenMap;

    // 計算某父任務的所有後代數量（遞迴）
    function countDescendants(id) {{
        const kids = childrenMap[id] || [];
        return kids.reduce((sum, c) => sum + 1 + countDescendants(c.id), 0);
    }}
    function countDone(id) {{
        const kids = childrenMap[id] || [];
        return kids.reduce((sum, c) => sum + (c.isDone ? 1 : 0) + countDone(c.id), 0);
    }}

    // 頂層父任務：有子任務且自身無 parentId
    const parentCards = cards.filter(c => c.isParentTask);
    const standaloneCards = cards.filter(c => c.isStandalone);

    if (parentCards.length === 0 && standaloneCards.length === 0) {{
        container.innerHTML = '<p style="color:#999;padding:16px">無資料</p>';
        return;
    }}

    // 依父任務自身欄位分群
    const statusGroups = {{}};
    parentCards.forEach(p => {{
        const key = p.list || '未知';
        if (!statusGroups[key]) statusGroups[key] = [];
        statusGroups[key].push(p);
    }});

    // 決定預設 active tab（優先 Doing，若無則找第一個非 0）
    const hasStandalone = standaloneCards.length > 0;
    const standaloneIdx = CHILD_LIST_ORDER.length; // 獨立卡片 tab 排最後
    let defaultIdx = 0; // CHILD_LIST_ORDER[0] = 'Doing'
    const doingCount = (statusGroups['Doing'] || []).length;
    if (doingCount === 0) {{
        const firstNonZero = CHILD_LIST_ORDER.findIndex(s => (statusGroups[s] || []).length > 0);
        if (firstNonZero >= 0) {{
            defaultIdx = firstNonZero;
        }} else if (hasStandalone) {{
            defaultIdx = standaloneIdx;
        }}
    }}

    // ── Tab Bar ─────────────────────────────────────────────
    let tabBarHtml = `<div class="parent-status-tab-bar" style="display:flex;flex-wrap:wrap;gap:4px;margin-bottom:0;border-bottom:2px solid #e0e0e0;padding-bottom:0">`;

    CHILD_LIST_ORDER.forEach((status, idx) => {{
        const count = (statusGroups[status] || []).length;
        const isDone = (status === 'DONE');
        const isZero = (count === 0);
        const isActive = (idx === defaultIdx);
        let cls = 'sub-tab-btn';
        if (isDone) cls += ' pst-done';
        if (isZero) cls += ' pst-zero';
        if (isActive) cls += ' active';
        const onclickAttr = isZero ? '' : ` onclick="switchParentStatusTab('${{tabName}}',${{idx}})"`;
        tabBarHtml += `<button class="${{cls}}"${{onclickAttr}}>${{status}} (${{count}})</button>`;
    }});

    // 獨立卡片 Tab
    if (hasStandalone) {{
        const isActive = (defaultIdx === standaloneIdx);
        let cls = 'sub-tab-btn' + (isActive ? ' active' : '');
        tabBarHtml += `<button class="${{cls}}" onclick="switchParentStatusTab('${{tabName}}',${{standaloneIdx}})">獨立卡片 (${{standaloneCards.length}})</button>`;
    }}
    tabBarHtml += `</div>`;

    // ── Panels ──────────────────────────────────────────────
    let panelsHtml = '';
    CHILD_LIST_ORDER.forEach((status, idx) => {{
        const isActive = (idx === defaultIdx);
        const groupParents = statusGroups[status] || [];
        panelsHtml += `<div class="parent-status-panel${{isActive ? ' active' : ''}}">`;

        if (groupParents.length === 0) {{
            panelsHtml += `<p style="color:#bbb;padding:12px 4px">此狀態目前無父任務</p>`;
        }} else {{
            groupParents.forEach(p => {{
                const total = countDescendants(p.id);
                if (total === 0) return;
                const done = countDone(p.id);
                const groupKey = tabName + '__' + p.id;
                panelsHtml += `<div class="parent-group">
                    <div class="parent-group-header" onclick="toggleGroup(this,'${{groupKey}}','${{p.id}}')" style="cursor:pointer">
                        <span class="pg-arrow">▶</span>
                        父任務：${{p.title}}（${{total}} 項）[完成率：${{done}}/${{total}}]
                    </div>
                    <div class="parent-group-body" style="display:none"></div>
                </div>`;
            }});
        }}
        panelsHtml += `</div>`;
    }});

    // 獨立卡片 Panel
    if (hasStandalone) {{
        const isActive = (defaultIdx === standaloneIdx);
        const groupKey = tabName + '__standalone';
        parentGroupData[groupKey] = standaloneCards;
        const done = standaloneCards.filter(c => c.isDone).length;
        panelsHtml += `<div class="parent-status-panel${{isActive ? ' active' : ''}}">
            <div class="parent-group">
                <div class="parent-group-header" onclick="toggleGroup(this,'${{groupKey}}',null)" style="cursor:pointer">
                    <span class="pg-arrow">▶</span>
                    獨立卡片（${{standaloneCards.length}} 項）[完成率：${{done}}/${{standaloneCards.length}}]
                </div>
                <div class="parent-group-body" style="display:none"></div>
            </div>
        </div>`;
    }}

    container.innerHTML = tabBarHtml + panelsHtml;
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
        const swimRowCls = getSwimRowClass(swim);
        focusHtml += `<div class="focus-row ${{swimRowCls}}" onclick="toggleFocusRow(this)"><strong>泳道：${{swim}}</strong> (${{total}} 項) [完成率：${{done}}/${{total}}]</div>`;
        focusHtml += `<div class="focus-children ${{swimRowCls}}">`;
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
        newHtml += `<tr class="${{getSwimRowClass(c.swimlane)}}">
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
        doneHtml += `<tr class="${{getSwimRowClass(c.swimlane)}}">
            <td>${{c.swimlane}}</td>
            <td>${{cardLink(c.id, c.title)}}</td>
            <td>${{c.members.join(', ') || '無'}}</td>
            <td>${{et.toISOString().split('T')[0]}}</td>
        </tr>`;
    }});
    document.getElementById('t2-newdone-done-table').querySelector('tbody').innerHTML = doneHtml;

    // 本週有異動：依欄位分群（Review→Doing→準備中→Waiting→Ready to GO），群組內依 dateLastActivity 由新到舊
    const ACT_EXCLUDE2 = {ACT_EXCLUDE_JSON};
    const ACT_GROUP_ORDER2 = {ACT_GROUP_ORDER_JSON};
    const actCards2 = cards.filter(c => {{
        const at = c.dateLastActivity ? new Date(c.dateLastActivity) : null;
        if (!at || at < startDt || at > endDt) return false;
        if (ACT_EXCLUDE2.includes(c.list)) return false;
        const ct = new Date(c.createdAt);
        const isNew = ct >= startDt && ct <= endDt;
        const et = c.endAt ? new Date(c.endAt) : null;
        const isDoneThisWeek = c.isDone && et && et >= startDt && et <= endDt;
        return !isNew && !isDoneThisWeek;
    }});
    // 依 list 分群，群組內依 dateLastActivity 由新到舊
    const actByList2 = {{}};
    actCards2.forEach(c => {{
        if (!actByList2[c.list]) actByList2[c.list] = [];
        actByList2[c.list].push(c);
    }});
    Object.values(actByList2).forEach(arr => arr.sort((a, b) => new Date(b.dateLastActivity) - new Date(a.dateLastActivity)));
    let actWrapHtml2 = '';
    if (actCards2.length === 0) {{
        actWrapHtml2 = '<p style="text-align:center;color:#999;padding:16px;">本週無異動卡片</p>';
    }} else {{
        ACT_GROUP_ORDER2.forEach(listName => {{
            const gc = actByList2[listName] || [];
            const collapsed = gc.length === 0 ? ' collapsed' : '';
            let rowsHtml = '';
            gc.forEach(c => {{
                rowsHtml += `<tr>
                    <td>${{c.swimlane}}</td>
                    <td>${{cardLink(c.id, c.title)}}</td>
                    <td><span class="badge">${{c.list}}</span></td>
                    <td>${{c.members.join(', ') || '無'}}</td>
                    <td>${{c.dateLastActivity.split('T')[0]}}</td>
                </tr>`;
            }});
            actWrapHtml2 += `<div class="act-group-card${{collapsed}}">
                <div class="act-group-hdr" onclick="toggleActGroup(this)">
                    <span class="act-group-arrow">▼</span>
                    <span>▌ ${{listName}}（${{gc.length}}）</span>
                </div>
                <div class="act-group-body">
                    <table class="act-group-table">
                        <thead><tr><th>主題</th><th>卡片名稱</th><th>欄位</th><th>負責人</th><th>最後活動日</th></tr></thead>
                        <tbody>${{rowsHtml}}</tbody>
                    </table>
                </div>
            </div>`;
        }});
    }}
    const actWrap2 = document.getElementById('t2-nd-act-wrap');
    if(actWrap2) actWrap2.innerHTML = actWrapHtml2;
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
        allHtml += `<tr class="${{getSwimRowClass(c.swimlane)}}">
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
