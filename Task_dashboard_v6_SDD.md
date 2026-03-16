# Task_dashboard_v6_SDD.md
# 週報儀表板 — 規格驅動開發文件（SDD）

> **文件版本**：v6.0
> **建立日期**：2026-03-16
> **取代文件**：Task_dashboard_v5.md（歷史留存）
> **維護原則**：所有新功能必須先在本文件寫完規格並確認，才能開始修改 `update_dashboard.py`

---

## 如何使用本文件（SDD 工作流程）

```
討論需求 → 補充至「五、待實作規格」（狀態：草案）
     ↓
使用者確認設計細節 → 狀態改為「已確認」
     ↓
開始實作 → 狀態改為「開發中」
     ↓
實作完成並驗證 → 狀態改為「已完成」，移至「四、已實作功能規格」
     ↓
更新 Changelog.md 與 CLAUDE.md
```

**規格狀態標記**

| 標記 | 說明 |
|------|------|
| 🔲 草案 | 正在討論中，設計細節未定 |
| ✅ 已確認 | 設計已確認，待開始實作 |
| 🔨 開發中 | 正在修改 update_dashboard.py |
| ✔️ 已完成 | 已實作並驗證，移至第四章 |

---

## 一、系統概述

### 1-1. 目標與定位

| 項目 | 說明 |
|------|------|
| 系統名稱 | 臨資大數據平台＆AI 週報儀表板 |
| 核心用途 | 每週例會風險管控、工作進度快速掌握、主管決策支援 |
| 資料來源 | Wekan 看板匯出 JSON（每週手動更新） |
| 輸出形式 | 單一 HTML 檔案（線上版 + 離線版） |
| 目標使用者 | 主管（週例會總覽）、個人成員（1:1 週會）、其他部門（推廣版） |
| 技術限制 | 純 Python + HTML/JS，無後端，無外部資料庫，不支援即時更新 |

### 1-2. 使用情境

| 情境 | 主要使用者 | 主要功能 |
|------|----------|----------|
| 週例會（30 分鐘） | 主管 | Tab 1：KPI 一覽、風險與停滯、Doing 明細 |
| 1:1 週會 | 個人成員 | Tab 2：個人泳道分析、個人明細 |
| 風險管控 | 主管 | 風險摘要卡（待實作）、即將到期、停滯分析 |
| 在外報告（無網路） | 主管、成員 | 離線版 HTML（make_offline.py 產出） |

---

## 二、架構總覽

### 2-1. 檔案結構

```
0.進度儀錶板with AI/
├── Task_dashboard_v6_SDD.md        ← 本文件（開發唯一依據）
├── Task_dashboard_v5.md             ← 歷史留存
├── update_dashboard.py              ← 唯一可修改的程式碼
├── make_offline.py                  ← 後製轉換（不含業務邏輯，勿修改）
├── team_config.json                 ← 本地個人設定（不上傳 GitHub）
├── team_config.example.json         ← 公開範本（無敏感資料）
├── README.md                        ← 公開說明文件
├── Changelog.md                     ← 開發變更紀錄（不上傳 GitHub）
├── wekan json/
│   └── export-board-*.json          ← Wekan 匯出 JSON（每週放入）
└── 週報儀表板_YYYYMMDD.html         ← 產出的互動儀表板
```

### 2-2. 資料流

```
Wekan JSON
    ↓  Python 解析
card_records (Python list of dict)
    ↓  json.dumps()
RAW (JavaScript Object in HTML)
    ↓  篩選器 + render functions
UI 表格、圖表、KPI 卡片
```

### 2-3. 雙主 Tab 架構

