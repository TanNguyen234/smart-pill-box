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

Website operator mô phỏng thiết bị phần cứng ảo 3 ngăn kết nối trực tiếp với backend FastAPI và SQLite. Hệ thống hỗ trợ mở/đóng nắp, nắp 3D-lite bằng CSS, đọc cảm biến tải trọng `WEIGHT_READING` (với ngưỡng nhận diện lấy thuốc 0.3g và hỗ trợ thử nhiễu cân 0.1g không làm giảm viên), nút bấm xác nhận trên hộp `CONFIRM_PRESSED`, tiến đồng hồ ảo (`+1m`, `+2m`, `+5m` và `Mốc tiếp theo`), đèn LED, còi báo Web Audio API và nhật ký thao tác đầy đủ.

Các API mô phỏng chính: `GET /api/simulation/state`, `POST /api/simulation/events` (nhận `LID_OPENED`, `LID_CLOSED`, `WEIGHT_READING`, `CONFIRM_PRESSED` kèm `compartment_id`/`slot`), `POST /api/simulation/advance` (hoặc `/clock`) với `{ "minutes": 1 }`, và `POST /api/simulation/reset` với `{ "confirm": true }`. UUID giúp thao tác không bị áp dụng hai lần khi gửi lại (idempotency). Reset yêu cầu xác nhận, xóa dữ liệu demo/nhật ký cũ và khôi phục đồng hồ cùng số viên về ban đầu mà không làm mất tài khoản hay lịch thuốc của caregiver. Nắp mở hoặc sụt giảm trọng lượng không được coi là bằng chứng xác thực đã uống cho đến khi có sự kiện xác nhận.

Flutter hiện có đăng nhập, danh sách/tạo lịch và trang hôm nay ban đầu. Màn hình lịch sử và cảnh báo trong Flutter, thông báo nền, cảm biến thật và trình dựng APK trên emulator chưa được triển khai trong phần này.
