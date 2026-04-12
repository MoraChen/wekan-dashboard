---
name: task-h-gdrive-upload
description: 將最新週報 HTML 與 AI分析結果/ 上傳（補新檔）到 Google Drive。觸發語句：「上傳雲端」「上傳儀表板到雲端」，或由 session-handoff 自動呼叫。
---

# Task H：上傳儀表板到 Google Drive

## [PRECONDITIONS]
如有任何一項不符 → 立即停止，告知使用者缺少什麼。

- [ ] `gdrive_config.txt` 存在（內含目標路徑）
- [ ] `gdrive_config.txt` 指定的磁碟機（通常為 `G:`）可存取
- [ ] 專案資料夾下有至少一個 `週報儀表板_*.html`

## [TRIGGERS]
- 使用者說：「上傳雲端」 / 「上傳儀表板到雲端」
- 由 `session-handoff` 在步驟 5.5 自動呼叫

## [EXECUTION]

1. **讀取目標路徑**
   - Read `gdrive_config.txt`，取第一行為 `DEST`

2. **確認目標可存取**
   - 用 `ls "$DEST"` 確認磁碟機掛載，失敗則停止並告知

3. **複製最新 HTML**
   - Glob `週報儀表板_*.html`，依檔名排序取最後一個（最新）
   - 若目標已有同名檔案 → 覆蓋（同名即同內容，安全覆蓋）
   - 執行：`cp "<最新HTML>" "$DEST/"`

4. **補新 AI 分析結果（只補、不刪）**
   - 列出本機 `AI分析結果/*.md` 的檔名
   - 列出 `$DEST/AI分析結果/*.md` 的檔名（目標若無此資料夾則先建立）
   - 取差集：本機有、目標沒有的 .md → 逐一 `cp`
   - 回報新增了幾個檔案

5. **回報結果**
   ```
   ✅ 已上傳：週報儀表板_YYYYMMDD.html → [DEST]
   📄 AI分析結果：補新 N 個 .md（略過 M 個已存在）
   ```

## [CONSTRAINTS]
- 不刪除目標資料夾中已有的任何檔案
- 不上傳 `ai_data.json`、`wekan json/`、`team_config.json` 等敏感或大型資料
- 磁碟機不可存取時，明確說明原因，不靜默失敗