```
┌─────────────────────────────────────────────────────────────────┐
│  Header：看板名稱 · 分析基準日 · 資料來源 · ⚡ 即將到期區間       │
├─────────────────────────────────────────────────────────────────┤
│  [ 📊 總覽 & 風險管理 ]  [ 👤 個人 & 細項追蹤 ]                  │
├─────────────────────────────────────────────────────────────────┤
│  Tab 1：篩選列 → KPI（9張）→ 子分頁（5個）→ 圖表（4張）          │
│  Tab 2：篩選列 → 個人泳道專注分析 → 子分頁（3個）                │
└─────────────────────────────────────────────────────────────────┘
```

---

## 三、資料架構規格

### 3-1. Card Record 欄位定義（Python → JS）

| 欄位名稱 | 型別 | 說明 | 來源 |
|---------|------|------|------|
| `id` | string | Wekan 卡片 `_id` | `c["_id"]` |
| `title` | string | 卡片標題 | `c["title"]` |
| `list` | string | 所在欄位名稱 | `lists_map[listId]` |
| `listId` | string | 所在欄位 ID | `c["listId"]` |
| `swimlane` | string | 所屬主題名稱 | `swimlanes_map[swimlaneId]` |
| `swimlaneId` | string | 所屬主題 ID | `c["swimlaneId"]` |
| `labels` | string[] | 標籤名稱陣列 | `labels_map[labelId]` |
| `members` | string[] | 負責人顯示名稱 | `display_users[memberId]` |
| `createdAt` | ISO string | 建立時間 | `c["createdAt"]` |
| `endAt` | ISO string | 完成時間 | `c["endAt"]` |
| `dueAt` | ISO string | 到期日 | `c["dueAt"]` |
| `dateLastActivity` | ISO string | 最後活動時間 | `c["dateLastActivity"]` |
| `archived` | bool | 是否封存 | `c["archived"]` |
| `isDone` | bool | 是否在 DONE 欄位或已封存 | `listId ∈ DONE_IDS \|\| archived` |
| `isDoing` | bool | 是否在 Doing 欄位 | `listId ∈ DOING_IDS` |
| `isWaiting` | bool | 是否在 Waiting 欄位 | `listId ∈ WAIT_IDS` |
| `isReview` | bool | 是否在 Review 欄位 | `listId ∈ REVIEW_IDS` |
| `inPipeline` | bool | 是否在 Pipeline 中 | `isDoing \|\| isWaiting \|\| isReview` |
| `isOverdue` | bool | 是否逾期 | `due_dt < NOW && !isDone` |
| `isStale` | bool | 是否停滯 | `inPipeline && staleDays > STALE_DAYS(14)` |
| `isDueSoon` | bool | 是否即將到期 | `NOW <= due_dt <= DUE_SOON_END && !isDone` |
| `staleDays` | int \| null | 停滯天數 | `(NOW - dateLastActivity).days` |
| `dueAtDisplay` | string | 到期日顯示（M/D）| `f"{due_dt.month}/{due_dt.day}"` |
| `noMember` | bool | 是否無負責人 | `len(members) == 0` |
| `hasChecklist` | bool | 是否有 Checklist | `clTotal > 0` |
| `clTotal` | int | Checklist 項目總數 | sum from checklists |
| `clDone` | int | Checklist 完成數 | sum from checklistItems |
| `clPct` | int \| null | Checklist 完成率（%） | `round(clDone*100/clTotal)` |
| `parentId` | string | 父任務卡片 ID | `c["parentId"]` |
| `isParentTask` | bool | 是父任務（有子、無父） | `id ∈ child_parent_ids && !parentId` |
| `isChildTask` | bool | 是子任務 | `hasParent` |
| `isStandalone` | bool | 獨立任務 | `!hasChildren && !hasParent` |
| ~~`cardNumber`~~ | — | 已移除（JS 未使用）| — |
| ~~`archivedAt`~~ | — | 已移除（JS 未使用）| — |
| ~~`hasParent`~~ | — | 已移除（`isChildTask` 已涵蓋）| — |
| ~~`hasChildren`~~ | — | 已移除（`isParentTask` 已涵蓋）| — |

### 3-2. team_config.json Schema

