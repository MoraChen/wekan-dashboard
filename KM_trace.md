# KM Trace — 卡點知識庫

> **用途**：記錄每次 session 遭遇的卡點完整歷史，供 Claude 查詢與 Mora 回顧。
> **維護規則**：每次 session-handoff 時，Claude 主動寫入新卡點；CLAUDE.md 的「已知卡點」表只保留 active 卡點，resolved 後移至此處歸檔。

---

## 模式統計

> 每次 session-handoff 後更新，幫助識別高頻卡點類型。

| 標籤 | 次數 | 最近一次 |
|------|------|---------|
| #環境差異 | 4 | 2026-05-01 |
| #前置條件未檢查 | 3 | 2026-04-13 |
| #轉義錯誤 | 2 | 2026-03-28 |
| #全域作用域衝突 | 2 | 2026-03-28 |
| #寫入競爭 | 1 | 2026-05-01 |
| #api_變更 | 1 | 2026-04-10 |
| #filter_不一致 | 1 | 2026-04-11 |
| #資料污染 | 1 | 2026-04-11 |
| #權限白名單 | 1 | 2026-04-11 |
| #buffer_上限 | 1 | 2026-03-28 |
| #tool_失效 | 1 | 2026-04-13 |
| #gdrive | 1 | 2026-04-13 |
| #file_protocol | 1 | 2026-04-13 |

---

## 卡點記錄

---

### [KM-001] Linux 開啟 HTML 後 AI 分析 Tab 無法自動載入

- **日期**：2026-04-13
- **狀態**：active
- **標籤**：#環境差異 #file_protocol
- **現象**：在 Linux 上用 `file://` 直接開啟週報 HTML，AI 分析 Tab 無法自動載入分析結果。
- **根因**：`file://` 協議下瀏覽器封鎖目錄讀取，需使用者手動點「選擇專案資料夾」。
- **嘗試過的方法**：無（首次發現，尚未根本解決）
- **最終解法 / 繞路方式**：手動點「選擇專案資料夾」選取本地 `AI分析結果/` 資料夾。
- **反思**：
  - **盲點來源**：開發與測試都在 Windows 環境，預設 G: 掛載後直接開啟；沒有考慮跨平台（Linux）的 `file://` 行為差異。
  - **下次觸發點**：執行 `task-e-offline-export` 或交付週報 HTML 給非 Windows 使用者之前，主動確認目標環境，並在交付說明附上「需手動選取資料夾」提示。

---

### [KM-002] task-h 在 Google Drive 未掛載時靜默失敗

- **日期**：2026-04-13
- **狀態**：active
- **標籤**：#前置條件未檢查 #gdrive
- **現象**：執行 `task-h-gdrive-upload` 時，若 G: 磁碟機未掛載，skill 無明顯錯誤提示，複製動作直接跳過。
- **根因**：`task-h` SKILL.md 設計時假設 G: 已存在，未加前置存在性檢查。
- **嘗試過的方法**：無（首次發現，尚未在 skill 層修復）
- **最終解法 / 繞路方式**：執行前手動確認 G: 存在；失敗則跳過並在交接筆記記錄「GDrive 未掛載，未上傳」。
- **反思**：
  - **盲點來源**：skill 設計聚焦在「怎麼複製」，沒有回頭問「環境準備好了嗎」；G: 掛載屬於外部依賴，卻被當成內部隱式假設。
  - **下次觸發點**：`task-h` SKILL.md 第一步應加入「確認 G: 磁碟機存在」前置檢查，不存在時輸出明確警告，而非靜默跳過。

---

### [KM-003] dashboard.html 中 `let` 重複宣告導致頁面空白

- **日期**：2026-03-28
- **狀態**：resolved
- **標籤**：#全域作用域衝突
- **現象**：開啟 HTML 後 Console 出現 `SyntaxError: Identifier 'xxx' has already been declared`，頁面空白。
- **根因**：重構時部分 `let` 變數同時存在於 `dashboard.html <script>` 和 `dashboard.js`，兩個 `<script>` 共用全域作用域。
- **嘗試過的方法**：逐一搜尋重複宣告。
- **最終解法**：掃描 `dashboard.html` 所有 `let` 宣告，全部移到 `dashboard.js`；`dashboard.html` 只保留 `const`（Jinja2 資料注入）。已固化為 ADR-002。
- **反思**：
  - **盲點來源**：重構時假設 HTML `<script>` 和外部 JS 是各自獨立的作用域，忘記兩者共用全域；沒有在重構流程中加入「作用域衝突檢查」。
  - **下次觸發點**：任何涉及 `dashboard.html <script>` 區塊的修改，執行前先確認沒有 `let` 宣告；完成後立刻執行 `node --check template/dashboard.js`。

