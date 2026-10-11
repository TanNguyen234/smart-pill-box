# HƯỚNG DẪN HOẠT ĐỘNG VÀ VẬN HÀNH CHỨC NĂNG — THÀNH VIÊN 2 (BÙI MINH VUI)

> **Dự án:** Smart Pill Box — Hộp Thuốc Thông Minh  
> **Nhánh phát triển:** `quytrinhnhacvacanhcao` (và `donghonhacnho`)  
> **Người thực hiện:** Thành viên 2 — Phụ trách **Quy trình nhắc giờ, trạng thái thuốc và cảnh báo**  
> **Tài liệu đối chiếu:** `Dac_ta_thong_nhat_API_Database_Du_lieu_mau_Smart_Pill_Box.md`

---

## 1. Tổng quan phạm vi công việc đã hoàn thành

Thành viên 2 chịu trách nhiệm toàn bộ logic nghiệp vụ cốt lõi của hộp thuốc từ Backend đến hiển thị thời gian thực trên Web và Mobile App:

| STT | Hạng mục công việc | Mô tả chi tiết & Endpoint |
|---|---|---|
| **1** | **Đồng hồ giả lập theo phút** | Điều khiển thời gian độc lập với đồng hồ máy tính, chỉ tiến lên (`+1`, `+2`, `+5`, `+60` phút). Endpoint: `POST /api/simulation/advance` và `GET /api/simulation/clock/state`. |
| **2** | **Kích hoạt lần nhắc (Mốc 1)** | Tự động quét mốc giờ lịch (ví dụ 08:00): tạo bản ghi `DoseOccurrence` (`status="REMINDING"`, `reminder_count=1`), bật đèn LED và còi Buzzer ngăn tương ứng. |
| **3** | **Nhắc lại lần 2 (Sau 2 phút)** | Sau 2 phút (08:02) người bệnh chưa xác nhận: cập nhật `reminder_count=2`, phát thông báo nhắc lại lần 2 trên hộp và hiển thị trong lịch sử mốc. |
| **4** | **Cảnh báo quá hạn (Sau 5 phút)** | Sau 5 phút (08:05) chưa uống: tự động tắt đèn/còi, chuyển `status="UNCONFIRMED"`, sinh duy nhất một `Alert` (`kind="MISSED_CONFIRMATION"`, `status="PENDING"`) gửi đến người thân (caregiver). |
| **5** | **Thao tác thiết bị ảo & Idempotency** | Xử lý các sự kiện `LID_OPENED`, `LID_CLOSED`, `PILL_REMOVED` (giảm 1 viên và 0,5g), `CONFIRMED` (xác nhận đúng hạn/trễ hạn) và chống ghi trùng lặp bằng `event_uuid`. Endpoint: `POST /api/simulation/events`. |
| **6** | **Đặt lại buổi demo (Reset)** | Phục hồi đồng hồ về `07:59:00`, hoàn nguyên 3 ngăn thuốc ban đầu và dọn dẹp các lần uống/cảnh báo thử nghiệm. Endpoint: `POST /api/simulation/reset` với payload `{"confirmation": "RESET_DEMO"}`. |
| **7** | **Đọc & Xử lý cảnh báo trên Flutter** | Thêm tab **Cảnh báo** trên Flutter: người thân xem cảnh báo quá hạn thời gian thực, bấm **XỬ LÝ** kèm ghi chú mà không làm thay đổi lịch sử uống thuốc. Endpoint: `GET /api/alerts`, `PATCH /api/alerts/{id}` (hoặc `POST /api/alerts/{id}/resolve`). |
| **8** | **Đồng bộ thời gian thực Web & App** | App Flutter và Web Simulator tự động quét cập nhật đồng hồ và cảnh báo mỗi 2 giây/lần. Bổ sung nút Đồng bộ 🔄 và thao tác kéo làm mới (Pull-to-refresh). |
| **9** | **Trang Test chuyên dụng cho Thành viên 2** | Giao diện tại `http://localhost:5173/dongho` hiển thị đồng hồ, 3 ngăn hộp thuốc trực quan (đèn, còi, lời nhắc), nút cộng giờ và lịch sử các mốc đi qua mà không cần đăng nhập. |
| **10** | **Kiểm thử tự động (Unit Test / Pytest)** | Bộ test case kiểm tra toàn diện quy trình 07:59 &rarr; 08:00 &rarr; 08:02 &rarr; 08:05 &rarr; Xử lý cảnh báo &rarr; Reset demo đạt **100% Pass**. |

---

## 2. Chu kỳ nhắc giờ mẫu (Kịch bản Demo)

```
[07:59:00] -- Khởi tạo ban đầu: Hộp thuốc chờ, Đèn Tắt, Còi Tắt, Chưa đến giờ uống.
     |
     v (+1 phút)
[08:00:00] -- MỐC NHẮC LẦN 1: Tạo DoseOccurrence (REMINDING).
              -> Đèn LED Ngăn 1: BẬT
              -> Còi Buzzer: BẬT
              -> Lời nhắc: "Đến giờ 08:00"
     |
     v (+2 phút)
[08:02:00] -- NHẮC LẠI LẦN 2 (Trễ 2 phút chưa xác nhận):
              -> reminder_count = 2
              -> Lời nhắc: "NHẮC LẠI: Đã trễ 2 phút!"
              -> Đèn & Còi tiếp tục bật.
     |
     v (+3 phút)
[08:05:00] -- QUÁ HẠN 5 PHÚT (Chưa uống):
              -> Trạng thái lần uống: UNCONFIRMED
              -> Đèn LED: TẮT, Còi Buzzer: TẮT
              -> Tự động tạo 1 ALERT gửi đến App Flutter người thân!
              -> App Flutter nhận cảnh báo đỏ: "Quá hạn 5 phút chưa xác nhận uống Thuốc A (Ngăn 1)"
     |
     v (Người thân mở App Flutter)
[XỬ LÝ ALERT] -- Bấm "XỬ LÝ" -> Nhập ghi chú: "Đã gọi điện nhắc uống" -> Alert chuyển sang xanh (CHECKED).
     |
     v (Bấm nút trên Web)
[ĐẶT LẠI DEMO] -- Trở về 07:59:00, xóa dữ liệu thử nghiệm để demo lại từ đầu.
```

