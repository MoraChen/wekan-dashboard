---
name: task-b-full-analysis
description: 執行完整六步驟看板分析並產出報告。觸發語句：「重新做完整分析」。讀取 Task_dashboard_v6_SDD.md 的分析框架，對 wekan json/ 最新資料進行六步驟深度分析，產出繁體中文 Markdown 報告。
---

# Task B：完整看板分析

對最新 Wekan 資料執行六步驟系統性分析，產出可供週例會使用的完整報告。

## [PRECONDITIONS]
如有任何一項不符 → 立即停止，告知使用者。

- [ ] `wekan json/` 含最新 `.json` 檔
- [ ] `Task_dashboard_v6_SDD.md` 存在（含分析框架定義）

## [TRIGGERS]
使用者說：「重新做完整分析」

## [EXECUTION]
1. Read `Task_dashboard_v6_SDD.md` → 取得六步驟分析框架與 KPI 定義
2. Read `wekan json/` 最新 JSON 檔（Glob 找最新日期）
3. 依框架執行六步驟分析：
   - Step 1：整體看板健康度（Pipeline 分布、停滯率）
   - Step 2：本週完成與新增（趨勢對比）
   - Step 3：風險卡片清單（逾期、停滯、即將到期）
   - Step 4：主題（Swimlane）進度摘要
   - Step 5：里程碑狀態
   - Step 6：建議優先行動項目
4. 產出報告檔 `完整分析_YYYYMMDD.md`，儲存至專案根目錄
5. present_files 提供報告連結
6. 執行 session-handoff 的「任務完成通用清單」

## [REF_TERMS]
使用統一術語（見 CONSTRAINTS）：主題 / 里程碑 / Pipeline / 停滯 / 即將到期

## [CONSTRAINTS]
- 術語對照：主題＝Swimlane、里程碑＝貼「里程碑」標籤的卡片、Pipeline＝Doing+Waiting+Review
- 停滯定義：Pipeline 中超過 14 天無 `dateLastActivity` 更新
- 即將到期定義：`dueAt` 在今天起 7 天內（排除 DONE/Closed）
- `dueAt` 覆蓋率極低（約 1%），不以此作為逾期主指標
- 分析報告不上傳 git（含組織資訊）
