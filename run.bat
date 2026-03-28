@echo off
cd /d "%~dp0"
echo 正在更新儀表板...
python update_dashboard.py
echo.
pause
