@echo off
chcp 65001 >nul
title Smart Pill Box - One Click Launcher
echo =======================================================================
echo          KHỞI ĐỘNG HỆ THỐNG SMART PILL BOX TOÀN DIỆN
echo =======================================================================

echo [1/3] Đang khởi động Backend API tại http://localhost:8000 ...
start "Smart Pill Box - Backend API (Port 8000)" cmd /k "cd /d %~dp0backend && .venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000"

timeout /t 2 >nul

echo [2/3] Đang khởi động Web Simulator tại http://localhost:5173 ...
start "Smart Pill Box - Web Simulator (Port 5173)" cmd /k "cd /d %~dp0web-simulator && npm run dev"

timeout /t 2 >nul

echo [3/3] Đang khởi động Flutter Web App tại http://localhost:8080 ...
start "Smart Pill Box - Flutter Web (Port 8080)" cmd /k "cd /d %~dp0flutter-app && flutter run -d web-server --web-port 8080 --web-hostname 127.0.0.1"

echo.
echo =======================================================================
echo    CẢ 3 DỊCH VỤ ĐÃ ĐƯỢC MỞ TRONG 3 CỬA SỔ RIÊNG BIỆT:
echo    - Backend API Swagger Docs : http://localhost:8000/docs
echo    - Web Simulator (Hộp thuốc): http://localhost:5173
echo    - Flutter Web (Người thân) : http://localhost:8080
echo =======================================================================
echo.
pause
