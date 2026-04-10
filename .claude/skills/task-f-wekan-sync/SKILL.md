---
name: task-f-wekan-sync
description: 從 Wekan API 自動下載最新 JSON 並更新儀表板。觸發語句：「請同步最新資料」「從 Wekan 下載」「API 同步」。執行 wekan_sync.py，自動完成 API 下載 → 存 JSON → 更新儀表板 → 產出 HTML 全流程。
---

# Task F：Wekan API 自動同步

一鍵從 Wekan API 拉取最新資料，產出更新後的週報 HTML。

## [PRECONDITIONS]
如有任何一項不符 → 立即停止，告知使用者。

- [ ] `wekan_config.json` 存在（不得顯示其內容）
- [ ] `wekan_config.json` 中 API Token 欄位非空白（可 JSON parse 驗證 key 存在）
- [ ] `wekan_sync.py` 可透過 Glob 找到

## [GATE]
- ⚠️ 若 `wekan_config.json` 不存在：告知「請複製 wekan_config.json.template，填入 API Token 後重試」，不引導使用者開啟 template 以外的設定內容

## [TRIGGERS]
使用者說：「請同步最新資料」 / 「從 Wekan 下載」 / 「API 同步」

## [EXECUTION]
1. Glob 搜尋 `**/wekan_sync.py` 取得正確路徑
2. 執行 `python wekan_sync.py`
3. 確認輸出含 `[DONE]` 字樣（腳本自動完成 JSON 下載 + update_dashboard.py）
4. 確認 `週報儀表板_YYYYMMDD.html` 已產出
5. present_files 提供 HTML 連結
6. 執行 session-handoff 的「任務完成通用清單」

## [CONSTRAINTS]
- `wekan_config.json` 含 API Token，不得顯示、複製或上傳 git
- 若同步失敗，回報錯誤訊息原文，不猜測 Token 內容
