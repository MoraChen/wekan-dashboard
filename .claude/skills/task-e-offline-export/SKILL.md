---
name: task-e-offline-export
description: 產出完全離線版週報 HTML。觸發語句：「產出離線版」「明天要報告」「需要離線版」。必須先完成 task-a-update-dashboard，再執行 make_offline.py，產出 週報儀表板_YYYYMMDD_離線版.html。
---

# Task E：產出離線版儀表板

在線上版基礎上，產出完全內嵌資源的離線 HTML，可在無網路環境使用。

## [PRECONDITIONS]
如有任何一項不符 → 立即停止，告知使用者。

- [ ] 今日的線上版 `週報儀表板_YYYYMMDD.html` 已存在（先執行 Task A）
- [ ] `make_offline.py` 可透過 Glob 找到

## [TRIGGERS]
使用者說：「產出離線版」 / 「明天要報告」 / 「需要離線版」

## [EXECUTION]
1. 確認今日線上版 HTML 存在；若不存在，先執行 task-a-update-dashboard 全部步驟
2. Glob 搜尋 `**/make_offline.py` 取得正確路徑
3. 執行 `python make_offline.py`
4. 確認產出 `週報儀表板_YYYYMMDD_離線版.html`
5. present_files 提供離線版 HTML 連結
6. 執行 session-handoff 的「任務完成通用清單」

## [CONSTRAINTS]
- 修改功能只改 `update_dashboard.py`，不改 `make_offline.py`
- 離線版 HTML 不上傳 git
