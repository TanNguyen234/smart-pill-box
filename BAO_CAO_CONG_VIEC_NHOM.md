# BÁO CÁO NHẬT KÝ CÔNG VIỆC (DỰ ÁN SMART PILL BOX)

**Người thực hiện:** Lập trình viên Full-stack (Đảm nhận Vai trò 1 & Vai trò 5)
**Mục tiêu:** Xây dựng phần Backend API (FastAPI) và các Giao diện Lịch sử / Cảnh báo trên Ứng dụng Di động (Flutter).

---

## 1. CÁC TÍNH NĂNG VÀ MODULE ĐÃ HOÀN THÀNH

### 🛠 Phần 1: Backend (FastAPI + SQLite)
Tôi đã xây dựng hoàn chỉnh hệ thống API và cơ sở dữ liệu để phục vụ ứng dụng, bao gồm:
1. **Thiết kế Cơ sở dữ liệu (`models.py`)**:
   - Tạo 5 bảng CSDL: `users` (Tài khoản), `care_receivers` (Người bệnh), `schedules` (Lịch uống), `medication_events` (Sự kiện thiết bị), `alerts` (Cảnh báo).
2. **Khởi tạo Dữ liệu mẫu - Dummy Data (`database.py`)**:
   - Tự động tạo file SQLite `smartpill.sqlite3` tại thư mục `/data`.
   - Viết hàm `init_db()` để nạp sẵn 2 tài khoản (caregiver1, caregiver2) và 2 người bệnh (Nguyễn Văn A, Trần Thị B) mỗi khi khởi động server, giúp team test API dễ dàng.
3. **Phát triển API Endpoints (`main.py`)**:
   - `POST /login`: Đăng nhập (trả về role và user_id).
   - `POST /schedules`: Thêm lịch uống (Đã viết logic **chặn trùng giờ uống thuốc**).
   - `GET, PUT, DELETE /schedules`: Quản lý CRUD lịch uống thuốc.
   - `GET /events`: Lấy lịch sử kiện thiết bị (ngăn nào mở, uống lúc nào).
   - `GET /alerts` & `PATCH /alerts/{id}`: Xem danh sách cảnh báo và Cập nhật trạng thái (Đã kiểm tra, Đã hỗ trợ, Bỏ qua).

### 📱 Phần 2: Ứng dụng Flutter (Vai trò 5 - UI Cảnh báo & Lịch sử)
1. **Giao tiếp Máy chủ (`api_service.dart`)**:
   - Đóng gói toàn bộ lệnh `http.get` và `http.patch` để lấy sự kiện, cảnh báo và cập nhật.
   - **Tính năng đặc biệt**: Cho phép nhận IP động từ dòng lệnh (`String.fromEnvironment('API_BASE_URL')`) để team có thể test linh hoạt trên cả Máy ảo (Emulator) lẫn Máy thật (Smartphone) qua Wifi.
2. **Giao diện Lịch sử Uống thuốc (`history_screen.dart`)**:
   - Thiết kế danh sách bất đồng bộ (`FutureBuilder`), hiển thị rõ ràng ngăn chứa và thời điểm uống.
3. **Giao diện Xử lý Cảnh báo (`alerts_screen.dart`)**:
   - Giao diện chia màu thông minh (Đỏ: Cần xử lý, Xanh: Đã xử lý).
   - Tích hợp `AlertDialog` dạng popup để người dùng tương tác chuyển trạng thái của cảnh báo.

---

## 2. QUÁ TRÌNH KHẮC PHỤC LỖI (BUG FIXES)
Trong quá trình phát triển và kiểm thử nội bộ, tôi đã phát hiện và xử lý triệt để các lỗi sau để code chạy ổn định:

1. **Lỗi Đồng bộ Dữ liệu (Data Mapping Mismatch)**:
   - *Triệu chứng:* Backend mới tạo gửi về biến `care_receiver_id` nhưng Flutter Model cũ lại bắt biến `patient_id`.
   - *Khắc phục:* Đã sửa lại file `models.dart` và `smart_pill_api.dart` trong Flutter để đồng nhất toàn bộ key JSON với Backend mới.
2. **Lỗi Tham số Dữ liệu giả (Patient Argument Error)**:
   - *Triệu chứng:* Lỗi Compile khi dùng mảng `Patient` do truyền dư thuộc tính `caregiverId` và `age` so với thiết kế của Frontend.
   - *Khắc phục:* Xóa các thuộc tính thừa, chỉ giữ lại `id` và `name` ở hàm mock data.
3. **Lỗi Không tìm thấy đường mạng (No route to host - OS Error 113)**:
   - *Triệu chứng:* Điện thoại thật không gọi được API do code cũ đang bị hardcode cứng địa chỉ IP máy ảo (`10.0.2.2`).
   - *Khắc phục:* Thay thế bằng biến môi trường `API_BASE_URL`.

---

## 3. HƯỚNG DẪN DÀNH CHO TEAM (QUY TRÌNH CHẠY TEST)

Để các bạn khác trong nhóm tải code về và chạy thử, vui lòng làm đúng 2 bước sau:

**Bước 1: Bật Backend**
```bash
cd backend
source .venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8000
```
- API Swagger UI (Giao diện xem API): `http://localhost:8000/docs`

**Bước 2: Bật Flutter App (Dùng IP của bạn)**
- Mở Terminal khác, gõ lệnh `ip a` (Linux) hoặc `ipconfig` (Windows) để lấy IPv4 của máy tính (VD: 192.168.1.20).
```bash
cd flutter-app
# Nhớ đổi IP dưới đây thành IP thực tế của máy bạn
flutter run --dart-define=API_BASE_URL=http://192.168.1.20:8000
```
- Đăng nhập App với tài khoản: `caregiver1` / Mật khẩu: `123456`.
- Chuyển sang Tab "Lịch sử" hoặc "Cảnh báo" ở đáy màn hình để tận hưởng thành quả!
