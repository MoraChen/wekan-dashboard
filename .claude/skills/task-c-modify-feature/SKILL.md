---
name: task-c-modify-feature
description: 修改儀表板功能（CSS、JS、HTML 結構、資料邏輯）。觸發語句：「新增篩選」「調整圖表」「修改 XX 功能」「顏色改一下」「排版調整」。依修改類型選擇對應 template 檔案，執行 update_dashboard.py 驗收，有功能規格變更時需先有或補寫 SDD。
---

# Task C：修改儀表板功能

修改 template/ 或 update_dashboard.py，產出新版 HTML 供驗收。

## [PRECONDITIONS]
- [ ] 已確認修改類型（CSS / JS / HTML / Python 邏輯），對應到 REF_FILES 中的正確檔案
- [ ] 若影響資料結構或 API 合約 → SDD 需先存在或完成補寫（task-d-feature-design）

## [GATE]
- ⚠️ 若使用者問題描述不完整（只說「有問題」「怪怪的」）：先詢問三點再動工
  - 問題區域：Tab / 元件名稱
  - 預期行為：應該要...
  - 實際行為：現在的結果是...
- ⚠️ 若修改影響 Jinja2 資料注入點：需同時修改 `template/dashboard.html` 與 `update_dashboard.py`

## [TRIGGERS]
使用者說：「新增篩選」 / 「調整圖表」 / 「修改 XX 功能」 / 「顏色改一下」 / 「排版調整」

## [EXECUTION]
1. 依 REF_FILES 對照，選擇正確修改目標
2. 修改對應 template 檔案（不改已產出的 HTML）
3. 執行 `python update_dashboard.py` 確認無錯誤
4. 執行 `node --check template/dashboard.js` 確認 JS 無語法錯誤
5. present_files 提供新版 HTML 連結
6. 說明本次修改了哪個 template 檔的哪個區段，請使用者確認對應功能
7. 使用者確認後：執行 session-handoff 的「任務完成通用清單」（含更新 SDD 驗收清單）
8. 詢問「✅ 文件已更新，可以上 git 了嗎？」並提供 git 指令

## [REF_FILES]
| 修改類型 | 目標檔案 |
|---------|---------|
| CSS 樣式（顏色、排版、元件外觀） | `template/dashboard.css` |
| JS 互動邏輯（函數、篩選、渲染） | `template/dashboard.js` |
| HTML 結構（新增 Tab、調整骨架） | `template/dashboard.html` |
| 新增 Jinja2 資料注入點 | `template/dashboard.html` **＋** `update_dashboard.py` |
| Python 資料處理邏輯 | `update_dashboard.py`（不動 template/） |

## [REF_V7_RULES]
Template v7 架構規範（修改前必讀）：
- `template/dashboard.html` 的 `<script>` 區塊：只放 Jinja2 data injection 的 `const` 宣告（`const RAW`、`const MILESTONES` 等），**不寫任何 `let` 變數**
- 全域 `let` 宣告一律留在 `template/dashboard.js`，否則造成 `SyntaxError: Identifier has already been declared`
- 從 Python f-string 提取 JS 時，三種轉義需同步還原：`{{` → `{`、`}}` → `}`、`\\` → `\`（缺第③步會造成正規表達式 SyntaxError）

## [CONSTRAINTS]
- 不直接改已產出的 `週報儀表板_*.html`
- 小幅 CSS/JS 調整（不影響資料結構）：可直接執行，在 Changelog 記錄即可，不需 SDD
- 影響資料結構或函式介面：必須先有 SDD（否則執行 task-d-feature-design）
- git 指令提供後，直接說「完成後直接說下一個需求即可，不需要回報結果」