```json
{
  "members": {
    "<wekanUserId>": { "fullname": "顯示姓名" }
  },
  "board": {
    "lists_order": ["欄位名稱依流程順序..."],
    "swimlanes_order": ["主題A", "主題B", ...],
    "default_swim_selections": [],
    "lists_roles": {
      "done":    ["DONE"],
      "closed":  ["Closed", "過往卡片", "過往卡片待青"],
      "doing":   ["Doing"],
      "waiting": ["Waiting"],
      "review":  ["Review / 使用者Test"],
      "backlog": ["Backlog"],
      "ready":   ["Ready to GO"],
      "info":    ["Goal＆專案資訊"]
    }
  }
}
```

> **此檔不上傳 GitHub**。其他部門套用時，只需填入自己的欄位名稱，不改程式碼。

### 3-3. 時間常數（Python 端）

| 常數 | 值 | 說明 |
|------|----|------|
| `NOW` | `datetime.now(UTC)` replace to 23:59:59 | 執行當下，作為快照基準 |
| `WEEK_START` | `NOW - 7 days`，replace to 00:00:00 | 本週區間起點 |
| `STALE_DAYS` | `14` | 停滯判斷天數門檻 |
| `DUE_SOON_DAYS` | `7` | 即將到期判斷天數 |
| `DUE_SOON_END` | `NOW + 7 days`，replace to 23:59:59 | 即將到期區間終點 |
| `TODAY_DISPLAY` | `f"{NOW.month}/{NOW.day}"` | 顯示用日期（M/D） |
| `DUE_SOON_END_DISPLAY` | `f"{DUE_SOON_END.month}/{DUE_SOON_END.day}"` | 顯示用到期終點 |

---

## 四、已實作功能規格（v6 基線）

### 4-1. 篩選器

#### Tab 1 篩選器

| 篩選項目 | 元件 | 資料欄位 | 預設值 |
|---------|------|---------|--------|
| 開始/結束日期 | `<input type="date">` | 控制本週動態區間 | 今日往前 7 天 ~ 今日 |
| 流程欄位（多選） | list-picker | `c.list` | 全選 |
| 主題（多選） | swim-picker | `c.swimlane` | `default_swim_selections`（空=全選） |
| 標籤（多選） | label-picker | `c.labels` | 全選 |
| 狀態（多選） | status-picker | isDoing/isWaiting/isStale... | 全選 |
| 封存狀態（多選） | archived-picker | `c.archived` | 僅未封存 |

#### Tab 2 篩選器

| 篩選項目 | 元件 | 特殊行為 |
|---------|------|---------|
| 開始/結束日期 | `<input type="date">` | 個人泳道以 `createdAt` 篩選 |
| 主題（多選） | swim-picker | — |
| 標籤（多選） | label-picker | — |
| 成員（多選） | member-picker | **選恰好 1 位 → 觸發個人泳道專注分析** |
| 狀態（多選） | status-picker | — |
| 封存狀態（多選） | archived-picker | — |
| 任務結構（多選） | tasktype-picker | 父任務/子任務/獨立任務 |

### 4-2. KPI 卡片（9 個）

| # | 名稱 | 定義 | 資料來源 | Tooltip | 特殊行為 |
|---|------|------|---------|---------|---------|
| 1 | 本週新增 | `createdAt` 在篩選區間內 | filteredCards1 | ✅ | — |
| 2 | 本週完成 | `endAt` 在篩選區間內 && `isDone` | filteredCards1 | ✅ | — |
| 3 | Doing 數 | `isDoing = true` | filteredCards1 | — | — |
| 4 | Waiting 數 | `isWaiting = true` | filteredCards1 | — | — |
| 5 | 追蹤中數 | `isReview = true` | filteredCards1 | — | — |
| 6 | 停滯數 | `isStale = true` | filteredCards1 | ✅（停滯定義） | — |
| 7 | 無負責人數 | `noMember = true` | filteredCards1 | — | — |
| 8 | 待辦積壓 | Backlog + Ready to GO 未封存 | filteredCards1 | ✅ | — |
| 9 | ⚡ 即將到期 | `isDueSoon = true && !archived` | **RAW.cards**（全看板） | ✅（日期區間）| 點擊跳至 duesoon 子分頁 |