---

### [KM-004] Python f-string `\\` 轉義未還原，JS 正規表達式失效

- **日期**：2026-03-28
- **狀態**：resolved
- **標籤**：#轉義錯誤
- **現象**：儀表板搜尋/篩選功能異常；Console 出現 `SyntaxError` 與正規表達式相關錯誤。
- **根因**：從 Python f-string 提取 JS 時，只做了 `{{` → `{`、`}}` → `}` 的還原，遺漏了 `\\` → `\` 的步驟，導致 `/^https?:\\/\\//` 等正規表達式仍是雙反斜線形式。
- **嘗試過的方法**：逐一手動確認正規表達式。
- **最終解法**：全文搜尋 `\\` 並逐一還原；已固化為 ADR-003（三步還原清單）。
- **反思**：
  - **盲點來源**：`{{` / `}}` 的轉義是直覺可見的（Jinja2 習慣），但 `\\` 的轉義是 Python 字串底層行為，需要刻意記憶；沒有轉義還原的系統性 checklist。
  - **下次觸發點**：任何從 Python f-string 提取 JS 的操作，都必須執行三步還原（`{{→{`、`}}→}`、`\\→\`），完成後執行 `node --check` 驗證。

---

### [KM-005] dashboard.html 出現雙 `</head>`

- **日期**：2026-03-28
- **狀態**：resolved
- **標籤**：#轉義錯誤
- **現象**：HTML 結構不合法，部分瀏覽器渲染異常。
- **根因**：重構時複製貼上疏漏，`</head>` 出現兩次。
- **嘗試過的方法**：直接刪除多餘標籤。
- **最終解法**：刪除多餘的 `</head>`；加入驗收步驟：開啟 DevTools Elements 面板確認 `<head>` 結構。
- **反思**：
  - **盲點來源**：大量複製貼上時沒有逐行審查結構標籤；驗收只看畫面，沒有看 DOM 結構。
  - **下次觸發點**：任何重構 HTML 骨架後，用瀏覽器 Elements 面板或 HTML validator 確認 `<head>` / `<body>` 結構正常，再驗收。

---

### [KM-006] `ai_request.json` 寫入大型欄位時內容截斷

- **日期**：2026-03-28
- **狀態**：resolved（ADR-007 根本修復）
- **標籤**：#buffer_上限 #前置條件未檢查
- **現象**：`ai_request.json` 檔案結尾不完整，JSON 無法正常 parse（`Unterminated string`）。
- **根因**：File System Access API `createWritable()` 對 12–23 KB 的大型 JSON 字串有 buffer 邊界問題；加上 `keepExistingData` 行為，短內容覆蓋長內容時尾端殘留 null bytes。
- **最終解法**：ADR-007 Method B 架構：Python 自動輸出 `ai_data.json`（大型資料），瀏覽器只寫薄層 `ai_request.json`（~2 KB）；`createWritable({ keepExistingData: false })` 修復 null byte 殘留。
- **反思**：
  - **盲點來源**：File System Access API 的文件沒有明確說明 buffer 上限；假設「能寫小檔就能寫大檔」，沒有做 12 KB 以上的邊界測試。
  - **下次觸發點**：任何用 File System Access API 寫入 JSON 的場景，若資料量超過 5 KB，先評估是否改由 Python 端產生，瀏覽器只處理薄層中繼資訊。

---

### [KM-007] Windows 本機執行 `python` 出現 exit code 49，腳本無輸出

- **日期**：2026-04-10
- **狀態**：resolved
- **標籤**：#環境差異 #前置條件未檢查
- **現象**：執行 `python update_dashboard.py` 後立即結束，exit code 49，stdout/stderr 完全無輸出。
- **根因**：Windows 繁中版 PATH 第一順位放了 `WindowsApps\python.exe`（Microsoft Store 虛設程式），未安裝時直接以 exit 49 退出，不執行任何腳本。
- **最終解法**：改用 `py update_dashboard.py`（Python Launcher）；`run.bat` 已改為 `py -X utf8 update_dashboard.py`。
- **反思**：
  - **盲點來源**：在 Linux/Cowork 環境開發，`python` 指令直接對應真實安裝；沒有意識到 Windows 有 Store 虛設程式機制。`exit code 49` 沒有任何輸出，難以直接判斷原因。
  - **下次觸發點**：Windows 環境遇到 exit code 49 且無任何輸出時，第一步先用 `where python` 確認第一順位是否為 WindowsApps；是則改用 `py`。

---

### [KM-008] Windows cp950 終端機執行腳本出現 UnicodeEncodeError

- **日期**：2026-04-10
- **狀態**：resolved
- **標籤**：#環境差異
- **現象**：`UnicodeEncodeError: 'cp950' codec can't encode character '\U0001f4c2'`，腳本在第一個 print 就中止。
- **根因**：台灣版 Windows 終端機預設 code page 為 cp950（Big5），Python stdout 跟著使用 cp950，無法輸出 emoji（U+1F000 以上字元）。
- **最終解法**：執行時加 `-X utf8` 參數；`run.bat` 已更新為 `py -X utf8 update_dashboard.py`。
- **反思**：
  - **盲點來源**：腳本在 Linux/Cowork（UTF-8）環境開發，沒有考慮 Windows 繁中版終端機的 code page 差異；emoji 在開發環境正常，切換環境才爆。
  - **下次觸發點**：Windows 本機執行任何含 emoji `print` 的 Python 腳本，一律使用 `py -X utf8`；新增腳本時優先用文字替代 emoji，或在腳本頂部加 `sys.stdout.reconfigure(encoding='utf-8')`。

