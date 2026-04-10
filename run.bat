@echo off
cd /d "%~dp0"
echo 正在更新儀表板...
py -X utf8 update_dashboard.py
echo.
pause
