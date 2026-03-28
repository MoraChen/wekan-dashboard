#!/bin/bash
cd "$(dirname "$0")"
echo "正在更新儀表板..."
python3 update_dashboard.py