> ⚠️ **KPI 9 資料來源不一致**：目前 KPI 9 用 `RAW.cards`（全看板），即將到期表格用 `filteredCards1`。這導致數字可能不同。**Feature B-1** 將修正此問題。

### 4-3. Tab 1 子分頁（5 個）

| 子分頁 | 說明 | 預設顯示 |
|--------|------|---------|
| 📅 本週動態 | mini-tab 三切換（新增/完成/有異動） | ✅ 預設顯示 |
| ▶️ Doing 明細 | 扁平清單，isDoing 卡片 | — |
| 🔴 風險與停滯 | 三子分頁（總覽/泳道/即將到期） | — |
| 🌳 父子結構 | 父任務可展開，含泳道篩選 | — |
| 📋 全部明細 | 分頁顯示（每頁 100 筆） | — |

#### 4-3a. 本週動態（mini-tab）

| mini-tab | 判斷欄位 | 排除條件 | 排序 |
|---------|---------|---------|------|
| 本週新增 | `createdAt` ∈ 篩選區間 | 無 | 依主題排序 |
| 本週完成 | `endAt` ∈ 篩選區間 && isDone | 無 | 依主題排序 |
| 本週有異動 | `dateLastActivity` ∈ 篩選區間 | 排除 DONE/Closed/Backlog/Goal＆專案資訊 | **依 dateLastActivity 由新到舊** |

#### 4-3b. Doing 明細

| 欄位 | 說明 |
|------|------|
| 專案 | swimlane 名稱 |
| 卡片名稱 | 含 🔗 hover 連結 |
| 停滯天數 | staleDays |
| 所在欄位 | list badge（badge-doing 樣式） |
| 負責人 | members |
| 最後活動日 | dateLastActivity 日期部分 |
| 狀態 | `⚡ MM/DD`（isDueSoon 時顯示）+ 停滯/活躍 badge |

#### 4-3c. 風險與停滯（3 子分頁）

**資料範圍**：排除 `_risk_exclude`（done + closed + info 角色對應的 List）+ 封存卡片

**排序規則**（共用）：

| 優先級 | 條件 | 次排序 |
|--------|------|--------|
| 0（最高）| isOverdue | — |
| 1 | isDueSoon | dueAt 升冪（由近到遠）|
| 2 | isStale | staleDays 降冪（天數多排前面） |
| 3 | noMember | — |

**風險標記 badge（可多個疊加）**：

| badge | 條件 | 樣式 |
|-------|------|------|
| 逾期 | isOverdue | 紅底 |
| ⚡ MM/DD | isDueSoon | 黃底橘字（badge-due-soon） |
| 停滯 | isStale | 灰底（badge-stale） |
| 無負責 | noMember | 橙底 |

**總覽風險表格欄位**：專案 / 卡片名稱 / **預計完成日** / 停滯天數 / 所在欄位 / 負責人 / 最後活動日 / Checklist進度 / 風險標記

**泳道篩選表格欄位**：同上（加泳道下拉篩選）

**⚡ 即將到期表格欄位**：專案 / 卡片名稱 / **預計完成日**（粗體）/ 所在欄位 / 負責人 / 最後活動日 / 風險標記

> ✔️ **Feature B-1 已完成**：即將到期表格使用 `RAW.cards`（全看板），與 KPI 9 對齊，不受篩選器影響。

#### 4-3d. 父子結構

- 以父任務為群組（可展開/收合）
- 群組標題：`▼ 父任務：{title}（N 項）[完成率：done/total]`
- 預設全部展開（lazy expand on click）
- 獨立卡片群組置底
- Tab 1 頂部有泳道單選下拉篩選

