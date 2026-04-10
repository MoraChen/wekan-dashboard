---
name: task-g-ai-analysis
description: 執行 AI 週報分析。觸發語句：「分析」「請執行 AI 分析」「AI 分析」。讀取 ai_request.json（prompt 模板）與 ai_data.json（完整卡片資料），執行分析，以繁體中文寫出報告至 AI分析結果/ 資料夾。儀表板產生 ai_request.json 後切換到 Cowork 也會觸發。
---

# Task G：AI 週報分析

讀取分析請求與看板資料，執行結構化 AI 分析，產出繁體中文週報。

## [PRECONDITIONS]
如有任何一項不符 → 立即停止，告知使用者指定訊息。

- [ ] `ai_request.json` 存在 → 若不存在：告知「請先在儀表板 AI Tab 點擊『🤖 產生分析請求』」
- [ ] `ai_data.json` 存在 → 若不存在：告知「請先執行 update_dashboard.py 更新資料」
- [ ] `ai_request.json` 中 `ready == true` → 若為 false：靜默停止（已處理過）

## [GATE]
- ⚠️ 若 `ai_data.json.generated_at` 比 `ai_request.json.generated_at` 早超過 2 小時：
  警告「⚠️ ai_data.json 資料可能不是最新，建議先執行 update_dashboard.py」，等使用者確認後繼續

## [TRIGGERS]
使用者說：「分析」 / 「請執行 AI 分析」 / 「AI 分析」

## [EXECUTION]
1. Read `ai_request.json` → 取出：`prompt_template`、`today`、`output_filename`、`output_folder`、`prompt_version_info`
2. Read `ai_data.json` → 取出完整卡片資料
3. 依 REF_FORMAT 規則將卡片資料格式化為 `{{WEKAN_DATA}}` 文字
4. 將 `{{TODAY}}` 替換為今日日期、`{{WEKAN_DATA}}` 替換為格式化文字，組成完整 prompt
5. 以完整 prompt 執行分析，輸出繁體中文報告
6. 依 REF_OUTPUT 模板，將結果寫入 `{output_folder}/{output_filename}`
7. 將 `ai_request.json` 的 `ready` 欄位設為 `false`
8. 告知使用者：「✅ 分析完成，請點儀表板右側『🔄 載入最新』查看結果」

## [REF_FORMAT]
各類卡片格式化規則（只顯示 description_sections 中存在的 key，不存在則略過）：

```
【本週完成 N 張】
主題：XXX
  - 卡片標題（負責人：OOO）
    └ 現況描述：...
    └ 交付物：...
    └ 完成定義：...

【目前風險 N 張】
主題：XXX
  - 卡片標題（停滯14天 / 逾期 / ⚡即將到期：M/D）
    └ 現況描述：...

【Doing 中 N 張】  【Waiting N 張】  【Review N 張】
（同上格式，附帶負責人與停滯狀態）

【本週新增 N 張】
主題：XXX
  - 卡片標題（負責人：OOO，欄位：XXX）
```

`相關連結` key：格式化為 `  連結：label — url` 逐條列出。

## [REF_OUTPUT]
```
# AI 週報分析  YYYY-MM-DD HH:MM
（空一行）
（分析內容）
（空一行，僅在 prompt_version_info 存在時加入以下行）
> **使用 Prompt 版本**：vN · 上次修改：YYYY-MM-DD HH:MM
```

## [CONSTRAINTS]
- `ai_request.json` 與 `ai_data.json` 含看板人名與任務資料，不得上傳 git
- 執行後必須將 `ready` 設為 `false`，避免重複執行
