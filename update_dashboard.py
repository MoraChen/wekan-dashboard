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

import json, os, glob, re
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

# ── 讀取 AI Prompt 模板（ai_prompt_template.md） ─────────
_ai_prompt_path = os.path.join(BASE_DIR, "ai_prompt_template.md")
_DEFAULT_PROMPT = (
    "你是一位週報分析顧問，請根據以下 Wekan 看板資料，以繁體中文產出本週進度分析。\n"
    "分析基準日：{{TODAY}}\n\n{{WEKAN_DATA}}"
)
try:
    with open(_ai_prompt_path, "r", encoding="utf-8") as _pf:
        AI_PROMPT_TEMPLATE = _pf.read()
except FileNotFoundError:
    AI_PROMPT_TEMPLATE = _DEFAULT_PROMPT
    print("⚠️  ai_prompt_template.md 不存在，使用預設 prompt。")
AI_PROMPT_TEMPLATE_JSON = json.dumps(AI_PROMPT_TEMPLATE)

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

# ── 完整描述解析（AI 分析用）────────────────────────────
def parse_description(desc):
    """
    解析 Wekan 卡片 description，提取各段落與連結。
    支援格式：## 標題 / 標題： / **標題：**
    回傳 {"description_raw": str, "description_sections": dict}
    其中 "相關連結" 回傳 [{"label": str, "url": str}, ...] 清單。
    """
    if not desc:
        return {"description_raw": "", "description_sections": {}}

    KNOWN_SECTIONS = ["現況描述", "目標", "任務目的", "交付物", "完成定義", "相關連結"]
    SECTION_ALIASES = {"definition of done": "完成定義", "dod": "完成定義"}

    def normalize_sec(name):
        n = re.sub(r'\*', '', name).strip().rstrip('：: ').strip()
        lower_n = n.lower()
        for alias, canonical in SECTION_ALIASES.items():
            if alias in lower_n:
                return canonical
        for s in KNOWN_SECTIONS:
            if n.startswith(s):
                return s
        return n

    def is_section_header(line):
        s = line.strip()
        # ## 標題 style
        m = re.match(r'^#{1,3}\s+(.+)', s)
        if m:
            return normalize_sec(m.group(1))
        # **標題：** style
        m = re.match(r'^\*\*(.+?)\*\*\s*[：:]?\s*$', s)
        if m:
            cand = normalize_sec(m.group(1))
            if cand in KNOWN_SECTIONS:
                return cand
        # 標題：（行末為冒號，長度限制避免誤判）
        m = re.match(r'^([^-*\[\(（\d]{1,25})[：:]\s*$', s)
        if m:
            return normalize_sec(m.group(1))
        return None

    def extract_links(text):
        links = []
        # Markdown: [label](url)
        for label, url in re.findall(r'\[([^\]]+)\]\((https?://[^\)]+)\)', text):
            links.append({"label": label.strip(), "url": url.strip()})
        cleaned = re.sub(r'\[[^\]]+\]\(https?://[^\)]+\)', '', text)
        # 標籤 URL：label：url 或 label: url
        for m in re.finditer(r'([^\n（(：:]{1,30})[：:]\s*(https?://\S+)', cleaned):
            url = m.group(2).rstrip('.,;)')
            links.append({"label": m.group(1).strip(), "url": url})
        # 裸 URL（去除已抓到的）
        seen_urls = {lk["url"] for lk in links}
        cleaned2 = re.sub(r'[^\n]{0,30}[：:]\s*https?://\S+', '', cleaned)
        for url in re.findall(r'https?://\S+', cleaned2):
            url = url.rstrip('.,;)')
            if url not in seen_urls:
                links.append({"label": url, "url": url})
                seen_urls.add(url)
        return links

    sections = {}
    current_sec = None
    current_lines = []

    def flush():
        nonlocal current_sec, current_lines
        if current_sec is not None and current_lines:
            content = "\n".join(current_lines).strip()
            if content:
                if current_sec == "相關連結":
                    lks = extract_links(content)
                    sections[current_sec] = lks if lks else content
                else:
                    sections[current_sec] = content
        current_sec = None
        current_lines = []

    for line in desc.splitlines():
        header = is_section_header(line)
        if header:
            flush()
            current_sec = header
        elif current_sec is not None:
            current_lines.append(line)
    flush()

    return {"description_raw": desc, "description_sections": sections}

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

# ── 產生 HTML（Jinja2 渲染） ─────────────────────────────────────────────
from jinja2 import Environment, FileSystemLoader

TEMPLATE_DIR = os.path.join(BASE_DIR, "template")
env      = Environment(loader=FileSystemLoader(TEMPLATE_DIR))
template = env.get_template("dashboard.html")

# 讀入 CSS / JS 內容
with open(os.path.join(TEMPLATE_DIR, "dashboard.css"), encoding="utf-8") as _f:
    _css_content = _f.read()
with open(os.path.join(TEMPLATE_DIR, "dashboard.js"), encoding="utf-8") as _f:
    _js_content  = _f.read()

today_str = TODAY_STR