#### 4-3e. 全部明細

- 分頁顯示，每頁 100 筆
- 欄位：專案 / 卡片名稱 / 負責人 / 建立日 / 最後活動日 / 停滯天數 / Checklist / 標籤

### 4-4. Tab 2 子分頁（3 個）

| 子分頁 | 說明 |
|--------|------|
| 📅 本週動態 | 同 Tab 1 mini-tab 三切換設計 |
| 📋 全部明細 | 同 Tab 1 全部明細（依 Tab 2 篩選） |
| 🌳 父子結構 | 同 Tab 1 父子結構（無泳道篩選下拉） |

**個人泳道專注分析**（選恰好 1 位成員觸發）：
- 資料範圍：包含 DONE/Closed，排除 Backlog/Goal＆專案資訊
- 依泳道分組顯示該成員的卡片

### 4-5. 圖表（4 張）

| 圖表 | 類型 | 資料範圍 | 受篩選器 |
|------|------|---------|---------|
| 流程欄位分布 | 長條圖 | 依 filteredCards1，含所有欄位 | ✅ |
| 主題完成率 vs 停滯率 | 雙色柱圖 | **全看板 RAW.cards** | ❌ |
| 成員工作量分布 | 分組柱圖 | 依 filteredCards1 | ✅ |
| 每週完成趨勢（近 12 週）| 折線圖 | **Python 預算，全看板** | ❌ |

### 4-6. List 角色外部化（team_config.json）

8 個角色：`done / closed / doing / waiting / review / backlog / ready / info`

Python 端自動推導 5 組排除清單：

| 變數 | 組成 | 用途 |
|------|------|------|
| `_risk_exclude` | done + closed + info | 風險表格排除 |
| `_act_exclude` | done + closed + backlog + info | 本週有異動排除 |
| `_focus_exclude` | backlog + info | 個人泳道排除 |

### 4-8. 風險摘要卡（Feature A-1，v6.2）

**位置**：`#t1-panel-risk` 頂部，子分頁按鈕上方，三個子分頁共用

**資料來源**：跟篩選器走（`filteredCards1` 篩出的 riskCards）

**顯示邏輯**：

| 條件 | 顯示樣式 |
|------|---------|
| riskCards.length === 0 | 綠色「✅ 目前篩選範圍內無風險卡片」 |
| riskCards.length > 0 | 黃橘色警示卡，含四項數字 + 主題 top2 + 成員 top2 |

**內容格式**：
```
⚠️ 風險摘要（依目前篩選條件）
總計   共 N 個風險卡片（逾期 N0 ｜ 即將到期 N1 ｜ 停滯 N2 ｜ 無負責人 N3）
集中在  主題A（X 張）、主題B（Y 張）
成員   成員A（X 張）、成員B（Y 張）有最多待處理風險
```

**實作函式**：`buildRiskSummary(riskCards)` → 回傳 HTML 字串；在 `updateRiskTables` 開頭呼叫，結果寫入 `#risk-summary-box`

---

### 4-7. 設定外部化總覽

| 設定項目 | 位置 | 說明 |
|---------|------|------|
| 成員顯示姓名 | `team_config.json → members` | userId → fullname |
| 流程欄位排序 | `team_config.json → board.lists_order` | X 軸順序 |
| 主題排序 | `team_config.json → board.swimlanes_order` | 空陣列=依 JSON 原始順序 |
| 篩選器預設勾選 | `team_config.json → board.default_swim_selections` | 空陣列=全選 |
| List 角色對應 | `team_config.json → board.lists_roles` | 8 個角色 |

---

## 五、待實作規格

> 已完成的 Feature 規格已移至第四章對應節次，此章僅保留進行中或待討論的項目。

### ~~Feature B-1：⚡ 即將到期表格全看板化~~ ✔️ 已完成 → 移至 §4-3c