---

### [KM-009] Wekan card 連結全部顯示「頁面不存在」

- **日期**：2026-04-10
- **狀態**：resolved
- **標籤**：#api_變更
- **現象**：儀表板中所有卡片連結點開後顯示 Wekan「頁面不存在。」；看板本身可正常載入。
- **根因**：Wekan 更新後，card URL 格式從 `/b/{boardId}/{slug}/c/{cardId}` 改為 `/b/{boardId}/{slug}/{cardId}`（移除 `/c/` 前綴）。`cardLink()` 硬編碼了 `/c/`。
- **最終解法**：修改 `template/dashboard.js` 的 `cardLink()`，移除 `/c/`；URL 規格已寫入 `CLAUDE.md`。
- **反思**：
  - **盲點來源**：Wekan URL 格式被視為穩定不變的常數；系統升級時沒有「連結格式是否變更」的驗收步驟。
  - **下次觸發點**：Wekan 系統升級後，第一次開啟儀表板前先點一個卡片連結確認格式；若全部 404，優先確認 Wekan 實際 URL 格式（在 Wekan 手動開任一卡片，對比瀏覽器 URL）。

---

### [KM-010] 本週新增／完成包含 Goal＆專案資訊 / Backlog 卡片

- **日期**：2026-04-11
- **狀態**：resolved
- **標籤**：#filter_不一致
- **現象**：「本週新增」與「本週完成」Tab 出現應被排除的清單卡片（如「N2、週六輪值資訊」）。
- **根因**：`_focus_exclude` 已用於「有異動」和「焦點成員」篩選，但從未套用到 `_ai_new`、`_ai_done`（Python）以及三個 JS render 函式的 newCards/doneCards filter。
- **最終解法**：Python 端加 `_focus_exclude_set`；JS 端三個 render 函式各加 `!FOCUS_EXCLUDE.includes(c.list)`。
- **反思**：
  - **盲點來源**：`_focus_exclude` 是局部加入的，沒有「全域套用到所有 filter」的意識；新增篩選邏輯時只確認當前修改點，沒有全面掃描同一語意的所有使用點。
  - **下次觸發點**：任何修改 newCards/doneCards 相關 filter 後，確認 Python 端（`_ai_new`/`_ai_done`）與 JS 端（三個 render 函式）均已同步套用；修改 `_focus_exclude` 定義時，全文搜尋所有使用點。

---

