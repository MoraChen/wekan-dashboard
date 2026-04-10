# Wekan Dashboard Generator
### Interactive Weekly Dashboard — System A

> 🇹🇼 繁體中文 ｜ Version 7.9 ｜ 2026-04-05 更新

---

## 專案概覽

將 Wekan 看板 JSON 一鍵轉換為**互動式 HTML 週報儀表板**，供每週例會與個人任務追蹤使用。

> 📌 **早晨簡報系統（System B）是獨立的另一個資料夾**，兩個系統各自連接 Wekan API，互不依賴。

---

## 系統架構（本系統）

```
週例會前（手動或排程）

  wekan_sync.py
    ├─ 呼叫 Wekan API → 下載最新 JSON
    ├─ 執行 update_dashboard.py → 產出 HTML 週報
    └─ 輸出 ai_data.json（供 AI 分析用）

  或直接執行：
  update_dashboard.py → 讀取 wekan json/ 現有 JSON → 產出 HTML
```

---

## 資料夾結構

```
0.進度儀錶板with AI/
├── 核心腳本
│   ├── update_dashboard.py        主要儀表板產生腳本（v7.9）
│   ├── wekan_sync.py              Wekan API 下載 + 更新儀表板
│   └── make_offline.py            離線版產出腳本
│
├── 執行腳本（BAT）
│   ├── wekan_sync_auto.bat        Task Scheduler 用（下載 + 產 HTML）
│   └── run.bat                    開發用快速執行
│
├── 設定檔（請勿上傳 git）
│   ├── wekan_config.json          Wekan API 金鑰與看板 ID
│   ├── team_config.json           成員 ID → 顯示名稱對照
│   └── wekan_config.json.template 設定範本（可上傳）
│
├── 模板
│   └── template/
│       ├── dashboard.html
│       ├── dashboard.css
│       └── dashboard.js
│
├── AI 分析系統
│   ├── ai_prompt_template.md      分析 Prompt 模板（不上 git）
│   ├── ai_request.json            分析請求橋接（不上 git）
│   ├── ai_data.json               Wekan 資料橋接（不上 git）
│   └── AI分析結果/                 分析結果存放
│
├── 記錄與文件
│   ├── Changelog.md               完整開發歷程
│   ├── PLAYBOOK.md                工作流再現指南（不上 git）
│   ├── Task_dashboard_v7.9_SDD.md 系統設計文件
│   ├── Windows工作排程器設定步驟.md Task Scheduler 指南
│   └── wekan column definition.md Wekan JSON 欄位說明
│
├── 歸檔
│   ├── 歷史週報/
│   ├── 歷史SDD/
│   ├── 工具分析/
│   └── 歷史草稿/
│
└── 輸出（不上 git）
    ├── wekan json/                 Wekan 匯出 JSON
    └── 週報儀表板_YYYYMMDD.html    產出的互動式週報
```

---

## 快速開始

### 前置需求

```bash
python3 --version   # 需要 Python 3.8+
pip install requests jinja2
```

### 初次設定

```bash
# 複製設定檔範本
cp wekan_config.json.template wekan_config.json
cp team_config.example.json team_config.json
# 填入 Wekan API 設定與成員對照
```

### 日常執行

```bash
# 下載最新 JSON + 產出 HTML 儀表板
python wekan_sync.py

# 僅用現有 JSON 重新產出（不下載）
python update_dashboard.py

# 產出離線版（無需 CDN）
python make_offline.py
```

---

## 儀表板功能

| 功能 | 說明 |
|------|------|
| **KPI 卡片（8 個）** | 本週新增、完成、Doing、Waiting、追蹤中、停滯、無負責人、待辦積壓 |
| **圖表（4 張）** | 流程欄位分布、主題完成率/停滯率、成員工作量、每週完成趨勢 |
| **AI 分析 Tab** | 整合 Prompt 模板，一鍵產出分析請求，自動讀取結果 |
| **互動篩選** | 日期、欄位、主題、標籤、狀態多維度篩選 |
| **離線版** | `make_offline.py` 產出不依賴 CDN 的單一 HTML |

---

## 安全性與 Git 規範

絕對不上傳：

```
team_config.json        # 含成員 ID
wekan_config.json       # 含 API Token
CLAUDE.md               # 含工作內部資訊
PLAYBOOK.md             # 含內部決策
週報儀表板_*.html        # 含完整看板資料
wekan json/*.json       # 含完整看板 JSON
ai_data.json            # 含卡片描述
ai_request.json         # 含 prompt 內容
prompt.md               # 含對話記錄
```

---

## 版本記錄

詳細見 `Changelog.md`。

| 版本 | 日期 | 主要內容 |
|------|------|---------|
| v7.9 | 2026-03-28 | ai_data.json 架構重構，修復 null byte 與截斷問題 |
| v7.8 | 2026-03-28 | AI 分析結果自動附加 Prompt 版本資訊 |
| v7.1–7.7 | 2026-03-28 | AI Tab 完整流程（Prompt 設定、產生請求、載入結果） |
| Skill 架構 | 2026-03-30 | CLAUDE.md slim 化 + 8 個 AI 原生 SKILL.md |

---

## License

MIT License

---

*Built for [Wekan](https://wekan.github.io/)*