**問題陳述**：
目前 KPI 9（⚡ 即將到期）使用 `RAW.cards`（全看板），但下方即將到期表格使用 `filteredCards1`（受篩選器影響），導致兩者數字可能不一致，造成使用者困惑。

**解決方案**：
將 `risk-subpanel-duesoon` 表格改為使用 `RAW.cards`（全看板），與 KPI 9 對齊。加入視覺說明告知使用者此分頁不受篩選器影響。

**修改範圍**（`update_dashboard.py` 中的 JS 區段）：

```javascript
// 修改前
const dueSoonCards = cards.filter(c => isRiskCard(c) && c.isDueSoon)

// 修改後
const dueSoonCards = RAW.cards.filter(c => isRiskCard(c) && c.isDueSoon && !c.archived)
```

**視覺提示**（在 `risk-subpanel-duesoon` 面板頂部說明文字中補充）：

```html
<!-- 現有文字後面補充 -->
⚡ 即將到期：dueAt 在 {today_display} – {due_soon_end_display} 之間（不受篩選器影響，顯示全看板）
```

**KPI tooltip 更新**：
在 KPI 9 的 `data-tip` 中補充「全看板計算，不受篩選器影響」。

**驗證標準**：
- [ ] KPI 9 數字 = 即將到期表格筆數
- [ ] 切換篩選器後，KPI 9 和表格數字皆不變
- [ ] 面板有清楚的「不受篩選器影響」說明文字

---

### ~~Feature A-1：風險摘要卡~~ ✔️ 已完成 → 移至 §4-8

**問題陳述**：
主管在週例會時需要快速掌握「哪裡最危險、哪個人最需要關注」，目前需要自行閱讀風險表格才能判斷，缺乏高層次的文字摘要。

**設計目標**：
在風險分頁頂部自動產生一段自然語言摘要，讓主管 5 秒內掌握風險全貌。

**版面位置**：
```
🔴 風險與停滯 子分頁
├── [摘要卡] ← 新增於此（三個子分頁按鈕上方）
├── [總覽風險] [泳道篩選] [⚡ 即將到期]
└── 表格內容...
```

**資料範圍**：跟篩選器走（`filteredCards1`），讓主管縮小到特定主題時摘要也同步更新。

**摘要卡內容規格**：

```
⚠️ 風險摘要（依目前篩選條件）

共 {total} 個風險卡片（逾期 {n0} ｜ 即將到期 {n1} ｜ 停滯 {n2} ｜ 無負責人 {n3}）

集中在：{topSwim1}（{cnt1} 張）{若有第2名：、{topSwim2}（{cnt2} 張）}

成員：{member1}（{mcnt1} 張）{若有第2名：、{member2}（{mcnt2} 張）}有最多待處理風險
```

> 若無風險卡片：顯示「✅ 目前篩選範圍內無風險卡片」（綠色）

**JS 計算邏輯**：

```javascript
function buildRiskSummary(riskCards) {
    const total = riskCards.length;
    if (total === 0) return '<div class="risk-summary ok">✅ 目前篩選範圍內無風險卡片</div>';

    const n0 = riskCards.filter(c => c.isOverdue).length;
    const n1 = riskCards.filter(c => c.isDueSoon).length;
    const n2 = riskCards.filter(c => c.isStale).length;
    const n3 = riskCards.filter(c => c.noMember).length;

    // 主題集中度
    const swimCount = {};
    riskCards.forEach(c => { swimCount[c.swimlane] = (swimCount[c.swimlane] || 0) + 1; });
    const topSwims = Object.entries(swimCount).sort((a, b) => b[1] - a[1]).slice(0, 2);

    // 成員集中度
    const memberCount = {};
    riskCards.forEach(c => {
        c.members.forEach(m => { memberCount[m] = (memberCount[m] || 0) + 1; });
    });
    const topMembers = Object.entries(memberCount).sort((a, b) => b[1] - a[1]).slice(0, 2);

    const swimStr = topSwims.map(([s, n]) => `${s}（${n} 張）`).join('、');
    const memberStr = topMembers.length
        ? topMembers.map(([m, n]) => `${m}（${n} 張）`).join('、') + ' 有最多待處理風險'
        : '（所有風險卡片皆有負責人）';

    return `<div class="risk-summary warn">
        <span class="risk-summary-title">⚠️ 風險摘要</span>
        <span>共 <strong>${total}</strong> 個風險卡片（逾期 ${n0} ｜ 即將到期 ${n1} ｜ 停滯 ${n2} ｜ 無負責人 ${n3}）</span>
        ${topSwims.length ? `<span>集中在：${swimStr}</span>` : ''}
        ${topMembers.length ? `<span>成員：${memberStr}</span>` : ''}
    </div>`;
}
```

