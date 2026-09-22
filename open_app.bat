@echo off
chcp 65001 >nul
title شركة اعمار ليبيا - ERP
cd /d "E:\EmarrCoSys"

powershell -NoProfile -Command "try { $c = New-Object Net.Sockets.TcpClient; $c.Connect('127.0.0.1',5000); $c.Close(); exit 0 } catch { exit 1 }"
if errorlevel 1 (
    echo جاري تشغيل الخادم...
    start "" /min cmd /c "C:\windows\py.exe start_server.py"
    powershell -NoProfile -Command "$ok=$false; for($i=0;$i -lt 20;$i++){ try { $c=New-Object Net.Sockets.TcpClient; $c.Connect('127.0.0.1',5000); $c.Close(); $ok=$true; break } catch { Start-Sleep -Milliseconds 500 } }; if(-not $ok){ exit 1 }"
)

start "" "http://127.0.0.1:5000/"
exit /b 0
