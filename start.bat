@echo off
setlocal EnableExtensions
cd /d "%~dp0"

echo ==========================================
echo       UDP MULTICAST CHAT - START
echo ==========================================
echo.

where java >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Khong tim thay Java trong PATH.
    pause
    exit /b 1
)
where javac >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Khong tim thay javac trong PATH.
    pause
    exit /b 1
)
where npm >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Khong tim thay npm trong PATH.
    pause
    exit /b 1
)

echo [1/4] Kiem tra backend dang chay...
powershell -NoProfile -ExecutionPolicy Bypass -Command "$p=Get-CimInstance Win32_Process -Filter \"name='java.exe'\" | Where-Object { $_.CommandLine -like '*UdpChatServer*' }; if ($p) { exit 1 }"
if errorlevel 1 (
    echo [INFO] Backend dang chay. Hay dung restart.bat neu muon build lai.
    pause
    exit /b 0
)

echo [2/4] Compile backend...
if not exist "backend\bin" mkdir "backend\bin"
javac -encoding UTF-8 -d "backend\bin" "backend\UdpChatServer.java"
if errorlevel 1 (
    echo [ERROR] Compile backend that bai.
    pause
    exit /b 1
)

echo [3/4] Build frontend...
call npm --prefix "frontend" run build
if errorlevel 1 (
    echo [ERROR] Build frontend that bai.
    pause
    exit /b 1
)

echo [4/4] Khoi dong backend + frontend...
start "UDP Multicast - Backend" cmd /k "cd /d ""%~dp0"" && java -cp ""backend\bin"" UdpChatServer"
timeout /t 1 /nobreak >nul
start "UDP Multicast - Frontend" cmd /k "cd /d ""%~dp0frontend"" && npm run dev -- --host 0.0.0.0"

echo.
echo ==========================================
echo Ung dung da duoc khoi dong.
echo Backend : http://localhost:8081
echo Frontend: http://localhost:5173
echo UDP     : port 5000
echo ==========================================
endlocal