html = template.render(
    # 樣式 / 結構
    css_content          = _css_content,
    js_content           = _js_content,
    # 看板基本資訊
    board_title          = board_title,
    now_str              = now_str,
    json_fname           = json_fname,
    today_display        = today_display,
    due_soon_end_display = due_soon_end_display,
    today_str            = today_str,
    # 主資料
    data_json            = data_json,
    # AI Tab 資料
    ai_new_json          = AI_NEW_JSON,
    ai_done_json         = AI_DONE_JSON,
    ai_risk_json         = AI_RISK_JSON,
    ai_doing_json        = AI_DOING_JSON,
    # 成果亮點
    milestones_json          = MILESTONES_JSON,
    milestone_label_json     = MILESTONE_LABEL_JSON,
    milestone_notes_json     = MILESTONE_NOTES_JSON,
    milestone_notes_dir_json = MILESTONE_NOTES_DIR_JSON,
    # 設定變數
    default_start            = DEFAULT_START,
    default_end              = DEFAULT_END,
    swim_order_json          = SWIM_ORDER_JSON,
    default_swim_sel_json    = DEFAULT_SWIM_SEL_JSON,
    risk_exclude_json        = RISK_EXCLUDE_JSON,
    act_exclude_json         = ACT_EXCLUDE_JSON,
    focus_exclude_json       = FOCUS_EXCLUDE_JSON,
    list_order_json          = LIST_ORDER_JSON,
    ready_names_json         = READY_NAMES_JSON,
    act_group_order_json     = ACT_GROUP_ORDER_JSON,
    ai_save_folder           = AI_SAVE_FOLDER,
    ai_filename_prefix       = AI_FILENAME_PREFIX,
    ai_prompt_template_json  = AI_PROMPT_TEMPLATE_JSON,
    wekan_card_url_base      = WEKAN_CARD_URL_BASE,
    today_display_json       = TODAY_DISPLAY_JSON,
    due_soon_end_json        = DUE_SOON_END_JSON,
)

with open(OUT_FILE, "w", encoding="utf-8") as f:
    f.write(html)
print(f"🎉 儀表板已產生：{os.path.basename(OUT_FILE)}")
print(f"   路徑：{OUT_FILE}")

# ── 產出 ai_data.json（供 Cowork Task G 分析用）────────────────────────────
# 包含完整卡片描述（description_raw + description_sections），Python 直接寫出，
# 不經過瀏覽器，不受 File System Access API buffer 上限限制。

_raw_desc_by_id = {c["_id"]: c.get("description", "") for c in data["cards"]}
_risk_exclude_names = set(_risk_exclude)
_tz_tw = timezone(timedelta(hours=8))

def _ai_card(r, include_desc=True):
    rec = {
        "id":             r["id"],
        "title":          r["title"],
        "swimlane":       r["swimlane"],
        "list":           r["list"],
        "members":        r["members"],
        "stale_days":     r["staleDays"],
        "is_stale":       r["isStale"],
        "is_overdue":     r["isOverdue"],
        "is_due_soon":    r["isDueSoon"],
        "due_at_display": r["dueAtDisplay"],
    }
    if include_desc:
        parsed = parse_description(_raw_desc_by_id.get(r["id"], ""))
        rec["description_raw"]      = parsed["description_raw"]
        rec["description_sections"] = parsed["description_sections"]
    return rec

_done_tw   = [r for r in card_records if r["isDone"] and r["endAt"]
              and parse_dt(r["endAt"]) and parse_dt(r["endAt"]) >= WEEK_START]
_new_tw    = [r for r in card_records if r["createdAt"]
              and parse_dt(r["createdAt"]) and parse_dt(r["createdAt"]) >= WEEK_START
              and not r["archived"]]
_risk_tw   = [r for r in card_records if r["list"] not in _risk_exclude_names
              and not r["archived"] and (r["isStale"] or r["isOverdue"] or r["isDueSoon"])]
_doing_tw  = [r for r in card_records if r["isDoing"]   and not r["archived"]]
_wait_tw   = [r for r in card_records if r["isWaiting"] and not r["archived"]]
_review_tw = [r for r in card_records if r["isReview"]  and not r["archived"]]

_ai_data = {
    "generated_at":      datetime.now(_tz_tw).isoformat(),
    "wekan_json_source": os.path.basename(JSON_PATH),
    "today":             f"{NOW.year}/{NOW.month}/{NOW.day}",
    "stats": {
        "done_this_week": len(_done_tw),
        "new_this_week":  len(_new_tw),
        "risk":           len(_risk_tw),
        "doing":          len(_doing_tw),
        "waiting":        len(_wait_tw),
        "review":         len(_review_tw),
    },
    # 含完整描述
    "done_this_week": [_ai_card(r) for r in _done_tw],
    "risk":           [_ai_card(r) for r in _risk_tw],
    "doing":          [_ai_card(r) for r in _doing_tw],
    "waiting":        [_ai_card(r) for r in _wait_tw],
    "review":         [_ai_card(r) for r in _review_tw],
    # 新增卡片不帶描述（通常尚未填寫）
    "new_this_week":  [_ai_card(r, include_desc=False) for r in _new_tw],
}

AI_DATA_PATH = os.path.join(BASE_DIR, "ai_data.json")
with open(AI_DATA_PATH, "w", encoding="utf-8") as _f:
    json.dump(_ai_data, _f, ensure_ascii=False, indent=2)
print(f"🤖 AI 資料已更新：ai_data.json（{os.path.getsize(AI_DATA_PATH)//1024} KB）")
