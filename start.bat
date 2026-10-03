@echo off
setlocal
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

where npm >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Khong tim thay npm trong PATH.
    pause
    exit /b 1
)

echo [1/3] Compile backend...
if not exist "backend\bin" mkdir "backend\bin"
javac -encoding UTF-8 -d "backend\bin" "backend\UdpChatServer.java"
if errorlevel 1 (
    echo [ERROR] Compile backend that bai.
    pause
    exit /b 1
)

echo [2/3] Build frontend...
call npm --prefix "frontend" run build
if errorlevel 1 (
    echo [ERROR] Build frontend that bai.
    pause
    exit /b 1
)

echo [3/3] Khoi dong backend + frontend...
start "UDP Multicast - Backend" cmd /k "cd /d ""%~dp0"" && java -cp ""backend\bin"" UdpChatServer"
start "UDP Multicast - Frontend" cmd /k "cd /d ""%~dp0frontend"" && npm run dev"

echo.
echo Backend:  http://localhost:8081
echo Frontend: http://localhost:5173
echo.
echo Ung dung da duoc khoi dong.
timeout /t 3 >nul
endlocal