**CSS 規格**：

```css
.risk-summary {
    padding: 12px 16px;
    border-radius: 8px;
    margin-bottom: 14px;
    display: flex;
    flex-direction: column;
    gap: 4px;
    font-size: 0.9em;
    line-height: 1.6;
}
.risk-summary.warn {
    background: #fff8e1;
    border-left: 4px solid #f9a825;
    color: #5d4037;
}
.risk-summary.ok {
    background: #e8f5e9;
    border-left: 4px solid #43a047;
    color: #2e7d32;
}
.risk-summary-title {
    font-weight: 700;
    font-size: 0.95em;
    margin-bottom: 2px;
}
```

**呼叫位置**（在 `updateRiskTables` 函式中）：

```javascript
// updateRiskTables 函式開頭，riskCards 計算後
const summaryEl = document.getElementById('risk-summary-box');
if (summaryEl) summaryEl.innerHTML = buildRiskSummary(riskCards);
```

**HTML 位置**（在風險子分頁按鈕列上方）：

```html
<div id="risk-summary-box"></div>
<div class="sub-tab-bar">
    <button ... onclick="switchRiskSubTab('overview')">總覽風險</button>
    ...
</div>
```

**驗證標準**：
- [ ] 風險摘要卡出現在子分頁按鈕上方
- [ ] 切換篩選器後，摘要數字自動更新
- [ ] 無風險卡片時顯示綠色「✅ 無風險」
- [ ] 文字格式符合規格（含 N0/N1/N2/N3 明細）
- [ ] 主題集中度顯示 top 2（不足 2 個時只顯示有的）
- [ ] 成員集中度顯示 top 2

---

## 六、設計決策記錄（ADR）

| 決策 | 選擇 | 理由 | 日期 |
|------|------|------|------|
| 時間基準 | Python `datetime.now()` 執行時快照，嵌入 HTML | 歷史 HTML 查閱時仍知道當時基準日 | 2026-03-15 |
| 停滯定義 | Pipeline 中 > 14 天無 `dateLastActivity` | `dueAt` 覆蓋率只有 1%，不適合作主指標 | v4 以前 |
| KPI 9 資料來源 | `RAW.cards`（全看板）| 即將到期屬於全局風險，不應受篩選限制 | 2026-03-16 |
| 風險摘要卡資料範圍 | 跟篩選器（`filteredCards1`）| 主管縮小到特定主題時，摘要也同步聚焦 | 2026-03-16 |
| 即將到期表格資料來源 | 改用 `RAW.cards`（Feature B-1）| 與 KPI 9 對齊，避免數字不一致 | 2026-03-16 |
| 多 badge 疊加 | `buildRiskBadges(c)` 回傳所有適用 badge | 一張卡片可同時逾期＋停滯，需全部顯示 | 2026-03-16 |
| List 角色外部化 | `team_config.json → board.lists_roles` | 讓其他部門無需改程式碼即可套用 | 2026-03-15 |
| Swimlane 外部化 | `team_config.json → board.swimlanes_order` | 組織名稱不應進入公開 GitHub | 2026-03-15 |
| 離線版分離 | `make_offline.py` 為純後製轉換 | 業務邏輯只在 `update_dashboard.py`，維護單一真相來源 | v4 |
| 個人泳道觸發條件 | 選恰好 1 位成員 | 0 位或多位無法「專注」，設計上明確限制 | v4 |

