#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
wekan_sync.py - Wekan API JSON

usage:
  python3 wekan_sync.py

config: wekan_config.json
"""

import io
import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

# ── Windows UTF-8 終端機設定 ──────────────────────────────────────
if sys.platform == "win32":
    try:
        import ctypes
        ctypes.windll.kernel32.SetConsoleOutputCP(65001)   # 等同 chcp 65001
        ctypes.windll.kernel32.SetConsoleCP(65001)
    except Exception:
        pass
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace", line_buffering=True)
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace", line_buffering=True)
    except Exception:
        pass

def log(msg):
    """輸出訊息（支援中文）"""
    try:
        print(str(msg), flush=True)
    except Exception:
        safe = str(msg).encode("ascii", errors="replace").decode("ascii")
        print(safe, flush=True)

# ── 相依套件檢查 ─────────────────────────────────────────────────
try:
    import requests
except ImportError:
    sys.stdout.write("[ERROR] Missing 'requests' package. Run: pip install requests\n")
    sys.stdout.flush()
    sys.exit(1)

# ── 設定檔路徑 ───────────────────────────────────────────────────
BASE_DIR = Path(__file__).parent
CONFIG_PATH = BASE_DIR / "wekan_config.json"
JSON_DIR = BASE_DIR / "wekan json"

# ── 讀取設定 ─────────────────────────────────────────────────────
if not CONFIG_PATH.exists():
    template = BASE_DIR / "wekan_config.json.template"
    if template.exists():
        log("[ERROR] 找不到 wekan_config.json")
        log("   請複製 wekan_config.json.template -> wekan_config.json 並填入設定")
    else:
        log("[ERROR] 找不到 wekan_config.json，請參考說明建立設定檔")
    sys.exit(1)

with open(CONFIG_PATH, encoding="utf-8") as f:
    cfg = json.load(f)

SERVER_URL = cfg.get("server_url", "").rstrip("/")
BOARD_ID   = cfg.get("board_id", "")
USER_ID    = cfg.get("user_id", "")
API_TOKEN  = cfg.get("api_token", "")

# 驗證必填欄位
missing = [k for k, v in {"server_url": SERVER_URL, "board_id": BOARD_ID,
                           "user_id": USER_ID, "api_token": API_TOKEN}.items() if not v]
if missing:
    log(f"[ERROR] wekan_config.json 缺少必填欄位：{', '.join(missing)}")
    sys.exit(1)

# ── 函式定義 ─────────────────────────────────────────────────────

def download_board() -> Path:
    """從 Wekan API 下載看板 JSON，儲存至 wekan json/ 資料夾"""
    url = f"{SERVER_URL}/api/boards/{BOARD_ID}/export"
    headers = {
        "Authorization": f"Bearer {API_TOKEN}",
        "userId": USER_ID,
        "Content-Type": "application/json",
    }

    log(f"[INFO] 連線至 Wekan：{SERVER_URL}")

    try:
        resp = requests.get(url, headers=headers, timeout=30)
    except requests.exceptions.ConnectionError:
        log(f"[ERROR] 無法連線至 {SERVER_URL}，請確認網路或伺服器狀態")
        sys.exit(1)
    except requests.exceptions.Timeout:
        log("[ERROR] 連線逾時（30 秒），請稍後再試")
        sys.exit(1)

    if resp.status_code == 401:
        log("[ERROR] 認證失敗（401）：請確認 api_token 與 user_id 是否正確")
        sys.exit(1)
    elif resp.status_code == 403:
        log("[ERROR] 權限不足（403）：此帳號無法匯出看板，請確認是否為看板管理員")
        sys.exit(1)
    elif resp.status_code == 404:
        log(f"[ERROR] 找不到看板（404）：board_id '{BOARD_ID}' 可能不正確")
        sys.exit(1)
    elif resp.status_code != 200:
        log(f"[ERROR] API 回應錯誤（{resp.status_code}）：{resp.text[:200]}")
        sys.exit(1)

    try:
        data = resp.json()
    except json.JSONDecodeError:
        log("[ERROR] API 回應不是有效的 JSON，請確認 Wekan 版本是否支援看板匯出 API")
        sys.exit(1)

    # 確認資料夾存在
    JSON_DIR.mkdir(exist_ok=True)

    # 以日期時間命名（確保唯一且可追蹤）
    today_str = datetime.now().strftime("%Y%m%d_%H%M")
    filename = JSON_DIR / f"export-board-{today_str}.json"

    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    size_kb = filename.stat().st_size / 1024
    log(f"[OK] JSON 已儲存：{filename.name}（{size_kb:.0f} KB）")
    return filename


def update_dashboard() -> bool:
    """執行 update_dashboard.py 產出 HTML 儀表板"""
    script = BASE_DIR / "update_dashboard.py"
    if not script.exists():
        log(f"[ERROR] 找不到 update_dashboard.py（{script}）")
        return False

    log("[INFO] 執行 update_dashboard.py 更新儀表板...")
    result = subprocess.run(
        [sys.executable, str(script)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        cwd=str(BASE_DIR),
    )

    if result.stdout:
        log(result.stdout.strip())
    if result.returncode != 0:
        log("[ERROR] update_dashboard.py 執行失敗：")
        if result.stderr:
            log(result.stderr.strip())
        return False

    return True


def cleanup_old_json(keep_days: int = 30):
    """清理 30 天前的 JSON 檔案（避免磁碟累積）"""
    cutoff = datetime.now().timestamp() - keep_days * 86400
    removed = 0
    for f in JSON_DIR.glob("export-board-*.json"):
        if f.stat().st_mtime < cutoff:
            f.unlink()
            removed += 1
    if removed:
        log(f"[INFO] 已清除 {removed} 個 {keep_days} 天前的舊 JSON 檔")


# ── 主程式 ───────────────────────────────────────────────────────

if __name__ == "__main__":
    start = datetime.now()
    log("=" * 50)
    log(f"[START] Wekan 自動同步  {start.strftime('%Y-%m-%d %H:%M:%S')}")
    log("=" * 50)

    # 1. 下載 JSON
    download_board()

    # 2. 更新儀表板
    ok = update_dashboard()

    # 3. 清理舊 JSON
    cleanup_old_json(keep_days=30)

    elapsed = (datetime.now() - start).seconds
    if ok:
        log("=" * 50)
        log(f"[DONE] 完成！耗時 {elapsed} 秒")
        log("=" * 50)
    else:
        log("[WARN] 同步完成但儀表板更新失敗，請檢查 update_dashboard.py")
        sys.exit(1)
