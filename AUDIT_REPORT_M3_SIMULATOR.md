# BÁO CÁO KIỂM TOÁN KỸ THUẬT TOÀN DIỆN & ĐỘC LẬP: WEB IOT SIMULATOR (MEMBER 3)

**Dự án**: Smart Pill Box — IoT Medication Reminder & Monitoring (Software Simulation)  
**Đối tượng kiểm toán**: Thành viên 3 (M3) — Web IoT Simulator  
**Mã nguồn được kiểm toán**:  
- Frontend Simulator: `d:\Download\SmartPillBox\web-simulator`  
- Backend Simulation Endpoints: `d:\Download\SmartPillBox\backend\app`  
**Căn cứ đặc tả chuẩn (Ground Truth)**:  
- Đặc tả thiết bị mô phỏng: `docs/03_SIMULATOR.md`  
- Hợp đồng API v1: `docs/05_API_CONTRACT.md`  
- Máy trạng thái & Quy tắc nghiệp vụ: `docs/02_RULES_STATE_MACHINE.md`  
- Kế hoạch phân công nhiệm vụ: `project/tasks.csv` (Nhiệm vụ T003, T008, T013, T018, T023, T028, T033, T038)  
- Kiến trúc & Phạm vi hệ thống: `docs/00_SCOPE.md` & `docs/01_ARCHITECTURE.md`  
**Ngày thực hiện kiểm toán**: 2026-10-16  
**Chế độ kiểm toán**: Read-Only Audit (Không sửa đổi mã nguồn ứng dụng)  
**Cơ quan kiểm toán**: Master Audit Team (Teamwork Independent Forensic Auditor)

---

## MỤC LỤC BÁO CÁO

