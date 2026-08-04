@echo off
chcp 65001 >nul 2>&1
echo ============================================
echo   福利吧论坛签到 - 本地测试工具
echo ============================================
echo.

set /p cookie="请粘贴你的 Cookie 字符串: "

echo.
echo 正在执行签到测试...
echo.

set FORUM_COOKIE=%cookie%
set CHECKIN_MODE=checkin
set PUSHPLUS_TOKEN=
set SERVERCHAN_KEY=

python checkin.py

echo.
pause
