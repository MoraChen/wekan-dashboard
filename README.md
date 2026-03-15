# Wekan Dashboard Generator
### 互動式週報儀表板產生器

> 🇹🇼 [繁體中文](#繁體中文) ｜ 🇺🇸 [English](#english)

---

## 繁體中文

將 Wekan 匯出的 JSON 一鍵轉換為互動式 HTML 週報儀表板，適合週例會與個人追蹤使用。

### 功能特色

- **雙主 Tab 設計**
  - 📊 **總覽 & 風險管理**：KPI 卡片、圖表、風險排序、Doing 明細、本週動態
  - 👤 **個人 & 細項追蹤**：個人泳道分析（選取 1 位成員自動觸發）、全部明細

- **KPI 卡片（8 個）**：本週新增、本週完成、Doing、Waiting、追蹤中、停滯、無負責人、待辦積壓

- **智慧排序**
  - 本週有異動：依最後活動日由新到舊
  - 風險與停滯：逾期 → 停滯（天數遞減）→ 無負責人

- **互動篩選**：日期範圍、流程欄位、主題（Swimlane）、標籤、狀態、封存狀態

- **圖表（4 張）**：流程欄位分布、主題完成率 vs 停滯率、成員工作量、每週完成趨勢

- **效能優化**：Lazy render、分頁（100 筆/頁）、父子結構 lazy expand

- **離線版支援**：`make_offline.py` 產出無需網路的單一 HTML 檔案

### 快速開始

**1. 安裝需求**
```bash
python3 --version  # 需要 Python 3.8+
# 無需額外安裝套件，只使用標準函式庫
```

**2. 建立設定檔**
```bash
cp team_config.example.json team_config.json
```

開啟 `team_config.json`，依序填入：

- **`members`**：Wekan user ID → 顯示名稱對照（如何找 user ID 見下方說明）
- **`board.lists_roles`**：你的看板欄位名稱對應（若欄位名稱與預設值不同才需調整）
- **`board.lists_order`**：圖表 X 軸的欄位顯示順序
- **`board.swimlanes_order`**：主題（Swimlane）顯示順序

> 📌 只要填 `team_config.json`，不需要修改任何程式碼。

**3. 匯出 Wekan 看板**
- 進入 Wekan 看板 → 右上選單 → Export Board → 下載 JSON
- 將 JSON 檔放入 `wekan json/` 資料夾

**4. 產出儀表板**
```bash
python3 update_dashboard.py
# 產出：週報儀表板_YYYYMMDD.html

# 如需離線版（無網路環境使用）：
python3 make_offline.py
# 產出：週報儀表板_YYYYMMDD_離線版.html
```

### 設定檔說明（team_config.json）

| 欄位 | 說明 | 不填時的預設行為 |
|------|------|----------------|
| `members` | user ID → 顯示姓名 | 顯示 Wekan username |
| `board.lists_roles` | 流程欄位角色對應（8 個角色） | 使用英文預設欄位名稱 |
| `board.lists_order` | 圖表 X 軸欄位排序 | 依 Wekan JSON 原始順序 |
| `board.swimlanes_order` | 主題顯示順序 | 依 Wekan JSON 原始順序 |
| `board.default_swim_selections` | 篩選器預設勾選的主題 | 全選 |

**`lists_roles` 的 8 個角色：**

| 角色 | 用途 | 預設對應欄位 |
|------|------|------------|
| `done` | 已完成，計入本週完成 KPI | `DONE` |
| `closed` | 已結束，排除於風險分析 | `Closed` |
| `doing` | 進行中，計入 Doing KPI & Pipeline | `Doing` |
| `waiting` | 等待中，計入 Waiting KPI & Pipeline | `Waiting` |
| `review` | 追蹤中，計入追蹤中 KPI & Pipeline | `Review / User Test` |
| `backlog` | 待辦池，計入待辦積壓 KPI | `Backlog` |
| `ready` | 準備好，計入待辦積壓 KPI | `Ready to GO` |
| `info` | 說明卡片，排除於動態與風險 | `Goal & Project Info` |

> 若你的欄位名稱為中文或不同命名，只需在 `lists_roles` 填入對應的標題即可。

### 資料夾結構

```
wekan-dashboard/
├── update_dashboard.py        # 主要腳本
├── make_offline.py            # 離線版產出腳本
├── team_config.example.json   # 設定範例（可作為填寫參考）
├── team_config.json           # 你的設定檔（請勿上傳至公開平台）
├── wekan json/                # Wekan 匯出 JSON（請勿上傳）
└── 週報儀表板_YYYYMMDD.html   # 產出的儀表板（請勿上傳）
```

### 看板流程欄位

腳本預設支援以下流程欄位順序（透過 `team_config.json` 的 `board.lists_order` 調整，無需修改程式碼）：

```
Goal & Project Info → Backlog → Preparing → Ready to GO →
Doing → Waiting → Review / User Test → DONE → Closed
```

### 停滯定義

卡片在 Pipeline（Doing / Waiting / Review / User Test）中，超過 **14 天**無任何活動（可在腳本中調整 `STALE_DAYS`）。

---

## English

Convert your Wekan board export (JSON) into an interactive HTML weekly dashboard with a single command. Designed for team weekly meetings and personal task tracking.

### Features

- **Dual-Tab Layout**
  - 📊 **Overview & Risk Management**: KPI cards, charts, risk table, Doing details, weekly activity
  - 👤 **Personal & Detail Tracking**: Personal swimlane analysis (triggered by selecting exactly 1 member)

- **8 KPI Cards**: New this week, Completed, Doing, Waiting, In Review, Stale, No Owner, Backlog

- **Smart Sorting**
  - Weekly activity: newest `dateLastActivity` first
  - Risk table: Overdue → Stale (days desc) → No owner

- **Interactive Filters**: Date range, list, swimlane, label, status, archived state

- **4 Charts**: List distribution, swimlane completion vs stale rate, member workload, weekly trend (12 weeks)

- **Performance**: Lazy render, pagination (100 rows/page), lazy expand parent-child tree

- **Offline Support**: `make_offline.py` produces a fully self-contained HTML file

### Quick Start

**1. Requirements**
```bash
python3 --version  # Python 3.8+ required
# No additional packages needed — standard library only
```

**2. Create your config file**
```bash
cp team_config.example.json team_config.json
```

Open `team_config.json` and fill in:

- **`members`**: Wekan user ID → display name mapping (see "How to Find Wekan User IDs" below)
- **`board.lists_roles`**: Your board's list name mappings (only needed if your list names differ from the defaults)
- **`board.lists_order`**: Display order of lists on the chart X-axis
- **`board.swimlanes_order`**: Display order of swimlanes

> 📌 Only `team_config.json` needs to be edited — no code changes required.

**3. Export your Wekan board**
- Go to your Wekan board → Menu (top right) → Export Board → Download JSON
- Place the JSON file inside the `wekan json/` folder

**4. Generate dashboard**
```bash
python3 update_dashboard.py
# Output: 週報儀表板_YYYYMMDD.html

# For offline use (no internet required):
python3 make_offline.py
# Output: 週報儀表板_YYYYMMDD_離線版.html
```

### Configuration Reference (team_config.json)

| Field | Purpose | Default when omitted |
|-------|---------|----------------------|
| `members` | user ID → display name | Shows Wekan username |
| `board.lists_roles` | List role mappings (8 roles) | Built-in English list names |
| `board.lists_order` | Chart X-axis list order | Wekan JSON original order |
| `board.swimlanes_order` | Swimlane display order | Wekan JSON original order |
| `board.default_swim_selections` | Pre-checked swimlanes in filter | All selected |

**The 8 `lists_roles` roles:**

| Role | Purpose | Default list name |
|------|---------|-------------------|
| `done` | Completed cards; counted in "completed this week" KPI | `DONE` |
| `closed` | Archived/ended; excluded from risk analysis | `Closed` |
| `doing` | In progress; counted in Doing KPI & Pipeline | `Doing` |
| `waiting` | Blocked/waiting; counted in Waiting KPI & Pipeline | `Waiting` |
| `review` | Under review; counted in Review KPI & Pipeline | `Review / User Test` |
| `backlog` | Backlog pool; counted in backlog KPI | `Backlog` |
| `ready` | Ready to start; counted in backlog KPI | `Ready to GO` |
| `info` | Reference cards; excluded from activity & risk | `Goal & Project Info` |

> If your board uses different list names (e.g. in another language), just set the matching titles in `lists_roles`.

### Project Structure

```
wekan-dashboard/
├── update_dashboard.py        # Main script
├── make_offline.py            # Offline version generator
├── team_config.example.json   # Config template (use as reference)
├── team_config.json           # Your config file (DO NOT COMMIT)
├── wekan json/                # Wekan JSON exports (DO NOT COMMIT)
└── 週報儀表板_YYYYMMDD.html   # Generated dashboard (DO NOT COMMIT)
```

### Stale Card Definition

A card is considered **stale** if it has been in the Pipeline (Doing / Waiting / Review / User Test) for more than **14 days** without any activity. Configurable via `STALE_DAYS` in the script.

### How to Find Wekan User IDs

User IDs can be found in the exported JSON under the `members` array. Each member object contains an `_id` field — use this as the key in `team_config.json`.

### License

MIT License — feel free to use, modify, and share.

---

*Built with ❤️ for teams using [Wekan](https://wekan.github.io/) open-source kanban.*