1. [TỔNG QUAN KẾT QUẢ KIỂM TOÁN (EXECUTIVE SUMMARY)](#1-tổng-quan-kết-quả-kiểm-toán-executive-summary)
2. [MA TRẬN ĐỐI CHIẾU 8 TASK WORKPLAN CỦA MEMBER 3 (T003 – T038)](#2-ma-trận-đối-chiếu-8-task-workplan-của-member-3-t003--t038)
3. [KIỂM TOÁN CHI TIẾT 6 THÀNH PHẦN GIAO DIỆN BẮT BUỘC (R1)](#3-kiểm-toán-chi-tiết-6-thành-phần-giao-diện-bắt-buộc-r1)
4. [KIỂM TOÁN TUÂN THỦ HỢP ĐỒNG API VÀ RANH GIỚI PHẦN CỨNG (R2)](#4-kiểm-toán-tuân-thủ-hợp-đồng-api-và-ranh-giới-phần-cứng-r2)
5. [BÁO CÁO KIỂM TRA TĨNH KHỬ ICON AI SLOP VÀ COMMENT TỰ SỰ (R3)](#5-báo-cáo-kiểm-tra-tĩnh-khử-icon-ai-slop-và-comment-tự-sự-r3)
6. [KIỂM TRA CHẤT LƯỢNG KỸ THUẬT & QUẢN LÝ TRẠNG THÁI (R4)](#6-kiểm-tra-chất-lượng-kỹ-thuật--quản-lý-trạng-thái-r4)
7. [KẾ HOẠCH KHẮC PHỤC HÀNH ĐỘNG ĐƯỢC (ACTIONABLE REMEDIATION PLAN)](#7-kế-hoạch-khắc-phục-hành-động-được-actionable-remediation-plan)

---

## 1. TỔNG QUAN KẾT QUẢ KIỂM TOÁN (EXECUTIVE SUMMARY)

Báo cáo này công bố kết quả kiểm toán độc lập, toàn diện đối với toàn bộ phần việc của **Thành viên 3 (M3 - Web IoT Simulator)** trong hệ thống Smart Pill Box. Web IoT Simulator đóng vai trò thay thế cho thiết bị phần cứng vật lý (Virtual ESP32 Device với 3 ngăn chứa thuốc, cảm biến tải trọng load cell HX711, công tắc từ đóng/mở nắp, còi báo buzzer và nút bấm xác nhận uống thuốc).

### 1.1. Các điểm mạnh kỹ thuật nổi bật (Strengths)

1. **Khả năng biên dịch và Type-safety tuyệt đối (Clean Build & Types)**: 
   - Mã nguồn được xây dựng trên nền tảng React 19, TypeScript và Vite.
   - Vượt qua kiểm tra kiểu tĩnh của TypeScript (`npx tsc -b`) với **Exit code 0** (0 lỗi kiểu dữ liệu).
   - Đóng gói production qua Vite (`npx vite build`) thành công 100%, 17 modules chuyển đổi trơn tru, tạo bundle tối ưu kích thước 237.30 kB trong 479ms.
   - Kiểm tra tĩnh linter qua Oxlint (`npx oxlint`) đạt **0 warnings, 0 errors** trên toàn bộ các tệp nguồn, tuân thủ nghiêm ngặt 116 quy tắc mã nguồn.
2. **Cơ chế âm thanh Buzzer Web Audio API đạt chuẩn công nghiệp**:
   - Hiện thực xuất sắc còi báo ảo bằng Web Audio API thuần túy (`App.tsx:144-162`), sử dụng `AudioContext`, `OscillatorNode` (sóng sin tần số chuẩn 880Hz) và `GainNode` để định hình đường bao âm lượng (exponential envelope mượt mà, không tiếng lách cách clipping).
   - Giải quyết triệt để rào cản chính sách Autoplay Policy của trình duyệt hiện đại thông qua cơ chế người dùng chủ động mở khóa (Sound Opt-in button kích hoạt `audioContext.resume()` tại `App.tsx:203-212`).
   - Tích hợp chỉ báo thị giác dự phòng (Visual Fallback indicator) nhấp nháy theo nhịp còi thông qua CSS animation `buzzer-pulse`, đảm bảo an toàn y tế trong trường hợp âm thanh bị tắt hoặc chặn.
3. **Quản lý trạng thái Single Source of Truth (SSoT) chuẩn mực**:
   - Giao diện UI render hoàn toàn thụ động (passive render) dựa trên dữ liệu phản hồi từ backend thông qua endpoint `GET /api/simulation/state`.
   - Tuyệt đối **không sử dụng `localStorage` hay `sessionStorage`** để lưu trữ trạng thái phân xử liều thuốc hay số viên. Tránh hoàn toàn hiện tượng phân rã trạng thái (state drift) giữa client và SQLite DB.
   - Không lạm dụng cơ chế cập nhật lạc quan (No Optimistic UI Updates). Khi thao tác, các nút bấm chuyển sang trạng thái disabled kèm chỉ báo "Đang gửi…", chỉ phản ánh giá trị mới khi nhận được phản hồi HTTP 200 từ backend.
4. **Xử lý ngoại lệ và mất kết nối mạng (Resilient Offline UX)**:
   - Cơ chế polling tuần hoàn 2000ms có quản lý vòng đời tài nguyên hoàn hảo (tự động dọn dẹp timer qua `clearInterval` khi unmount).
   - Khi backend mất kết nối hoặc trả về lỗi 4xx/5xx, giao diện lập tức chuyển Connection Badge sang trạng thái `OFFLINE` màu đỏ, hiển thị Banner cảnh báo lỗi rõ ràng, và **giữ nguyên trạng thái hiển thị hợp lệ gần nhất**, tuyệt đối không tạo thành công ảo (No fake success).
5. **Mã nguồn sạch và Vô trùng Icon AI Slop**:
   - Quét tĩnh tự động khẳng định **0 emoji AI slop** (✨, 🤖, 🧠, 🪄, 🚀, 🔥, ⚡, 💡, 🎉).
   - **0 bình luận tự sự / nhật ký hội thoại của AI** ("Here we implement...", "As requested..."). Toàn bộ mã nguồn chỉ có duy nhất 1 chú thích mang tính kỹ thuật kiến trúc y tế chuẩn mực tại `App.tsx:160`.
   - Giao diện sử dụng bảng màu lâm sàng (clinical color palette) trang nhã, đúng phong cách thiết bị y tế chuyên nghiệp.

### 1.2. Các sai phạm và thiếu sót cốt lõi (Core Deficiencies & Architectural Violations)

Bên cạnh các điểm mạnh về cú pháp và UX, kiểm toán phát hiện **4 sai phạm cốt lõi** làm gãy đổ tính toàn vẹn của mô hình IoT y tế và sai lệch nghiêm trọng so với hợp đồng đặc tả:

1. **Đảo ngược Ranh giới Phần cứng (Hardware Boundary Inversion - Nghiêm trọng nhất)**:
   - **Vi phạm điều khoản cấm của API Contract Section 3 & Simulator Spec Section 4**: Bộ mô phỏng được quy định chỉ là thiết bị ngoại vi vật lý, chỉ được gửi các tín hiệu cảm biến thô cấp thấp (`LID_OPENED`, `LID_CLOSED`, `WEIGHT_READING: {weight_g}`, `CONFIRM_PRESSED: {occurrence_id}`). 
   - **Thực tế sai phạm**: Client tự phát sinh và gửi trực tiếp các sự kiện kết luận nghiệp vụ cấp cao `PILL_DISPENSED` và `DOSE_CONFIRMED` (`App.tsx:43, 392, 393`).
   - **Hệ quả**: Backend (`main.py:402-408`) chấp nhận sự kiện nghiệp vụ và tự trừ 0.5g thay vì tiếp nhận số đo load cell. Mô hình cơ sở dữ liệu `DoseOccurrence` (`models.py:38-45`) **hoàn toàn thiếu cột `sensor_evidence`** (`weight_drop`, `opened`, `none`), làm mất sạch dấu vết kiểm toán y tế (không thể phân biệt bệnh nhân uống thuốc có sụt cân thật hay chỉ nhấn nút khống).
2. **Sai lệch Hợp đồng API (API Contract Drift)**:
   - **Sai lệch Route**: Đặc tả chuẩn yêu cầu `POST /api/simulation/advance`. Cả Frontend (`App.tsx:269`) và Backend (`main.py:442`) tự ý đổi thành `POST /api/simulation/clock`.
   - **Sai lệch Định danh ngăn**: Đặc tả chuẩn quy định `compartment_id` (1..3). Cả hai bên đang dùng trường `slot`.
   - **Sai lệch Giới hạn thời gian**: Backend giới hạn `minutes` từ `1..60`, vi phạm dải giá trị chuẩn `1..1440` trong `05_API_CONTRACT.md`.
   - **Thiếu trường bảo vệ Reset**: `POST /api/simulation/reset` không gửi và không kiểm tra trường `{ "confirm": true }` theo hợp đồng mà đòi hỏi `{ "event_uuid": UUID }`.
3. **Thiếu sót 3 Thành phần Giao diện Bắt buộc trong Workplan (Missing UI Requirements)**:
   - **Nắp 3D-lite CSS**: Đặc tả yêu cầu nắp 3 ngăn mô phỏng góc mở/đóng bằng CSS 3D Transforms (`perspective`, `rotateX`). Hiện thực thực tế chỉ là một text badge 2D phẳng (`App.tsx:382`) đổi màu cam/xám.
   - **Nút Next Milestone**: Chỉ có các nút bước cố định `+1 phút`, `+2 phút`, `+5 phút` (`App.tsx:372`). Thiếu nút "Next Milestone" để người thuyết trình nhảy tức thì đến mốc sự kiện logic gần nhất.
   - **Ô nhập Manual weight reading kèm nhiễu 0.1g**: Hoàn toàn vắng bóng trong mã nguồn. Chỉ có nút cứng "Lấy một viên −0.5g", không có ô nhập trọng lượng tùy biến và không kiểm thử tình huống nhiễu cơ học 0.1g không làm giảm số viên.
4. **Đèn LED Dot thiếu hiệu ứng Blinking**: Đèn LED hiển thị trạng thái on/off qua màu sắc nhưng thiếu animation nhấp nháy khi có đợt nhắc nhở tích cực.

---

## 2. MA TRẬN ĐỐI CHIẾU 8 TASK WORKPLAN CỦA MEMBER 3 (T003 – T038)

Theo `project/tasks.csv`, `project/WORKPLAN_TABLE.md` và `docs/08_TEAM_WORKPLAN.md`, Member 3 đảm nhiệm 8 nhiệm vụ với tổng thời lượng ước tính **61 giờ**:

| Task ID | Tên công việc (WBS / tasks.csv) | Mốc / Tuần | Giờ ước tính | Tiêu chí nghiệm thu chuẩn (Acceptance Criteria) | Trạng thái thực tế trong mã nguồn | Bằng chứng cụ thể (File & Line Number) | Đánh giá sai lệch & Rủi ro |
|:---:|---|:---:|:---:|---|:---:|---|---|
| **T003** | Web simulator wireframe/3 ngăn | W1 | 6h | Có từng control map sang event phần cứng. Phải xác định rõ từng nút/cần gạt tương ứng với mã event gửi lên backend. | **Một phần** | `docs/03_SIMULATOR.md:16-25`<br>`web-simulator/src/App.tsx:379-400` | Đặc tả văn bản có bảng map event tại Section 3, nhưng không có file artifact wireframe/mockup chuyên biệt trong repo. Mã event bị lệch chuẩn nghiệp vụ. |
| **T008** | Khởi tạo React Vite TS | W1 | 5h | `npm run build` thành công trên môi trường sạch, không lỗi typecheck/lint. | **Hoàn thành** | `web-simulator/package.json:1-32`<br>`web-simulator/tsconfig.json:1-25`<br>`vite.config.ts:1-7` | Setup chuẩn React 19 + Vite 8.3 + TS 6.0 + Oxlint. Chạy `tsc -b`, `vite build`, `oxlint` đều đạt Exit code 0 hoàn hảo. |
| **T013** | Web operator login + GET state | W2 | 9h | 3 ngăn render chính xác theo API `/api/simulation/state`; lỗi token/hết hạn hiển thị rõ ràng (visible error). | **Hoàn thành** | `web-simulator/src/App.tsx:164-186`<br>`web-simulator/src/App.tsx:304-330`<br>`web-simulator/src/App.tsx:379-400` | Màn hình đăng nhập operator bảo vệ truy cập (`App.tsx:304-330`). Hiển thị lỗi login rõ ràng (`App.tsx:324`). Render 3 ngăn thuốc từ `device.compartments`. Polling đều đặn 2000ms. |
| **T018** | Web lid/open/weight actions HTTP | W2 | 11h | Click sinh UUID v4 cho event, DB phản ánh thay đổi thật (`Click emits UUID event, DB reflects real change`). Xử lý lỗi request trung thực. | **Một phần (Sai lệch kiến trúc)** | `web-simulator/src/App.tsx:250-262`<br>`web-simulator/src/App.tsx:389-393`<br>`backend/app/main.py:402-408` | Sinh UUID v4 chuẩn qua `crypto.randomUUID()`. Đóng/mở nắp gửi `LID_OPENED`/`LID_CLOSED`. Nhưng hành động cân nặng lại gửi `PILL_DISPENSED` thay vì `WEIGHT_READING`. Đổi tên trường thành `slot`. |
| **T023** | Web LED/buzzer + confirm button | W3 | 9h | Confirm trong DB cập nhật sang Flutter, âm thanh có cơ chế xin quyền/opt-in (`Confirm in DB updates Flutter, sound opt-in`). | **Một phần (Sai lệch kiến trúc)** | `web-simulator/src/App.tsx:144-162`<br>`web-simulator/src/App.tsx:203-212`<br>`web-simulator/src/App.tsx:345, 385, 393` | Buzzer Web Audio API có opt-in chuẩn mực. LED dot hiển thị on/off rõ ràng. Nút confirm có mặt. Tuy nhiên: gửi `DOSE_CONFIRMED` thay vì `CONFIRM_PRESSED`; LED thiếu animation blinking; nắp thiếu 3D CSS. |
| **T028** | Web clock controls and reset demo | W4 | 8h | Nhảy cóc thời gian qua các deadline phải kích hoạt đủ sự kiện trung gian; nút reset bắt buộc có xác nhận (`Jump across deadlines triggers all; reset requires confirm`). | **Một phần (Sai lệch API)** | `web-simulator/src/App.tsx:264-301`<br>`web-simulator/src/App.tsx:371-374`<br>`backend/app/main.py:442-509` | Reset có confirm dialog bảo vệ an toàn (`App.tsx:284`). Backend chạy transaction quét đủ từng phút khi advance (`main.py:459`). Nhưng gọi sai route `/clock` (thay vì `/advance`), thiếu nút Next Milestone. |
| **T033** | Web offline/retry/manual weight noise | W5 | 8h | Không giả mạo thành công khi API lỗi; biến động trọng lượng 0.1g không được suy đoán là đã lấy thuốc (`No fake success, 0.1g not inferred as retrieval`). | **Một phần (Thiếu chức năng)** | `web-simulator/src/App.tsx:181, 344, 365`<br>`web-simulator/src/App.tsx:392` | Offline UX đạt xuất sắc: banner đỏ, giữ nguyên state, tự động retry 2s, không fake success. **Tuy nhiên, tính năng Manual weight reading và nhiễu 0.1g hoàn toàn chưa được lập trình trong code.** |
| **T038** | Polish simulator + record demo evidence | W6 | 5h | Cả 3 ngăn tương tác hoàn chỉnh, thể hiện trực quan mọi trạng thái UI (`3 compartments usable; visible UI states`). | **Một phần** | `web-simulator/src/App.tsx:379-430`<br>`web-simulator/src/App.css:1-240` | Giao diện hiển thị trực quan, hỗ trợ responsive, hiển thị nhật ký thời gian thực và lịch đồng bộ từ SQLite. Chưa có thư mục chứa ảnh chụp chứng cứ demo (screenshots) trong repository. |

---

## 3. KIỂM TOÁN CHI TIẾT 6 THÀNH PHẦN GIAO DIỆN BẮT BUỘC (R1)

Đối chiếu chi tiết 6 thành phần giao diện bắt buộc được quy định tại `docs/03_SIMULATOR.md` và `ORIGINAL_REQUEST.md`:

### 3.1. Nắp 3D-lite bằng CSS (CSS transforms, perspective, visual animation)
- **Yêu cầu chuẩn (`docs/03_SIMULATOR.md:10`)**: *"Ba cards tương ứng ngăn 1/2/3: nắp 3D-lite bằng CSS (không cần Three.js), LED dot, tình trạng lid..."*. Yêu cầu sử dụng các thuộc tính CSS 3D Transform (`perspective`, `rotateX`, `transform-origin`, `transition`) để tạo hiệu ứng thị giác mở lật nắp hộp thuốc rõ rệt.
- **Hiện trạng thực tế trong mã nguồn**: **KHÔNG ĐẠT (NON-COMPLIANT)**.
- **Bằng chứng mã nguồn**:
  - Tại `web-simulator/src/App.tsx:382`:
    ```tsx
    <span className={`lid-badge ${item.lid_open ? 'opened' : ''}`}>
      <i />{item.lid_open ? 'Đang mở' : 'Đang đóng'}
    </span>
    ```
  - Tại `web-simulator/src/App.css:47-50`:
    ```css
    .lid-badge { display:flex; align-items:center; gap:7px; padding:6px 9px; border-radius:50px; background:#eff1eb; color:#69756a; font-size:9px; }
    .lid-badge i { width:6px; height:6px; background:#829281; border-radius:50%; }
    .lid-badge.opened { background:#f5e8dc; color:#955b39; }
    .lid-badge.opened i { background:#c98251; }
    ```
- **Phân tích đánh giá**: Trạng thái nắp hiện thời chỉ là một huy hiệu phẳng (2D pill badge) với một dấu chấm tròn đổi màu từ xanh xám `#829281` sang cam nâu `#c98251`. Hoàn toàn không có bất kỳ cấu trúc không gian 3D nào (`perspective`, `rotateX(-105deg)`, `preserve-3d`). Người xem không có cảm nhận trực quan về việc nắp hộp đang mở ra hay đậy lại trong không gian thực.

### 3.2. Đèn LED Dot (Styling, color states, blinking)
- **Yêu cầu chuẩn (`docs/03_SIMULATOR.md:10, 22`)**: Đèn LED nằm trên từng ngăn, sáng/nhấp nháy khi `led_on = true` (có lịch nhắc đang kích hoạt), tắt khi bình thường. Là chỉ báo thị giác dự phòng (Visual Fallback) bắt buộc.
- **Hiện trạng thực tế trong mã nguồn**: **ĐẠT MỘT PHẦN (PARTIALLY COMPLIANT)**.
- **Bằng chứng mã nguồn**:
  - Tại `web-simulator/src/App.tsx:385`:
    ```tsx
    <div><span>ĐÈN BÁO</span><strong><i className={`led ${item.led === 'Bật' ? 'led-on' : ''}`} />{item.led}</strong></div>
    ```
  - Tại `web-simulator/src/App.css:65-66`:
    ```css
    .led { display:inline-block; width:7px; height:7px; border-radius:50%; background:#cbd0c7; }
    .led-on { background:#a4bd53; box-shadow:0 0 0 3px #edf3da; }
    ```
- **Phân tích đánh giá**: Đèn LED kích thước 7px có 2 trạng thái màu rõ ràng: tắt (màu xám nhạt `#cbd0c7`) và bật (màu xanh lá `#a4bd53` kèm viền shadow `#edf3da`). Tuy nhiên, thiếu hẳn animation nhấp nháy (`@keyframes led-blink`) khi đang trong giai đoạn báo động nhắc nhở (trong khi còi buzzer lại có animation pulse). Cần bổ sung animation nhấp nháy tần số 1Hz để tăng tính cảnh báo thị giác.

### 3.3. Còi báo Buzzer (Web Audio API fallback, oscillator/gain nodes, user unlock)
- **Yêu cầu chuẩn (`docs/03_SIMULATOR.md:13`, `docs/01_ARCHITECTURE.md:5`)**: Sử dụng Web Audio API phát tiếng bíp khi nhắc liều; xử lý rào cản Autoplay Policy của trình duyệt thông qua nút bấm người dùng; có LED/text fallback.
- **Hiện trạng thực tế trong mã nguồn**: **ĐẠT XUẤT SẮC (FULLY COMPLIANT)**.
- **Bằng chứng mã nguồn**:
  - Tạo âm thanh Web Audio API tại `web-simulator/src/App.tsx:144-162`:
    ```tsx
    function playReminderTone() {
      try {
        const context = audioContext.current ?? new window.AudioContext()
        audioContext.current = context
        const oscillator = context.createOscillator()
        const gain = context.createGain()
        oscillator.type = 'sine'
        oscillator.frequency.value = 880
        gain.gain.setValueAtTime(0.0001, context.currentTime)
        gain.gain.exponentialRampToValueAtTime(0.13, context.currentTime + 0.025)
        gain.gain.exponentialRampToValueAtTime(0.0001, context.currentTime + 0.35)
        oscillator.connect(gain)
        gain.connect(context.destination)
        oscillator.start()
        oscillator.stop(context.currentTime + 0.36)
      } catch {
        // Audio is an optional browser feature; the visual alarm remains authoritative.
      }
    }
    ```
  - Mở khóa âm thanh (User Opt-in Gesture) tại `web-simulator/src/App.tsx:203-212`:
    ```tsx
    async function toggleAudio() {
      try {
        if (!audioContext.current) audioContext.current = new window.AudioContext()
        await audioContext.current.resume()
        setAudioEnabled((enabled) => !enabled)
        setActionMessage('')
      } catch {
        setActionMessage('Trình duyệt không cho phép bật âm thanh. Đèn và chữ nhắc vẫn hoạt động.')
      }
    }
    ```
  - Nút bật âm thanh tại `App.tsx:345`: `<button className={`audio-toggle ${audioEnabled ? 'audio-on' : ''}`} type="button" onClick={() => void toggleAudio()} aria-pressed={audioEnabled}>{audioEnabled ? '♫ Còi đang bật' : '♫ Bật âm thanh'}</button>`.
  - Visual Fallback Pulse tại `App.tsx:387` và `App.css:201-202`: class `.buzzer-indicator.buzzer-on` chạy animation `buzzer-pulse 1.6s ease-in-out infinite`.
- **Phân tích đánh giá**: Thiết kế rất chuyên nghiệp: sử dụng đúng sóng sin 880Hz, tạo envelope bằng hàm `exponentialRampToValueAtTime` tránh tiếng rè/pop, bắt try/catch an toàn không làm crash giao diện nếu trình duyệt từ chối, và có chỉ báo thị giác phụ trợ.

### 3.4. Nút Next Milestone
- **Yêu cầu chuẩn (`docs/03_SIMULATOR.md:25`, `tasks.csv:T028`)**: Nút "Next Milestone" cho phép người vận hành nhảy thời gian ảo đến mốc sự kiện quan trọng gần nhất (giờ uống thuốc 08:00, nhắc lại 08:02, deadline cảnh báo 08:05) do backend tính toán và đề xuất.
- **Hiện trạng thực tế trong mã nguồn**: **THIẾU HOÀN TOÀN (MISSING)**.
- **Bằng chứng mã nguồn**:
  - Tại `web-simulator/src/App.tsx:371-374`:
    ```tsx
    <div className="clock-buttons">
      {[1, 2, 5].map((minutes) => (
        <button type="button" key={minutes} disabled={!device || busyControl} onClick={() => void advanceClock(minutes)}>
          {busyControl ? 'Đang chạy…' : `+${minutes} phút`}
        </button>
      ))}
      <button className="reset-button" type="button" disabled={!device || busyControl} onClick={() => void resetSimulation()}>
        Đặt lại hộp
      </button>
    </div>
    ```
- **Phân tích đánh giá**: Bộ điều khiển thời gian chỉ cung cấp các bước cộng cố định (`+1 phút`, `+2 phút`, `+5 phút`). Người thuyết trình phải bấm nút thủ công nhiều lần, thiếu nút nhảy thông minh "Next Milestone" để rút ngắn thời gian thao tác khi demo trực tiếp.

### 3.5. Nút Đặt lại hộp (Reset demo kèm Confirmation Dialog)
- **Yêu cầu chuẩn (`docs/03_SIMULATOR.md:25, 57`, `tasks.csv:T028`)**: Nút Reset xóa dữ liệu phiên demo, đưa đồng hồ về `2026-10-09 07:59:00+07:00`; bắt buộc phải có hộp thoại xác nhận (confirmation dialog) để ngăn chặn việc người trình bày bấm nhầm làm hỏng kịch bản demo.
- **Hiện trạng thực tế trong mã nguồn**: **ĐẠT CHUẨN (FULLY COMPLIANT)**.
- **Bằng chứng mã nguồn**:
  - Tại `web-simulator/src/App.tsx:283-301`:
    ```tsx
    async function resetSimulation() {
      if (!token || !window.confirm('Đặt lại hộp sẽ xóa lịch sử thao tác, lần nhắc và cảnh báo của phiên demo hiện tại. Các tài khoản và lịch thuốc vẫn được giữ; nhật ký sẽ ghi thao tác đặt lại. Tiếp tục?')) return
      setBusyControl(true)
      setActionMessage('')
      try {
        const updated = await request<DeviceState>('/api/simulation/reset', token, {
          method: 'POST',
          body: JSON.stringify({ event_uuid: crypto.randomUUID() }),
        })
        setDevice(updated)
        lastReminderEventId.current = 0
        setConnectionError('')
      } catch (error) { ... }
    }
    ```
- **Phân tích đánh giá**: Nút Reset có cơ chế bảo vệ kép: bắt buộc quyền operator và hiển thị hộp thoại `window.confirm` với nội dung giải thích minh bạch về phạm vi dữ liệu bị xóa (xóa lịch sử phiên demo, giữ nguyên lịch thuốc và tài khoản người dùng).

### 3.6. Ô nhập Manual weight reading kèm nhiễu 0.1g
- **Yêu cầu chuẩn (`docs/03_SIMULATOR.md:21, 34`, `tasks.csv:T033`, `docs/07_SECURITY_TESTS.md:FN-04`)**: Ô nhập trọng lượng thủ công dành riêng cho Operator để kiểm thử sai số cân nặng. Khi nhập giảm 0.1g (dưới ngưỡng phát hiện 0.3g), hệ thống vẫn gửi `WEIGHT_READING` nhưng **không được coi là lấy thuốc**, không làm giảm số viên và không đổi trạng thái liều.
- **Hiện trạng thực tế trong mã nguồn**: **THIẾU HOÀN TOÀN (MISSING)**.
- **Bằng chứng mã nguồn**:
  - Quét toàn bộ `App.tsx` không hề có thẻ `<input>` nào cho trọng lượng (chỉ có input email/password tại màn hình đăng nhập).
  - Trọng lượng chỉ hiển thị dưới dạng văn bản tĩnh từ API: `{item.weight_grams.toFixed(1)} g` (`App.tsx:385`).
  - Thao tác thay đổi trọng lượng duy nhất là nút bấm cứng tại `App.tsx:392`:
    ```tsx
    <button className="dispense-button" type="button" disabled={!item.lid_open || item.pill_count <= 0 || busySlot === item.slot || busyControl} onClick={() => void sendEvent(item.slot, 'PILL_DISPENSED')} title={!item.lid_open ? 'Mở nắp ngăn trước' : item.pill_count <= 0 ? 'Ngăn đã hết thuốc mẫu' : undefined}>
      Lấy một viên <span>−0,5 g</span>
    </button>
    ```
- **Phân tích đánh giá**: Không có khả năng giả lập nhiễu 0.1g. Khi người dùng bấm lấy viên, hệ thống ép buộc trừ đúng 0.5g thông qua sự kiện cấm `PILL_DISPENSED`, hoàn toàn tước đoạt khả năng kiểm thử quy tắc dung sai nhiễu cảm biến (Noise Immunity Test).

---

## 4. KIỂM TOÁN TUÂN THỦ HỢP ĐỒNG API VÀ RANH GIỚI PHẦN CỨNG (R2)

### 4.1. Bảng đối chiếu 3 chiều giữa Đặc tả chuẩn, Web Simulator và Backend

| Hạng mục đối chiếu | 1. Đặc tả chuẩn (`docs/05_API_CONTRACT.md`) | 2. Web Simulator thực tế (`web-simulator/src/App.tsx`) | 3. Backend thực tế (`backend/app/main.py`) | Đánh giá sai lệch & Rủi ro |
|---|---|---|---|---|
| **Route tiến đồng hồ ảo** | `POST /api/simulation/advance` (Mục 3, dòng 48) | `POST /api/simulation/clock` (`App.tsx:269`) | `@app.post("/api/simulation/clock")` (`main.py:442`) | **BẤT ĐỒNG ROUTE:** Cả Frontend và Backend tự ý dùng route không có trong đặc tả. Route `/advance` không tồn tại. |
| **Dải giá trị số phút** | `minutes`: số nguyên từ `1` đến `1440` (1 ngày) | Gửi `minutes: 1, 2, 5` (`App.tsx:372`) | `minutes: int = Field(ge=1, le=60)` (`schemas.py:84`) | **SAI LỆCH SCHEMA:** Backend giới hạn tối đa 60 phút, từ chối các bước nhảy lớn (ví dụ nhảy qua đêm). |
| **Định danh ngăn thuốc** | `compartment_id` (số nguyên 1..3) (Mục 1, 3) | `slot: number` (`App.tsx:6, 252`) | `slot: int = Field(ge=1, le=3)` (`schemas.py:78`) | **BẤT ĐỒNG TÊN TRƯỜNG:** Sai lệch thuộc tính dữ liệu xuyên suốt các tầng. |
| **Payload Đặt lại hộp (Reset)** | `{ "confirm": true }` (Mục 3, dòng 50) | `{ event_uuid: UUID }` (`App.tsx:290`) | `SimulationResetInput: { event_uuid: UUID }` (`schemas.py:87`) | **THIẾU TRƯỜNG BẢO VỆ:** Bỏ quên cờ `confirm: true` được chỉ định trong hợp đồng API. |
| **Cấu trúc sự kiện tương tác** | `{ event_uuid, compartment_id, event_type, payload: {} }` | `{ event_uuid, slot, event_type }` (phẳng, không có `payload`) (`App.tsx:252`) | `EventInput: { event_uuid, slot, event_type }` (`schemas.py:76-80`) | **SAI LỆCH CẤU TRÚC:** Thiếu trường `payload` lồng nhau để truyền dữ liệu cảm biến bổ sung. |
| **Sự kiện cảm biến cân nặng** | `WEIGHT_READING: { "weight_g": 4.5 }` (Mục 3, dòng 59) | Gửi `PILL_DISPENSED` (`App.tsx:392`) | Nhận `PILL_DISPENSED` (`schemas.py:79`, `main.py:402`). Từ chối `WEIGHT_READING` (422). | **VI PHẠM RANH GIỚI PHẦN CỨNG:** Client tự ý kết luận hành vi lấy thuốc. |
| **Sự kiện nút xác nhận** | `CONFIRM_PRESSED: { "occurrence_id": 51 }` (Mục 3, dòng 63) | Gửi `DOSE_CONFIRMED` (`App.tsx:393`) | Nhận `DOSE_CONFIRMED` (`schemas.py:79`, `main.py:409`). Từ chối `CONFIRM_PRESSED` (422). | **VI PHẠM ĐIỀU KHOẢN CẤM:** Client tự xác nhận liều thay vì gửi tín hiệu nút bấm vật lý thô. |
| **Thuộc tính đồng hồ trong `/state`** | `virtual_now` (chuỗi ISO 8601 có timezone) | Đọc `device.virtual_clock` (`App.tsx:36, 360`) | Trả về `virtual_clock` (`main.py:185`) | **SAI LỆCH ĐẶT TÊN:** Dùng `virtual_clock` thay vì `virtual_now`. |
| **Định dạng trạng thái đèn LED** | `led_on: boolean` (trạng thái logic) | Đọc `item.led === 'Bật'` (`App.tsx:385`) | Trả về chuỗi tiếng Việt `"Bật"` / `"Tắt"` (`main.py:161, 174`) | **RÒ RỈ UI VÀO API:** Trả về chuỗi bản địa hóa thay vì boolean logic chuẩn. |
| **Bằng chứng cảm biến (`sensor_evidence`)** | `none`, `opened`, `weight_drop` lưu trong DB | Không có | **Model `DoseOccurrence` không có cột `sensor_evidence`** (`models.py:38-45`) | **MẤT DẤU VẾT KIỂM TOÁN Y TẾ:** Không thể xác minh liều thuốc có bằng chứng cảm biến đi kèm. |

---

### 4.2. Phân tích chuyên sâu vi phạm Ranh giới Phần cứng (Hardware Boundary Inversion)

#### A. Đối chiếu văn bản đặc tả cấm đoán
Mục 3 của `docs/05_API_CONTRACT.md` quy định bằng một điều khoản in đậm mang tính bắt buộc:
> *"Do **not** expose write endpoints accepting `ALERT_CREATED`, `CONFIRMED`, `POSSIBLY_RETRIEVED`, or `REMINDER_STARTED` as raw client event."*

Mục 1 & 4 của `docs/03_SIMULATOR.md` xác định nguyên tắc bất biến:
> *"Website thay **thiết bị vật lý**, không phải giả lập API response. Người trình bày tương tác hộp thuốc ảo; web tạo event HTTP và render state **do backend trả về**."*  
> *"Không gửi event 'MEDICATION_RETRIEVED' do client tự kết luận."*

#### B. Thực tế vi phạm trong mã nguồn Backend và Frontend
1. **Frontend Simulator tự định nghĩa và phát sinh sự kiện kết luận nghiệp vụ**:
   Tại `web-simulator/src/App.tsx:43`:
   ```ts
   type EventType = 'LID_OPENED' | 'LID_CLOSED' | 'PILL_DISPENSED' | 'DOSE_CONFIRMED'
   ```
   Tại các nút bấm tương tác (`App.tsx:392-393`):
   - Nút lấy thuốc: gửi trực tiếp `PILL_DISPENSED`.
   - Nút xác nhận: gửi trực tiếp `DOSE_CONFIRMED`.
2. **Backend tiếp nhận sự kiện cấm và tự trừ thuốc ảo**:
   Tại `backend/app/main.py:402-408`:
   ```python
   elif payload.event_type == "PILL_DISPENSED":
       if not compartment["lid_open"]:
           raise HTTPException(status_code=409, detail=f"Hãy mở nắp ngăn {payload.slot} trước khi lấy viên")
       if compartment["pill_count"] <= 0:
           raise HTTPException(status_code=409, detail=f"Ngăn {payload.slot} đã hết thuốc mẫu")
       compartment["pill_count"] -= 1
       compartment["weight_grams"] = round(max(0.0, compartment["weight_grams"] - 0.5), 1)
   ```
   Tại `backend/app/main.py:409-427`:
   ```python
   elif payload.event_type == "DOSE_CONFIRMED":
       ...
       due.confirmed_at = now
       due.status = "confirmed_late" if now - due.scheduled_at >= timedelta(minutes=5) else "confirmed_on_time"
   ```

#### C. Hậu quả kỹ thuật và Rủi ro an toàn y tế
- **Phá vỡ mô hình trừu tượng hóa phần cứng (Hardware Abstraction Breakage)**: Vi điều khiển IoT (ESP32) trong đời thực chỉ có công tắc hành trình, cảm biến cân nặng HX711 và nút bấm cơ học. Vi điều khiển không có trí thông minh nhân tạo và không thể biết được bệnh nhân có "thực sự lấy viên thuốc hay chưa".
- **Rò rỉ logic phân xử (Adjudication Leakage)**: Việc client tự gửi `PILL_DISPENSED` và `DOSE_CONFIRMED` biến Web Simulator từ một "thiết bị ngoại vi mô phỏng" thành một "thực thể đưa ra phán quyết nghiệp vụ".
- **Mất mát dữ liệu kiểm toán y tế**: Do bỏ qua sự kiện `WEIGHT_READING`, backend không thể lưu lại trọng lượng cơ sở khi mở nắp (`open_baseline_weight_mg`). Bảng `DoseOccurrence` không có trường `sensor_evidence`. Bác sĩ hay người thân trên ứng dụng Flutter hoàn toàn không thể biết được người bệnh có thực sự lấy thuốc ra khỏi ngăn (độ sụt trọng lượng >= 0.3g) hay chỉ mở nắp rồi ấn nút xác nhận bừa bãi.

---

### 4.3. Tính lũy thừa (Idempotency), Chu kỳ Polling và Khả năng chịu lỗi Offline

#### A. Tính lũy thừa (Idempotency)
- **Đánh giá**: **ĐẠT CHUẨN (PASS)**.
- **Chứng minh**:
  - Mọi thao tác gửi sự kiện (`App.tsx:252`), tiến đồng hồ (`App.tsx:271`), và reset demo (`App.tsx:290`) đều tự động sinh chuỗi UUID v4 độc bản thông qua API chuẩn `crypto.randomUUID()`.
  - Backend lưu trữ `event_uuid` trong bảng `device_events` với ràng buộc duy nhất `UniqueConstraint("event_uuid")` (`models.py:49`).
  - Tại `main.py:386-391`, backend kiểm tra: nếu nhận lại cùng một `event_uuid` với cùng nội dung, backend trả về kết quả hợp lệ với cờ `"idempotent": True` (không thực thi lặp lại); nếu nhận cùng `event_uuid` nhưng nội dung payload khác, backend ném lỗi `HTTP 409 Conflict`.

#### B. Cơ chế Polling & Giải phóng tài nguyên
- **Đánh giá**: **ĐẠT CHUẨN (PASS)**.
- **Chứng minh**:
  - Triển khai tại `App.tsx:164-186` với chu kỳ `window.setInterval(() => void refresh(), 2000)` (đúng khuyến nghị 1–2 giây trong `05_API_CONTRACT.md` Mục 4).
  - Có cơ chế dọn dẹp timer khi component unmount: `window.clearInterval(timer)` và gắn cờ `alive = false` để hủy bỏ các promise fetch đang dở dang (`App.tsx:184-185`).

#### C. Xử lý ngoại lệ mạng & Tính toàn vẹn Offline
- **Đánh giá**: **ĐẠT XUẤT SẮC (PASS)**.
- **Chứng minh**:
  - Khi ngắt kết nối backend hoặc request thất bại: Badge kết nối chuyển sang nhãn "Mất kết nối" màu đỏ (`App.tsx:344`), xuất hiện Banner cảnh báo màu đỏ (`App.tsx:365`): *"Không thể đồng bộ với backend ... Đang thử kết nối lại mỗi 2 giây."*.
  - **Bảo toàn dữ liệu (No Fake Success)**: Trạng thái `device` cũ được **giữ nguyên vẹn trong bộ nhớ RAM**, tuyệt đối không tự xóa trắng và không cập nhật giao diện giả mạo khi backend từ chối hoặc lỗi mạng.

---

## 5. BÁO CÁO KIỂM TRA TĨNH KHỬ ICON AI SLOP VÀ COMMENT TỰ SỰ (R3)

Quá trình kiểm tra tĩnh toàn diện được thực hiện trên toàn bộ các tệp mã nguồn của thư mục `web-simulator/src/` (`App.tsx`, `App.css`, `index.css`, `main.tsx`).

### 5.1. Bảng kết quả quét Regex tự động

| Hạng mục kiểm tra tĩnh | Mẫu Regex / Lệnh thực thi | Mục tiêu phát hiện | Kết quả quét | Đánh giá |
|---|---|---|:---:|:---:|
| **Icon / Emoji AI Slop** | `rg -n "[✨🤖🧠🪄🚀🔥⚡💡🎉]" src/` | Các emoji thường bị AI sinh mã tùy tiện | **0 matches** | **HOÀN TOÀN SẠCH** |
| **Bình luận tự sự AI** | `rg -i -n "Here we\|As requested\|Let's\|Note: I\|I added\|I have\|TODO\|FIXME\|hack" src/` | Nhật ký làm việc, văn phong đàm thoại hoặc cờ TODO cẩu thả của AI | **0 matches** | **HOÀN TOÀN SẠCH** |
| **Lưu trữ cục bộ** | `rg -i -n "localStorage\|sessionStorage" src/` | Lạm dụng bộ nhớ trình duyệt vi phạm SSoT | **0 matches** | **HOÀN TOÀN SẠCH** |
| **Trích xuất Unicode** | Node.js script quét ký tự ngoài bảng mã ASCII chuẩn | Lập danh mục tất cả ký tự phi chuẩn | **12 ký tự** | **CHẤP NHẬN ĐƯỢC (Cần tối ưu)** |

---

### 5.2. Danh mục ký tự Unicode phát hiện và Đánh giá rủi ro

Toàn bộ 12 ký tự Unicode đặc thù được trích xuất từ mã nguồn gồm: `—`, `↗`, `·`, `♫`, `×`, `…`, `◷`, `↙`, `−`, `↻`, `✓`, `⟲`.

| Ký tự | Mã Unicode | Vị trí xuất hiện tiêu biểu trong code | Mục đích sử dụng | Đánh giá & Khuyến nghị kỹ thuật |
|:---:|:---:|---|---|---|
| `—` | U+2014 | `App.tsx:309, 354, 360` | Gạch ngang Em-dash hiển thị mã máy `SIM—001`, giờ rỗng | Ký tự typographic chuẩn mực trong in ấn, giao diện đẹp. |
| `↗` / `↙` | U+2197 / U+2199 | `App.tsx:325, 390, 405, 416` | Mũi tên định hướng (mở nắp hộp ↗, đóng nắp hộp ↙) | Ký hiệu định hướng tối giản, trực quan, không dùng emoji. |
| `·` | U+00B7 | `App.tsx:354, 359, 410, 424` | Dấu chấm giữa phân cách breadcrumb và metadata | Ký tự typographic chuẩn. |
| `♫` | U+266B | `App.tsx:345, 387`, `App.css:230` | Biểu tượng nốt nhạc cho nút còi báo Buzzer | Glyph ký âm unicode. Trên một số hệ điều hành cũ có thể hiển thị lệch font. **Khuyến nghị thay bằng inline SVG icon.** |
| `×` | U+00D7 | `App.tsx:366` | Dấu nhân đóng banner thông báo lỗi | Ký tự toán học chuẩn, thẩm mỹ tốt hơn chữ 'x' thường. |
| `…` | U+2026 | `App.tsx:367, 372` | Dấu ba chấm biểu thị trạng thái đang tải / đang xử lý | Ký tự typographic chuẩn. |
| `◷` | U+25F7 | `App.tsx:370` (`.console-icon`) | Biểu tượng mặt đồng hồ bảng điều khiển thời gian | Glyph hình học unicode đặc thù. **Khuyến nghị thay bằng inline SVG icon** để hiển thị đồng nhất. |
| `−` | U+2212 | `App.tsx:392, 416` | Dấu trừ toán học biểu thị sụt giảm khối lượng `−0,5 g` | Ký tự toán học chuẩn, chính xác hơn dấu gạch nối hyphen `-`. |
| `↻` / `⟲` | U+21BB / U+27F2 | `App.tsx:410, 416, 420` | Mũi tên xoay biểu thị đồng bộ dữ liệu và đặt lại hộp | Biểu tượng trạng thái trực quan, rõ nghĩa. |
| `✓` | U+2713 | `App.tsx:416` | Dấu tích đã xác nhận uống thuốc trong nhật ký | Biểu tượng trạng thái chuẩn. |

---

### 5.3. Kiểm tra bình luận và Văn phong mã nguồn

Trong toàn bộ thư mục `src/`, chỉ phát hiện **duy nhất 1 dòng bình luận**:
- Tại `web-simulator/src/App.tsx:160`:
  ```tsx
  // Audio is an optional browser feature; the visual alarm remains authoritative.
  ```
- **Đánh giá văn phong**: Bình luận này thể hiện tư duy kiến trúc y tế sâu sắc (khẳng định âm thanh chỉ là tính năng bổ trợ của trình duyệt, cảnh báo thị giác mới là căn cứ thẩm quyền tối thượng), không hề có tính tự sự, đàm thoại hay dấu vết sinh mã tự động cẩu thả của AI. Giao diện sử dụng tiếng Việt chuẩn mực, thuật ngữ y tế nghiêm túc, tạo sự an tâm và tin cậy cho người sử dụng.

---

## 6. KIỂM TRA CHẤT LƯỢNG KỸ THUẬT & QUẢN LÝ TRẠNG THÁI (R4)

### 6.1. Bằng chứng thực thi CLI từ Môi trường Thực tế

Tất cả các lệnh kiểm tra tự động đã được thực thi trực tiếp trên hệ thống với kết quả như sau:

#### 1. Kiểm tra kiểu dữ liệu tĩnh (TypeScript Typecheck)
```powershell
npx tsc -b
```
- **Thư mục thực thi**: `d:\Download\SmartPillBox\web-simulator`
- **Exit Code**: `0`
- **Output**: Hoàn toàn sạch, không có bất kỳ lỗi kiểu dữ liệu nào.

#### 2. Kiểm tra đóng gói Production (Vite Build)
```powershell
npx vite build
```
- **Thư mục thực thi**: `d:\Download\SmartPillBox\web-simulator`
- **Exit Code**: `0`
- **Chi tiết Output**:
  ```text
  vite v8.3.4 building client environment for production...
  transforming...
  ✓ 17 modules transformed.
  rendering chunks...
  computing gzip size...
  dist/index.html                   0.46 kB │ gzip:  0.32 kB
  dist/assets/index-Dt_6UYST.css   20.33 kB │ gzip:  5.62 kB
  dist/assets/index-C9XsQTjJ.js   237.30 kB │ gzip: 74.19 kB
  ✓ built in 479ms
  ```

#### 3. Kiểm tra chất lượng mã nguồn bằng Linter (Oxlint)
```powershell
npx oxlint
```
- **Thư mục thực thi**: `d:\Download\SmartPillBox\web-simulator`
- **Exit Code**: `0`
- **Chi tiết Output**:
  ```text
  Found 0 warnings and 0 errors.
  Finished in 238ms on 3 files with 116 rules using 4 threads.
  ```

#### 4. Kiểm tra biên dịch cú pháp Backend (Python PyCompile)
```powershell
python -m py_compile app/main.py app/schemas.py app/models.py app/seed.py app/database.py
```
- **Thư mục thực thi**: `d:\Download\SmartPillBox\backend`
- **Exit Code**: `0`
- **Output**: 100% cú pháp Python hợp lệ, không có lỗi thụt lề hay lỗi biên dịch.

---

### 6.2. Kiểm toán State Management & Single Source of Truth (SSoT)

- **Trạng thái lưu trữ hoàn toàn trong RAM**:
  - Trạng thái thiết bị được quản lý qua React Hook: `const [device, setDevice] = useState<DeviceState | null>(null)` (`App.tsx:136`).
  - Toàn bộ dữ liệu hiển thị (số viên, khối lượng, trạng thái nắp, đèn LED, còi báo, danh sách lịch, nhật ký sự kiện) đều được cấp nguồn trực tiếp từ backend phản hồi qua `GET /api/simulation/state`.
- **Tuyệt đối không lưu trữ phân xử trong LocalStorage**:
  - Quét chuỗi `localStorage` và `sessionStorage` trên toàn bộ thư mục `src/`: **0 kết quả**.
  - Token xác thực và trạng thái hoạt động tự động giải phóng khi người dùng tắt hoặc làm mới tab trình duyệt, ngăn ngừa triệt để tình trạng lệch pha dữ liệu giữa phiên demo và cơ sở dữ liệu SQLite của backend.
- **Không có Optimistic UI Updates**:
  - Khi người dùng tương tác mở nắp hay lấy thuốc, giao diện không tự ý suy đoán trạng thái thành công. Nút bấm được khóa (`disabled`) kèm thông báo "Đang gửi…". Chỉ khi backend trả về bản ghi `DeviceState` mới nhất với mã HTTP 200, giao diện mới tái kết xuất (re-render) giá trị thực tế.

---

## 7. KẾ HOẠCH KHẮC PHỤC HÀNH ĐỘNG ĐƯỢC (ACTIONABLE REMEDIATION PLAN)

Để đưa Member 3 đạt chuẩn nghiệm thu 100% theo đúng hợp đồng `docs/05_API_CONTRACT.md` và đồng bộ hoàn hảo với Member 2 (Backend) cùng Flutter (Member 4/5), kế hoạch khắc phục được chia thành 3 giai đoạn cụ thể:

### 7.1. Lộ trình triển khai 3 giai đoạn

```
[Giai đoạn 1: Chuẩn hóa Hợp đồng API & Tên trường]
   ├── Đăng ký alias endpoint: POST /api/simulation/advance song song với /clock
   ├── Đổi tên thuộc tính: slot -> compartment_id (hỗ trợ alias ngược)
   ├── Mở rộng payload Reset: hỗ trợ { "confirm": true, "event_uuid": UUID }
   ├── Chuẩn hóa trường thời gian: bổ sung virtual_now song song với virtual_clock
   └── Đổi định dạng đèn: bổ sung led_on: boolean song song với chuỗi hiển thị UI

[Giai đoạn 2: Khôi phục Ranh giới Cảm biến & Cơ chế Phân xử Backend]
   ├── Mở rộng EventInput: hỗ trợ WEIGHT_READING và CONFIRM_PRESSED kèm nested payload
   ├── Simulator gửi WEIGHT_READING: { weight_g } thay vì PILL_DISPENSED
   ├── Simulator gửi CONFIRM_PRESSED: { occurrence_id } thay vì DOSE_CONFIRMED
   ├── Backend tính toán độ sụt cân: so sánh với open_baseline_weight, ngưỡng >= 0.3g
   └── Bổ sung cột sensor_evidence vào model DoseOccurrence trong SQLite

[Giai đoạn 3: Hoàn thiện UI Simulator & Bằng chứng Nghiệm thu]
   ├── Xây dựng Nắp 3D-lite CSS bằng perspective và rotateX(-105deg)
   ├── Thêm nút Next Milestone tính toán mốc thời gian logic kế tiếp
   ├── Thêm cụm điều khiển Manual Weight Input kèm nút test nhiễu +0.1g
   ├── Bổ sung animation nhấp nháy cho LED dot khi có nhắc nhở tích cực
   └── Thay thế các ký tự unicode ♫ và ◷ bằng inline SVG icons chuyên nghiệp
```

---

### 7.2. Ma trận phân công trách nhiệm liên thành viên (Responsibility Matrix)

| Hạng mục công việc | Thành viên phụ trách chính | Thành viên phối hợp / Reviewer | Mức độ ảnh hưởng đến Flutter (M4/M5) |
|---|:---:|:---:|---|
| Bổ sung endpoint `POST /api/simulation/advance` và dải minutes `1..1440` | **Member 2** (Backend) | Member 3 (Web Sim) | Không ảnh hưởng (Flutter không gọi endpoint advance). |
| Chuẩn hóa `compartment_id`, `virtual_now`, `led_on` trong `/state` | **Member 2** (Backend) | Member 3, Member 4 | Rất tích cực: Flutter có thể đọc chung schema chuẩn `compartment_id`. |
| Chuyển đổi `PILL_DISPENSED` sang `WEIGHT_READING: { weight_g }` | **Member 3** (Web Sim) | Member 2 (Backend) | Gián tiếp: Flutter nhận đúng trạng thái `POSSIBLY_RETRIEVED` qua API. |
| Bổ sung cột `sensor_evidence` vào `DoseOccurrence` trong DB | **Member 2** (Backend) | Member 1, Member 5 | Rất lớn: Màn hình lịch sử liều của Flutter hiển thị đúng bằng chứng cảm biến. |
| Chuyển đổi `DOSE_CONFIRMED` sang `CONFIRM_PRESSED: { occurrence_id }` | **Member 3** (Web Sim) | Member 2 (Backend) | Đồng bộ: Cả Flutter và Web Sim đều gửi thao tác xác nhận chuẩn mực. |
| Hiện thực Nắp 3D-lite CSS, Next Milestone, Manual Weight Input 0.1g | **Member 3** (Web Sim) | Member 5 (QA Lead) | Thuần túy UI Web Simulator phục vụ bài thuyết trình trực tiếp. |

---

### 7.3. Mẫu Code Snippet đề xuất khắc phục cụ thể

#### 1. Backend: Cập nhật Schema & Endpoint tiếp nhận sự kiện thô (`backend/app/schemas.py`)
```python
# Cập nhật trong backend/app/schemas.py
from pydantic import BaseModel, Field
from typing import Literal, Any
from uuid import UUID

class EventInput(BaseModel):
    event_uuid: UUID
    compartment_id: int = Field(default=1, ge=1, le=3, alias="slot")
    event_type: Literal[
        "LID_OPENED", 
        "LID_CLOSED", 
        "WEIGHT_READING", 
        "CONFIRM_PRESSED", 
        "PILL_DISPENSED",   # Giữ lại tạm thời để tương thích ngược
        "DOSE_CONFIRMED"    # Giữ lại tạm thời để tương thích ngược
    ]
    payload: dict[str, Any] = Field(default_factory=dict)

    class Config:
        populate_by_name = True

class ClockAdvanceInput(BaseModel):
    event_uuid: UUID | None = None
    minutes: int = Field(ge=1, le=1440)  # Mở rộng dải giá trị lên 1440 phút

class SimulationResetInput(BaseModel):
    event_uuid: UUID | None = None
    confirm: bool = Field(default=True)
```

#### 2. Backend: Bổ sung cột `sensor_evidence` vào Model (`backend/app/models.py`)
```python
# Cập nhật trong backend/app/models.py
class DoseOccurrence(Base):
    __tablename__ = "dose_occurrences"
    id: Mapped[int] = mapped_column(primary_key=True)
    schedule_id: Mapped[int] = mapped_column(ForeignKey("medication_schedules.id"), index=True)
    scheduled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="scheduled")
    # Bổ sung trường sensor_evidence lưu vết kiểm toán y tế
    sensor_evidence: Mapped[str] = mapped_column(String(20), default="none")  # 'none', 'opened', 'weight_drop'
```

#### 3. Frontend Simulator: Chuyển đổi sang gửi sự kiện cảm biến thô (`web-simulator/src/App.tsx`)
```tsx
// Cập nhật các hàm gửi sự kiện phần cứng trong web-simulator/src/App.tsx

// 1. Thao tác lấy thuốc: gửi tín hiệu cảm biến cân nặng thô WEIGHT_READING
async function takePill(slot: number, currentWeight: number) {
  if (!token) return
  const newWeight = Math.max(0.0, Math.round((currentWeight - 0.5) * 10) / 10)
  await sendHardwareEvent(slot, 'WEIGHT_READING', { weight_g: newWeight })
}

// 2. Thao tác thử nghiệm nhiễu cảm biến: gửi thay đổi 0.1g (không làm mất thuốc)
async function injectWeightNoise(slot: number, currentWeight: number, delta: number) {
  if (!token) return
  const simulatedNoise = Math.max(0.0, Math.round((currentWeight + delta) * 10) / 10)
  await sendHardwareEvent(slot, 'WEIGHT_READING', { weight_g: simulatedNoise })
}

// 3. Thao tác bấm nút xác nhận vật lý: gửi CONFIRM_PRESSED kèm occurrence_id
async function confirmPhysicalButton(slot: number, occurrenceId: number | null) {
  if (!token || !occurrenceId) return
  await sendHardwareEvent(slot, 'CONFIRM_PRESSED', { occurrence_id: occurrenceId })
}

// Hàm gửi sự kiện phần cứng chuẩn theo API Contract v1
async function sendHardwareEvent(compartmentId: number, eventType: string, payload: Record<string, unknown> = {}) {
  setBusySlot(compartmentId)
  setActionMessage('')
  try {
    const updated = await request<DeviceState>('/api/simulation/events', token, {
      method: 'POST',
      body: JSON.stringify({
        event_uuid: crypto.randomUUID(),
        compartment_id: compartmentId,
        slot: compartmentId, // hỗ trợ cả 2 tên trường
        event_type: eventType,
        payload,
      }),
    })
    setDevice(updated)
    setConnectionError('')
  } catch (error) {
    if (error instanceof ApiRequestError) setActionMessage(error.message)
    else setConnectionError(error instanceof Error ? error.message : 'Lỗi gửi tín hiệu phần cứng')
  } finally {
    setBusySlot(null)
  }
}
```

#### 4. Frontend Simulator: Hiện thực Nắp 3D-lite CSS (`web-simulator/src/App.css`)
```css
/* Container tạo không gian phối cảnh 3D */
.lid-3d-viewport {
  perspective: 600px;
  width: 100%;
  height: 48px;
  margin-bottom: 12px;
}

/* Khối nắp hộp thuốc thực hiện xoay trong không gian 3D */
.lid-3d-plate {
  width: 100%;
  height: 100%;
  border-radius: 8px;
  background: linear-gradient(180deg, #d8ddd5 0%, #b8c0b4 100%);
  border: 1px solid #9ea89a;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.08);
  transform-origin: top center;
  transform-style: preserve-3d;
  transition: transform 0.45s cubic-bezier(0.34, 1.56, 0.64, 1), background-color 0.3s;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 11px;
  font-weight: 600;
  color: #434c44;
}

/* Trạng thái nắp mở lật ngược lên trên theo trục X */
.compartment-card.lid-open .lid-3d-plate {
  transform: rotateX(-110deg);
  background: linear-gradient(180deg, #f0dfd0 0%, #d9b89d 100%);
  border-color: #ba9372;
  box-shadow: 0 8px 16px rgba(149, 91, 57, 0.2);
  color: #8c4c23;
}

/* Animation nhấp nháy cho đèn LED dot */
@keyframes led-blinking {
  0%, 100% {
    background: #cbd0c7;
    box-shadow: none;
  }
  50% {
    background: #a4bd53;
    box-shadow: 0 0 0 4px #edf3da, 0 0 8px #a4bd53;
  }
}

.led-blinking {
  animation: led-blinking 1s ease-in-out infinite;
}
```

---

## 8. KẾT LUẬN CHUNG

Bộ mô phỏng Web IoT Simulator do **Thành viên 3 (M3)** xây dựng là một sản phẩm phần mềm có **chất lượng kỹ thuật nền tảng rất cao**: mã nguồn TypeScript chặt chẽ, biên dịch và linting hoàn toàn sạch (0 lỗi, 0 cảnh báo), thiết kế giao diện thanh lịch chuẩn y tế, quản lý trạng thái Single Source of Truth tuyệt đối tuân thủ (không lạm dụng LocalStorage), xử lý âm thanh Web Audio API xuất sắc và khả năng phục hồi khi mất kết nối mạng rất kiên cường.

Tuy nhiên, sản phẩm đang mắc phải **sai phạm kiến trúc cốt lõi về Ranh giới Phần cứng (Hardware Boundary Inversion)** và **lệch chuẩn hợp đồng API**. Web Simulator hiện đang hành xử như một giao diện nghiệp vụ tự phán quyết liều uống thay vì một thiết bị mô phỏng ngoại vi phần cứng thuần túy, dẫn đến việc mất mát dữ liệu bằng chứng cảm biến `sensor_evidence` trong cơ sở dữ liệu.

Báo cáo kiểm toán này cung cấp cơ sở đối chiếu vững chắc và giải pháp khắc phục chi tiết theo 3 giai đoạn. Khi nhóm phát triển thực hiện chuẩn hóa theo kế hoạch khắc phục trên, hệ thống Smart Pill Box sẽ đạt được tính toàn vẹn kiến trúc hoàn hảo, đảm bảo tính pháp lý y tế và kết nối đồng bộ 100% giữa Web Simulator của M3, Backend của M1/M2 và ứng dụng di động Flutter của M4/M5.
