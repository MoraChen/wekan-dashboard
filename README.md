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

**2. 設定成員對照**
```bash
cp team_config.example.json team_config.json
# 編輯 team_config.json，填入你的 Wekan user ID 與顯示名稱
```

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

### 資料夾結構

```
wekan-dashboard/
├── update_dashboard.py        # 主要腳本
├── make_offline.py            # 離線版產出腳本
├── team_config.example.json   # 成員設定範例
├── team_config.json           # 你的成員設定（請勿上傳）
├── wekan json/                # Wekan 匯出 JSON（請勿上傳）
└── 週報儀表板_YYYYMMDD.html   # 產出的儀表板（請勿上傳）
```

### 看板流程欄位

腳本支援以下預設流程欄位順序（可依需求調整 `LIST_ORDER`）：

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

**2. Configure your team**
```bash
cp team_config.example.json team_config.json
# Edit team_config.json with your Wekan user IDs and display names
```

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

### Project Structure

```
wekan-dashboard/
├── update_dashboard.py        # Main script
├── make_offline.py            # Offline version generator
├── team_config.example.json   # Member config template
├── team_config.json           # Your member config (DO NOT COMMIT)
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