---

## 3. Hướng dẫn chạy thử nghiệm thực tế (3 Terminal)

Mở **3 tab Terminal riêng biệt** trong VS Code hoặc PowerShell:

### Terminal 1: Khởi động Backend (FastAPI + SQLite)
```powershell
cd D:\Project_TMDT\smart-pill-box\backend
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```
> Khi thấy dòng: `Uvicorn running on http://0.0.0.0:8000` là máy chủ đã sẵn sàng.

### Terminal 2: Khởi động Web Simulator
```powershell
cd D:\Project_TMDT\smart-pill-box\web-simulator
npm run dev
```
> Truy cập trình duyệt vào trang test của Thành viên 2:  
> 👉 **http://localhost:5173/dongho**  
> *(Hoặc trang điều khiển chính của Operator tại: http://localhost:5173/)*

### Terminal 3: Khởi động Mobile App Flutter
- **Cách A: Chạy trực tiếp trên Windows Desktop (nhanh và nhẹ nhất):**
  ```powershell
  cd D:\Project_TMDT\smart-pill-box\flutter-app
  flutter run -d windows
  ```
- **Cách B: Chạy trên máy ảo Android (Medium_Phone):**
  ```powershell
  flutter emulators --launch Medium_Phone
  cd D:\Project_TMDT\smart-pill-box\flutter-app
  flutter run --dart-define=API_BASE_URL=http://10.0.2.2:8000
  ```
> Đăng nhập tài khoản người thân mẫu:
> - **Email:** `caregiver-a@example.test`
> - **Mật khẩu:** `123456`

---

## 4. Kịch bản nghiệm thu từng bước

1. **Kiểm tra trạng thái ban đầu:**
   - Trên Web `/dongho`: Nhấn nút đỏ **Đặt lại demo (07:59)**. Đồng hồ chỉ `07:59:00`.
   - Trên App Flutter: Nhìn góc trên thẻ xanh, giờ demo hiển thị đồng bộ `07:59:00`.
2. **Kích hoạt giờ uống 08:00:**
   - Trên Web `/dongho`: Nhấn **+1 Phút**. Đồng hồ nhảy lên `08:00:00`.
   - Web: Thẻ Ngăn 1 chuyển viền đỏ, **Đèn LED: Bật**, **Còi Buzzer: Bật**, Danh sách hiện: *"Tới giờ uống thuốc, còi và đèn đã bật"*.
   - Flutter: Sau 2 giây đồng hồ tự nhảy lên `08:00:00`, dòng trạng thái báo *"Đang đến giờ uống Thuốc A (Ngăn 1)"*.
3. **Kích hoạt nhắc lại lần 2 lúc 08:02:**
   - Trên Web `/dongho`: Nhấn **+2 Phút**. Đồng hồ nhảy lên `08:02:00`.
   - Web: Thẻ Ngăn 1 chuyển lời nhắc thành `NHẮC LẠI: Đã trễ 2 phút!`. Danh sách hiện dòng màu cam: *"Nhắc lại lần 2: Đã trễ 2 phút chưa xác nhận uống!"*.
4. **Kích hoạt cảnh báo quá hạn 08:05:**
   - Trên Web `/dongho`: Nhấn **+5 Phút**. Đồng hồ nhảy lên `08:07:00`.
   - Web: Đèn và còi Ngăn 1 tự động TẮT. Danh sách hiện dòng: *"Đã tạo cảnh báo quá hạn gửi đến người thân!"*.
   - Trên App Flutter: Mở tab **Cảnh báo** (hình quả chuông ở thanh điều hướng dưới cùng). Cảnh báo đỏ xuất hiện: *"Quá hạn 5 phút chưa xác nhận uống Thuốc A (Ngăn 1)"*.
5. **Xử lý cảnh báo trên App:**
   - Người thân bấm nút **XỬ LÝ**, nhập ghi chú (ví dụ: *"Đã liên hệ kiểm tra"*), bấm **Xác nhận**.
   - Cảnh báo chuyển sang màu xám có dấu tick xanh, ghi nhận đã xử lý hoàn tất.
6. **Đặt lại để demo lại:**
   - Bấm nút **Đặt lại demo (07:59)** trên Web để khôi phục toàn bộ hệ thống về ban đầu.

---

## 5. Lệnh chạy kiểm thử tự động (Pytest)

Để chạy kiểm thử toàn bộ logic nghiệp vụ mà không cần bật giao diện:
```powershell
cd D:\Project_TMDT\smart-pill-box\backend
.\.venv\Scripts\python.exe -m pytest
```
**Kết quả:** Toàn bộ 3 bài kiểm thử (Phân quyền, Idempotent sự kiện, và Quy trình nhắc nhở & cảnh báo của Thành viên 2) đều đạt **3 passed 100%**.

---
*Tài liệu được khởi tạo và đồng bộ tự động cho nhánh `quytrinhnhacvacanhcao`.*