---

## 七、技術規範

### 7-1. Python 端規範

| 規範 | 說明 |
|------|------|
| 時間計算 | 統一使用 `datetime.now(timezone.utc)`，避免本地時區問題 |
| JS 注入 | Python 計算後 `json.dumps()` 再注入 f-string，避免 XSS 和跳脫問題 |
| f-string 跳脫 | JS 的 `{}` 必須寫成 `{{}}` |
| List 角色 | 統一透過 `_ids_for_names(names)` 取得 ID，不hardcode |
| 排除清單 | 由 `_roles` 自動推導，不手動維護 |
| 輸出命名 | `週報儀表板_{TODAY_STR}.html`，舊檔不覆蓋 |

### 7-2. JS 端規範

| 規範 | 說明 |
|------|------|
| 資料來源 | `RAW.cards` = 全看板；`filteredCards1` / `filteredCards2` = 篩選後 |
| 排除清單 | `RISK_EXCLUDE_LISTS`、`ACT_EXCLUDE`、`FOCUS_EXCLUDE` 由 Python 注入為 JSON |
| 圖表 | Chart.js（線上版，from CDN）；MiniChart（離線版，內建） |
| 不受篩選器影響的區塊 | 必須在 UI 加說明文字，避免使用者困惑 |

### 7-3. 修改指引速查

| 需求 | 修改位置 |
|------|----------|
| 停滯閾值 | `STALE_DAYS = 14` |
| 本週區間 | `timedelta(days=7)` |
| 即將到期天數 | `DUE_SOON_DAYS = 7` |
| Wekan 連結 | `WEKAN_CARD_URL_BASE = "..."` |
| 成員顯示姓名 | `team_config.json → members` |
| 流程欄位名稱/排序 | `team_config.json → board.lists_order` |
| 主題名稱/排序 | `team_config.json → board.swimlanes_order` |
| 預設主題勾選 | `team_config.json → board.default_swim_selections` |
| 風險排除 List | `team_config.json → board.lists_roles`（closed/done/info） |
| **不要直接改已產出的 HTML** | 修改 `update_dashboard.py` 後重新執行腳本 |

---

## 八、版本演進紀錄

| 版本 | 日期 | 主要新增 |
|------|------|---------|
| v1 | — | 基礎 KPI + 靜態表格 |
| v2 | — | 篩選器、Tab 1/2 雙主 Tab |
| v3 | — | 圖表（Chart.js）、成員分析 |
| v4 | — | 可展開父子結構、個人泳道、篩選 Chip 列 |
| v5 | 2026-03 | 本週動態三欄、風險排除邏輯、版面重排、父子結構展開式 |
| **v6** | **2026-03-16** | **以下全部新增** |
| | | List 角色外部化（team_config.json）|
| | | Swimlane 排序外部化（team_config.json）|
| | | 即將到期功能：isDueSoon、dueAtDisplay、DUE_SOON_DAYS |
| | | KPI 9（⚡ 即將到期）|
| | | 風險子分頁第三頁（⚡ 即將到期）|
| | | 多 badge 疊加（buildRiskBadges）|
| | | 風險表格新增「預計完成日」欄位 |
| | | 新排序：逾期 → 即將到期 → 停滯 → 無負責人 |
| | | Doing 表格新增 ⚡ badge |
| | | 準備中（新欄位）加入流程 |
| **v6.1** | **2026-03-16** | **Feature B-1**：即將到期表格改全看板（KPI 與表格對齊） |
| **v6.2** | **2026-03-16** | **Feature A-1**：風險摘要卡（逾期/即將到期/停滯/成員集中度）|

---

*文件結束 — 下一步請依第五章待實作規格依序執行 Feature B-1，完成後更新狀態並移至第四章。*
