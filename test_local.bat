@echo off
chcp 65001 >nul 2>&1
echo ============================================
echo   福利吧论坛签到 - 本地测试工具
echo ============================================
echo.

set /p cookie="X_CACHE_KEY=f8271bd0b68fce72273aff8e7ee43c7c; S5r8_2132_saltkey=H545a45g; S5r8_2132_lastvisit=1785511167; S5r8_2132_auth=4bcdqPPIulxgGD4KO3kiW%2F5OxHGulI%2BTCrFEMtuqBQT72hra2Nu1583V2FeG90nVE3fMDUbOG5zhOGDJXyuYSs6Y7Q; S5r8_2132_lastcheckfeed=14501%7C1785514775; S5r8_2132_nofavfid=1; S5r8_2132_atarget=1; S5r8_2132_visitedfid=2; S5r8_2132_smile=1D1; S5r8_2132_ulastactivity=9d90A0%2F%2Fk7RpZUT89YTUwiTS543NDZbaUvPgfy1NnD9eoChEOOAj; server_name_session=1e78fd014e6e38a38e530c1daf08148a; S5r8_2132_st_p=14501%7C1785855283%7C1a959137ea882ce779fd34f0e827e73d; S5r8_2132_viewid=tid_282761; S5r8_2132_sid=L4bAH4; S5r8_2132_lip=119.237.255.102%2C1785856565; S5r8_2132_st_t=14501%7C1785856566%7C4f673efea17ba456c750fe0ef2447581; S5r8_2132_forum_lastvisit=D_2_1785856566; S5r8_2132_sendmail=1; S5r8_2132_checkpm=1; S5r8_2132_lastact=1785856679%09plugin.php%09"

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
