---
name: task-d-feature-design
description: 規劃新功能並產出 SDD（軟體設計文件）。觸發語句：「我想規劃新功能」「新增 Tab」「新增資料結構」「我想調整 XX 架構」。禁止跳步：必須依序完成需求討論 → SDD 確認 → 才進入實作。實作已完成但 SDD 未寫時，執行補寫流程（Task D-補）。
---

# Task D：規劃新功能 + SDD

需求討論 → SDD 起草與確認 → 交棒 task-c 實作。SDD 未確認前禁止動程式碼。

## [PRECONDITIONS]
- [ ] 使用者已描述至少一個具體需求（不接受「你覺得可以加什麼？」等開放問題）

## [GATE]
- ⚠️ 若需求描述模糊：每次只問一個問題釐清，不批次問多個問題

## [TRIGGERS]
使用者說：「我想先討論需求」 / 「新增 Tab」 / 「新增資料結構」 / 「我想調整 XX 架構」

## [EXECUTION — 新功能流程（D-主）]
1. 逐一討論需求（每次一個需求，不明確就提問）
2. 彙整需求清單，請使用者確認理解是否正確
3. Glob 找最新 `Task_dashboard_vN_SDD.md`，讀取版本號 N
4. 起草 `Task_dashboard_v(N+1)_SDD.md`（依 REF_SDD_TEMPLATE 結構）
5. 請使用者確認 SDD 內容
6. 使用者確認後：交棒 task-c-modify-feature 執行實作

## [EXECUTION — 補寫流程（D-補）]
觸發時機：實作已完成，但 SDD 尚未建立。

1. Read `Changelog.md` 最新條目，整理本次實作變更清單
2. 以「若在實作前就寫規格，應該寫什麼」角度倒推產出 SDD
3. 在 SDD 頭部標記「✅ 已實作（補寫規格）」
4. 寫入 `Task_dashboard_vX.Y_SDD.md`（版本號與 Changelog 一致）
5. 更新 CLAUDE.md 二、資料夾結構中的 SDD 檔案清單

## [REF_SDD_TEMPLATE]
每份 SDD 必須包含以下五個章節：
1. **背景與問題陳述（Why）**：為什麼要做這個功能？
2. **解決方案架構（What）**：整體設計決策與方案
3. **資料結構 / 函式規格（How）**：新增或修改的具體規格
4. **驗收清單**：確認實作符合規格的逐條核對清單（`[ ]` 格式）
5. **文件頭部版本號與建立日期**

## [CONSTRAINTS]
- 禁止在 SDD 確認前改任何程式碼
- 禁止跳步（需求確認 → SDD 確認 → 實作，三步驟依序執行）
- SDD 檔案不上傳 git（含組織資訊，已由 `.gitignore` wildcard 自動排除）
- 補寫的 SDD 必須在本 session 結束前完成，不得延後
