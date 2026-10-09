# Smart Pill Box

Bootstrap gồm một backend FastAPI/SQLite, web simulator cho operator và ứng dụng Flutter cho caregiver. Dữ liệu chỉ là dữ liệu giả.

## Chuẩn bị backend

Yêu cầu Python 3.12. Từ PowerShell:

```powershell
cd "D:\Download\SmartPillBox\backend"
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Trong `backend\.env`, đặt `JWT_SECRET` và `DEMO_PASSWORD` thành giá trị riêng trên máy. Sau đó chạy seed và API:

```powershell
.\.venv\Scripts\python.exe scripts\seed_demo.py
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## Ba cửa sổ PowerShell

Backend chạy ở `http://localhost:8000`; SQLite nằm tại `backend\data\smartpill.sqlite3`.

```powershell
# Cửa sổ 1 — backend
cd "D:\Download\SmartPillBox\backend"
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

```powershell
# Cửa sổ 2 — simulator trên http://localhost:5173
cd "D:\Download\SmartPillBox\web-simulator"
npm install
npm run dev
```

```powershell
# Cửa sổ 3 — Android Emulator
cd "D:\Download\SmartPillBox\flutter-app"
flutter pub get
flutter run --dart-define=API_BASE_URL=http://10.0.2.2:8000
```

Trước lần chạy đầu, tạo `.env` từ `backend\.env.example` và chạy `scripts\seed_demo.py`. Hai caregiver là `caregiver-a@example.test` và `caregiver-b@example.test`; operator là `operator@example.test`. Cả ba dùng mật khẩu cục bộ từ `DEMO_PASSWORD` trong `.env`. Không đưa `.env` hoặc database lên Git.

Flutter giữ token trong bộ nhớ; đăng nhập lại sau khi đóng hoặc tải lại ứng dụng. Trên điện thoại thật, đổi `API_BASE_URL` thành IP LAN của máy backend. HTTP local chỉ được bật trong cấu hình Android debug.

## Kiểm tra và phạm vi

```powershell
cd "D:\Download\SmartPillBox\backend"
.\.venv\Scripts\python.exe -m pytest
cd "D:\Download\SmartPillBox\web-simulator"
npm run build
cd "D:\Download\SmartPillBox\flutter-app"
flutter analyze
flutter test
```

Đã có đăng nhập JWT, quyền caregiver/operator, hồ sơ, tạo/sửa lịch, trạng thái ba ngăn và sự kiện mở/đóng nắp có chống UUID trùng. Nắp mở không xác nhận thuốc đã uống. Tiến đồng hồ, lấy viên, LED/buzzer, nhắc lại, lịch sử và cảnh báo chưa triển khai.
