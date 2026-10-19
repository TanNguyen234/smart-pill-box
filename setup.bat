@echo off
chcp 65001 >nul
title Smart Pill Box - Auto Setup Script
echo =======================================================================
echo          CÀI ĐẶT TỰ ĐỘNG TOÀN BỘ HỆ THỐNG SMART PILL BOX
echo =======================================================================
echo.

echo [1/3] Đang thiết lập Backend FastAPI...
cd /d %~dp0backend
if not exist .venv (
    echo   - Đang tạo Python virtual environment (.venv)...
    python -m venv .venv
)
call .venv\Scripts\activate.bat
echo   - Đang cài đặt thư viện Python từ requirements.txt...
pip install -r requirements.txt --quiet
if not exist .env (
    echo   - Đang tạo tệp cấu hình .env...
    copy .env.example .env >nul
    echo DEMO_PASSWORD=Password123!>>.env
)
echo   - Đang khởi tạo cơ sở dữ liệu mẫu SQLite (seed demo)...
python scripts\seed_demo.py
call deactivate

echo.
echo [2/3] Đang thiết lập Web Simulator (React + TypeScript)...
cd /d %~dp0web-simulator
call npm install --silent

echo.
echo [3/3] Đang tải các gói phụ thuộc Flutter App...
cd /d %~dp0flutter-app
call flutter pub get

echo.
echo =======================================================================
echo    CÀI ĐẶT THÀNH CÔNG 100%!
echo    Bây giờ bạn chỉ cần chạy "start_all.bat" để khởi động toàn bộ dự án.
echo =======================================================================
echo.
pause
