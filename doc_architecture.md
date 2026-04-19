# 文件架構說明

> **用途**：記錄本專案所有文件的職責、讀者、更新頻率與相互關係，供 Mora 回顧與 Claude 理解文件生態。
> **維護規則**：新增或移除文件時同步更新此檔；各文件職責有實質變化時亦需更新。
> 最後更新：2026-04-19

---

## 一、操作指引層（Claude 執行時讀取）

| 檔案 | 主要讀者 | 更新頻率 | 職責 | 關鍵關係 |
|------|---------|---------|------|---------|
| `~/.claude/CLAUDE.md`（global） | Claude（跨所有專案） | 偶爾 | 跨專案行為規範、語言偏好、回應風格 | 上位規則，project CLAUDE.md 不得複製其內容 |
| `CLAUDE.md`（project） | Claude（session 開始時） | 每次 session 結束 | 當前狀態、已知卡點快查表、Skill 觸發索引、絕對禁止 | 卡點快查指向 KM_trace；skill 觸發索引指向各 SKILL.md |
| `.claude/skills/session-handoff/SKILL.md` | Claude（任務完成後） | 流程有變動時 | session 結束的完整執行腳本（更新文件、寫 KM、git） | 驅動所有文件的更新：Changelog、PLAYBOOK、KM_trace、CLAUDE.md |
| `.claude/skills/task-*/SKILL.md`（8 個） | Claude（任務觸發時） | 功能有變動時 | 各任務的 TRIGGERS / PRECONDITIONS / EXECUTION / CONSTRAINTS | 由 CLAUDE.md 觸發索引指向；執行結果觸發 session-handoff |

---

## 二、知識沉澱層（人與 AI 共同閱讀）

| 檔案 | 主要讀者 | 更新頻率 | 職責 | 關鍵關係 |
|------|---------|---------|------|---------|
| `KM_trace.md` | Claude（查觸發點）+ Mora（回顧反思） | 每次 session-handoff | 完整卡點歷史：症狀、根因、盲點來源、下次觸發點、模式統計 | 原始記錄層；PLAYBOOK 踩過的坑從此萃取；CLAUDE.md 卡點表是其 active 子集 |
| `PLAYBOOK.md` | Mora（複製到新專案時） | 有新卡點或架構決策時 | 跨專案可攜的工作流食譜：核心邏輯、ADR、踩坑原則（精簡版，指向 KM 編號） | 依賴 KM_trace 作為原始細節來源；ADR 是設計決策的長期存檔 |
| `reflection.md` | Mora（定期回顧） | 每 50 則對話累計 | 以 prompt.md 對話記錄為素材，回顧 Mora 與 AI 的溝通品質：什麼問法有效、什麼造成來回、下次怎麼問更好。是 Mora 個人的 AI 溝通能力精進日誌，**不記錄技術卡點** | 觸發點在 session-handoff 步驟 3；技術卡點另寫 KM_trace |
| `~/.claude/memory/*.md` | Claude（跨 session 記憶） | 學到新事實或獲得 feedback 時 | 使用者偏好、feedback、專案背景、外部資源指引 | 跨 session 持久記憶；與 CLAUDE.md 不重複（CLAUDE.md 放專案即時狀態，memory 放通用偏好） |

---

## 三、歷史記錄層（版本追溯用）

| 檔案 | 主要讀者 | 更新頻率 | 職責 | 關鍵關係 |
|------|---------|---------|------|---------|
| `Changelog.md` | Mora（版本追蹤） | 每次任務驗收後 | 版本號、變更摘要、影響檔案 | session-handoff 步驟 1 自動追加 |
| `prompt.md` | Mora（對話脈絡回溯） | 每次 session 結束 | 完整對話記錄（序號 + 時間戳） | session-handoff 步驟 2 追加；累計達 50 則倍數觸發 reflection.md |

---

## 四、設計規格層（功能實作的依據）

| 檔案 | 主要讀者 | 更新頻率 | 職責 | 關鍵關係 |
|------|---------|---------|------|---------|
| `Task_dashboard_v7.9_SDD.md`（當前） | Claude + Mora | 功能規格變更時 | 功能設計決策、資料結構、驗收清單 | 實作前必須存在（SDD-first 原則）；任務 C/D 完成後同步更新 |
| `歷史SDD/`（封存） | Mora（回溯設計演進） | 不再更新 | 歷代版本的設計記錄 | 參考用，不影響當前執行 |

---

## 五、設定與資料層

| 檔案 | 主要讀者 | 更新頻率 | 職責 | 關鍵關係 |
|------|---------|---------|------|---------|
| `team_config.json` | Python 腳本 | 成員或看板異動時 | 成員 ID、看板設定、篩選規則 | 絕對不上 git；`update_dashboard.py` 讀取 |
| `wekan_config.json` | Python 腳本 | API Token 更換時 | Wekan API 認證資訊 | 絕對不上 git；`wekan_sync.py` 讀取 |
| `wekan_patches.json` | Python 腳本 | 需要補丁日期時 | 個別卡片的 `endAt`/`startAt` 補丁 | 解決 Wekan 封存卡片日期污染問題（KM-011） |
| `ai_prompt_meta.json` | Python 腳本 | Prompt 版本更新時 | Prompt 版本號、修改時間、歷史清單 | 配合 `AI prompt/` 資料夾追蹤分析品質演進 |

---

## 六、整體資訊流向

```
Wekan API / JSON
      ↓
update_dashboard.py（讀 team_config + wekan_patches）
      ↓
週報儀表板_*.html ← 產出
      ↓（任務完成）
session-handoff
  ├─→ Changelog.md       （版本記錄）
  ├─→ PLAYBOOK.md        （原則精華）
  ├─→ KM_trace.md        （卡點全史）
  ├─→ CLAUDE.md          （即時狀態）
  ├─→ prompt.md          （對話記錄）
  └─→ reflection.md      （每 50 則，AI 溝通品質反思）
```

---

## 七、容易混淆的邊界

| 容易混淆的兩個檔案 | 區別 |
|-----------------|------|
| `CLAUDE.md 已知卡點` vs `KM_trace.md` | 前者是 active 子集（Claude session 快查用），後者是完整歷史（含 resolved + 反思） |
| `PLAYBOOK.md 踩過的坑` vs `KM_trace.md` | 前者是跨專案可攜的原則萃取（精簡），後者是本專案的原始完整記錄 |
| `reflection.md` vs `KM_trace.md` | 前者是 AI 溝通品質的週期覆盤（人的視角），後者是技術與流程卡點的事件追蹤（執行視角） |
| `CLAUDE.md`（project） vs `~/.claude/CLAUDE.md`（global） | 前者放專案即時狀態與特有規則，後者放跨專案通用偏好；兩者絕對不能混寫 |