### [KM-011] dateLastActivity 批次操作污染，卡片被誤放進錯誤月份

- **日期**：2026-04-11
- **狀態**：resolved（ADR-014）
- **標籤**：#資料污染
- **現象**：指標平台的多張 2025/06 完成的卡片，在月檢視中出現在 2026/03 區段。
- **根因**：2026-03-09 執行批次封存，Wekan 把所有被碰到的卡片 `dateLastActivity` 更新為同一天；腳本以 `dateLastActivity` 作為排序日期回退值，誤判月份。
- **最終解法**：移除 `dateLastActivity` 回退路徑，改用 `createdAt` 作為最後防線（ADR-014）；個別卡片以 `wekan_patches.json` 補丁 `endAt`（ADR-013）。
- **反思**：
  - **盲點來源**：`dateLastActivity` 字義是「最後活動時間」，被誤用為「工作完成時間」；批次操作的副作用（所有被碰的卡片日期被覆蓋）沒有被預見。
  - **下次觸發點**：執行 Wekan 批次操作（批次封存、批次移動）前，確認是否會覆蓋 `dateLastActivity`；任何新增「以日期排序」的邏輯時，禁止使用 `dateLastActivity` 作為工作完成時間依據。

---

### [KM-012] Claude Code 權限白名單攔截，exit code 49 無輸出

- **日期**：2026-04-11
- **狀態**：resolved
- **標籤**：#權限白名單
- **現象**：Claude 執行 `python update_dashboard.py 2>&1` 等 Bash 指令後，exit code 49，完全無輸出。
- **根因**：`.claude/settings.local.json` 的 `permissions.allow` 只接受精確符合的指令模式；指令多帶一個參數（`2>&1`、`-c`）即不符合白名單，被 Claude Code 攔截並回傳 exit code 49。與 KM-007（Store python.exe）是不同原因的相同 exit code。
- **最終解法**：改用白名單中已允許的指令格式（`py -X utf8 update_dashboard.py`）。
- **反思**：
  - **盲點來源**：exit code 49 的第一直覺是 KM-007（Store python.exe），沒有意識到白名單攔截也會產生相同的 exit code + 無輸出；兩個原因的症狀完全相同，需要透過「指令是否精確符合白名單」來區分。
  - **下次觸發點**：遇到 exit code 49 且完全無輸出時，先查 `.claude/settings.local.json` 的 allow 清單，確認指令是否精確符合某一條目；若不符合，調整指令格式而非修改白名單。

---

### [KM-013] 產出 JS 後未立即執行語法驗證，由使用者開 HTML 才發現錯誤

- **日期**：2026-03-28
- **狀態**：resolved
- **標籤**：#全域作用域衝突
- **現象**：Claude 回報 JS 提取完成，但使用者開啟 HTML 後才在 Console 看到 SyntaxError。
- **根因**：驗收步驟只包含 `python update_dashboard.py` 和開啟 HTML，沒有在產出 JS 後立即執行 `node --check`；語法錯誤延遲到使用者驗收才被發現。
- **最終解法**：在驗收流程中加入 `node --check template/dashboard.js`，產出 JS 檔後立即執行。
- **反思**：
  - **盲點來源**：「產出 JS」和「驗證 JS 語法」被視為分離的步驟，且後者被排在使用者驗收階段而非 Claude 自驗階段；沒有把「工具能自動做的驗證」納入 Claude 的完成標準。
  - **下次觸發點**：任何產出或修改 `template/dashboard.js` 的操作完成後，Claude 主動執行 `node --check template/dashboard.js`，有錯誤才通知使用者，不等使用者開 HTML 才發現。

---

### [KM-014] Tailwind CDN 被引入但未實際使用，導致 preview 超時

- **日期**：2026-04-10
- **狀態**：resolved
- **標籤**：#前置條件未檢查
- **現象**：`timeline.html` 初版引入 `<script src="https://cdn.tailwindcss.com">`，但頁面不使用任何 Tailwind class，造成 preview screenshot 超時。
- **根因**：複製 HTML 範本時帶入了 Tailwind CDN 引用，沒有驗證是否實際使用。
- **最終解法**：移除未使用的 CDN；頁面改用原生 CSS。
- **反思**：
  - **盲點來源**：引入 CDN 是習慣性操作（「以防萬一要用」），沒有「引入前先確認是否真的需要」的意識；CDN timeout 的症狀（screenshot 超時）不直覺，不容易聯想到 CDN 是根因。
  - **下次觸發點**：任何 HTML 頁面引入外部 CDN 前，確認至少有一個 class 或 function 會實際使用到；沒有實際使用的 CDN 一律不引入。

