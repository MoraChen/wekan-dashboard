---
name: task-a-update-dashboard
description: 更新週報儀表板。觸發語句：「請更新儀表板」「更新儀表板」「跑一下腳本」。讀取 wekan json/ 最新 JSON，執行 update_dashboard.py，產出 週報儀表板_YYYYMMDD.html。使用者說「明天要報告」或「需要離線版」時，接著觸發 task-e-offline-export。
---

# Task A：更新儀表板

執行 update_dashboard.py，從最新 Wekan JSON 產出互動式週報 HTML。

## [PRECONDITIONS]
如有任何一項不符 → 立即停止，告知使用者缺少什麼。

- [ ] `wekan json/` 資料夾存在且含至少一個 `.json` 檔
- [ ] `update_dashboard.py` 可透過 Glob 找到（路徑每 session 不同）
- [ ] `template/dashboard.html`、`template/dashboard.css`、`template/dashboard.js` 均存在

## [TRIGGERS]
使用者說：「請更新儀表板」 / 「更新儀表板」 / 「跑一下腳本」

## [EXECUTION]
1. Glob 搜尋 `**/update_dashboard.py` 取得正確路徑
2. 執行 `python update_dashboard.py`
3. 確認輸出無錯誤訊息，且出現 `週報儀表板_YYYYMMDD.html`（以當天日期命名）
4. present_files 提供 HTML 連結
5. 執行 session-handoff 的「任務完成通用清單」（Changelog + PLAYBOOK + 狀態更新）

## [CONSTRAINTS]
- 產出 HTML 以當天日期命名，**保留**舊版 HTML，不覆蓋
- 只改 `update_dashboard.py` 或 `template/`，不直接改已產出的 HTML
- 腳本執行結果由 Claude 自行確認，不詢問「要確認嗎？」
