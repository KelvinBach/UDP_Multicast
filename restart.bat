@echo off
setlocal
cd /d "%~dp0"

echo ==========================================
echo      UDP Multicast - RESTART
echo ==========================================
echo.

echo [1/4] Dang dung backend...
powershell -NoProfile -ExecutionPolicy Bypass -Command "$p=Get-CimInstance Win32_Process -Filter \"name='java.exe'\" | Where-Object { $_.CommandLine -like '*UdpChatServer*' }; if ($p) { $p | ForEach-Object { Stop-Process -Id $_.ProcessId -Force } }"
timeout /t 1 /nobreak >nul

echo [2/4] Compile backend...
if not exist "backend\bin" mkdir "backend\bin"
javac -encoding UTF-8 -d "backend\bin" "backend\UdpChatServer.java"
if errorlevel 1 (
    echo.
    echo [ERROR] Compile backend that bai.
    pause
    exit /b 1
)

echo [3/4] Build frontend...
call npm --prefix "frontend" run build
if errorlevel 1 (
    echo.
    echo [ERROR] Build frontend that bai.
    pause
    exit /b 1
)

echo [4/4] Khoi dong lai...
start "UDP Chat Backend" cmd /k "cd /d ""%~dp0"" && java -cp ""backend\bin"" UdpChatServer"
timeout /t 1 /nobreak >nul
start "UDP Chat Frontend" cmd /k "cd /d ""%~dp0frontend"" && npm run dev"

echo.
echo ==========================================
echo Restart hoan tat.
echo Backend : http://localhost:8081
echo Frontend: http://localhost:5173
echo UDP     : port 5000
echo ==========================================
endlocal
