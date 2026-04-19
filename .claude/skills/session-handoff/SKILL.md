---
name: session-handoff
description: Session 交接與任務完成通用清單。觸發語句：「結束了」「交接筆記」「session 結束」，或任何任務（A/C/D/E/F/G）驗收通過後自動執行。依序更新 Changelog.md、PLAYBOOK.md、prompt.md、CLAUDE.md 當前狀態，必要時執行反思，最後輸出交接筆記。
---

# Session Handoff：任務完成通用清單 + Session 交接

每次任務驗收後（九之一）或 session 結束時（十）執行。所有步驟必須由 Claude 主動執行，不可留待下次 session 補做。

## [PRECONDITIONS]
- [ ] 至少有一個任務已驗收完成

## [TRIGGERS]
- 任務 A / C / D / E / F / G 驗收通過後（自動接續）
- 使用者說：「結束這個 session」 / 「交接筆記」 / 「session 結束」

## [EXECUTION — 任務完成通用清單（每次任務驗收後）]
1. 更新 `Changelog.md`：追加本次條目（依 REF_CHANGELOG 格式）；若不存在則先建立
2. 更新 `PLAYBOOK.md`（符合任一條件才執行）：
   - 新架構決定 → 追加「三、關鍵設計決策」ADR
   - 非顯而易見的 Bug 修復 → 追加「四、踩過的坑」
   - 工作流程或慣例調整 → 追加「二、從零複製的步驟」
3. 更新 SDD（任務 C / D 且有功能規格變更時才執行）：
   - 影響資料結構或函式介面 → 在對應 SDD 追加或修訂章節
   - 新功能且已有對應 SDD → 將驗收清單勾選為 `[x]`
   - 未預先寫 SDD → 執行 task-d-feature-design 補寫流程
4. 更新 CLAUDE.md「當前狀態」區塊：反映本次完成事項、待辦與 git 狀態

## [EXECUTION — Session 交接（session 結束時）]
依序執行，不得跳步：

1. 執行上方「任務完成通用清單」步驟 1–4（若尚未完成）
2. 追加對話記錄到 `prompt.md`（依 REF_PROMPT 步驟）
3. 檢查反思觸發：若本 session 後累計訊息達 50 的倍數 → 追加 `reflection.md`（依 REF_REFLECTION 格式）
   - reflection.md 的焦點是**Mora 與 AI 的溝通品質**（什麼問法有效、什麼造成來回、下次怎麼問更好），不記錄技術卡點（技術卡點寫 KM_trace.md）
4. 更新 CLAUDE.md「當前狀態」（確認已含最新 prompt.md 序號）
4.5 卡點回顧 → 寫入 KM_trace.md（依 REF_KM_TRACE 格式）：
   - 回顧本次 session 遭遇的卡點（工具失敗、流程繞路、驗證無法完成等）
   - 每個卡點追加一條記錄到 `KM_trace.md`，需包含反思的兩個欄位（盲點來源 + 下次觸發點）
   - 更新 KM_trace.md 頂部「模式統計」表（新增標籤或累計次數）
   - 同步更新 CLAUDE.md 的「已知卡點」表：新增 active 卡點、已解決的改為 resolved 並移除
   - 若某卡點的「下次觸發點」指向特定 SKILL.md，在交接筆記的「待確認事項」中標注建議修改
5. 輸出交接筆記（依 REF_HANDOFF_NOTE 格式）
5.5 執行 task-h-gdrive-upload（上傳最新 HTML ＋ 補新 AI分析結果/*.md 到 Google Drive）
6. 詢問是否上 git → 使用者確認後，Claude 直接執行：
   ```
   git add Changelog.md PLAYBOOK.md [其他本次異動的可上傳檔案]
   git commit -m "docs: [本次 session 摘要]"
   git push
   ```
   執行完畢後確認 push 成功，更新交接筆記的 git 狀態勾選

## [REF_CHANGELOG]
```
## vX.X｜YYYY-MM-DD
### 變更內容
- [具體說明]
### 影響檔案
- [檔案名稱]
```

## [REF_PROMPT]
追加對話記錄步驟：
1. Read `prompt.md`，找最後一則訊息的序號 N 與時間戳記 T
2. Glob 找最新 JSONL：`/sessions/*/mnt/.claude/projects/**/*.jsonl`
3. 篩選比時間戳記 T 更新的使用者訊息（排除自動系統訊息）
4. 依日期分組追加，格式：`**N. [YYYY-MM-DD HH:MM]**` 換行 `> [訊息內容]`（台灣時間）；有新日期加 `## YYYY-MM-DD` 標題
5. 更新 prompt.md 第 4 行的總計與時間範圍

## [REF_REFLECTION]
```markdown
---
## 📝 第 N 次反思｜YYYY-MM-DD（第 X～Y 則對話）

### 本期協作摘要
### 本期做得好的地方
### 本期可以改善的地方
### 下期優化重點
```

## [REF_KM_TRACE]
每個卡點新增一個區塊，ID 格式 `KM-NNN`（接續最後一個編號）：
```markdown
### [KM-NNN] 卡點標題

- **日期**：YYYY-MM-DD
- **狀態**：active / resolved
- **標籤**：#標籤1 #標籤2
- **現象**：使用者或 Claude 觀察到的表面問題
- **根因**：導致問題的技術或流程根本原因
- **嘗試過的方法**：
- **最終解法 / 繞路方式**：
- **反思**：
  - **盲點來源**：當初為什麼沒想到？（假設錯誤 / 缺少前置確認 / skill 流程缺口）
  - **下次觸發點**：下次執行到哪個步驟時應主動提醒？（session 開始 / 執行某 skill 前 / 特定條件出現時）
```
標籤參考：`#環境差異` `#前置條件未檢查` `#api_auth` `#file_protocol` `#gdrive` `#wekan` `#skill_設計缺口`

## [REF_HANDOFF_NOTE]
```
## 📋 Session 交接筆記｜YYYY-MM-DD HH:MM

### ✅ 本次完成
### 🔜 下次繼續
### ⚠️ 待確認事項
### 📁 本次異動的檔案
### 🔢 git 狀態
- [ ] 已更新 Changelog.md
- [ ] 已更新 PLAYBOOK.md
- [ ] 已更新 prompt.md（最後一則：#N）
- [ ] 已建立 / 更新 SDD（若有功能規格變更）
- [ ] 已上 git（commit message：`vX.X: ...`）
```

## [REF_OUTPUT_FORMAT]
任務完成回報格式（任務驗收時使用）：
```
✅ 完成：[簡述]
📁 產出：[檔案名稱 + 連結]
🔜 下一步建議：[待辦]
💬 需要你決定的事：[若有，否則省略]
```

## [CONSTRAINTS]
- prompt.md 追加步驟**必須由 Claude 主動執行**，不可留待下次 session
- 所有文件更新步驟必須實際執行完畢再往下，不可只提醒使用者去做
- **Claude Code 本機模式**：git 由 Claude 直接執行，不提供指令給使用者手動操作
- 不可逆操作（刪除、大量改寫）仍需先向使用者明確確認