---

### [KM-015] preview_screenshot / preview_snapshot 工具失效，QC 無法產生視覺截圖

- **日期**：2026-04-13
- **狀態**：active
- **標籤**：#tool_失效
- **現象**：QC 時 `preview_screenshot` 和 `preview_snapshot` 兩個工具都執行失敗，只能改用 `preview_eval` 讀取 DOM 代替，無法留下視覺截圖證明。
- **根因**：尚未確認（可能是 preview 環境未正確啟動，或工具本身有版本問題）。
- **嘗試過的方法**：改用 `preview_eval` 讀 DOM 作為替代驗收依據。
- **最終解法 / 繞路方式**：以 DOM 讀取結果作為功能驗收，但無視覺截圖。
- **反思**：
  - **盲點來源**：工具失敗後直接改用替代方案（`preview_eval`），沒有深究失敗原因；如果根因是「preview server 未啟動」，重啟後兩個工具可能恢復，但沒有嘗試。
  - **下次觸發點**：`preview_screenshot` 或 `preview_snapshot` 失敗時，先嘗試 `preview_start` 重啟 preview server，確認 server 狀態後再重試工具；若仍失敗才改用 `preview_eval` 作為替代，並在交接筆記標注「QC 無視覺截圖」。

---

### [KM-016] 大型 HTML 寫入過程被中斷，JS 末尾截斷導致 Tab 失效（第二次發生）

- **日期**：2026-05-01
- **狀態**：resolved
- **標籤**：#環境差異 #寫入競爭
- **現象**：`update_dashboard.py` 產出的 HTML 末尾 846 chars 缺失（`clearAllChips2` + `DOMContentLoaded` 入口），造成瀏覽器重新整理後所有 Tab 按鈕無法點擊（事件監聽器從未被綁定）。兩次發生時的截斷大小分別為 846 / 842 chars，不完全相同，但截斷點位置一致（`clearAllChips1` 函式內部）。
- **根因**：HTML 寫入（`f.write(html)`）在 1MB+ 大型檔案的 OS buffer flush 過程中被外部中斷（最可能：OneDrive sync 同時搶鎖、或 `wekan_sync_auto.bat` 觸發的 `update_dashboard.py` subprocess 與使用者手動執行發生競爭）。Python `with open` 的 `__exit__` 呼叫 `close()` 時未完全 flush 即中止，留下截斷版 HTML。Jinja2 渲染本身正常（用真實資料測試確認），`dashboard.js` 無 Jinja2 特殊序列。
- **嘗試過的方法**：
  1. 排查 Jinja2 模板特殊序列（無匹配）
  2. 排查 `data_json` 含 `</script>`（無）
  3. 排查 Windows Task Scheduler（無相關任務）
  4. 用最小資料和真實 prompt template 分別測試 Jinja2 渲染（均正常）
- **最終解法**：
  1. `update_dashboard.py` 頂部加 `sys.stdout.reconfigure(encoding='utf-8', errors='replace')`（防止 emoji print 在 cp950 環境 crash）
  2. HTML 寫入改為原子模式：`tmp_file = OUT_FILE + ".tmp"` → `f.write(html)` → `os.replace(tmp_file, OUT_FILE)`；任何中斷只影響 `.tmp`，不影響正式 HTML
- **反思**：
  - **盲點來源**：第一次發生時，以為是 `python -X utf8` 解決了問題（實際上只是下一次執行時沒有被中斷）；沒有意識到 1MB 大型檔案在 OneDrive 目錄下有寫入競爭風險，也沒有主動加原子寫入防禦。
  - **下次觸發點**：任何在 OneDrive / 雲端同步目錄下寫入 500KB 以上檔案的腳本，一律使用 write-to-tmp + `os.replace()` 原子模式；驗收時確認 HTML 含 `DOMContentLoaded` 字串（`grep -c DOMContentLoaded 週報儀表板_*.html` 應為 1）。
