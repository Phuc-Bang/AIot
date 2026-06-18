# Hướng dẫn Khởi động lại Toàn bộ Hệ thống (Lab 6 & PhoneGuard)

Tài liệu này hướng dẫn cách chạy độc lập hoặc chạy đồng thời cả hai dự án **Lab 6 (Computer Vision as IoT Sensor)** và **PhoneGuard AIoT** mà không lo xung đột cổng dịch vụ.

---

## 🛠️ Trạng thái Hệ thống Hiện tại
* **Tất cả các tiến trình nền và Docker Container đã được tắt hoàn toàn.**
* Các cổng dịch vụ được thiết kế tránh xung đột:
  * **Port 8001**: Dành riêng cho Backend Lab 6.
  * **Port 8005**: Dành riêng cho Backend PhoneGuard AIoT (hoặc Port 8000 trong container Docker).
  * **Port 5173 (hoặc 3000)**: Dành cho PhoneGuard React Frontend.
  * **Port 8501**: Dành cho Streamlit Dashboard.

---

## 1. Dự án 1: Lab 6 (Computer Vision as IoT Sensor)
Dự án này thu thập dữ liệu chuyển động từ camera (hoặc camera giả lập) và hiển thị qua giao diện dashboard tối giản (được tối ưu hóa Light/Dark theme theo phong cách Swiss Industrial Print).

### Bước 1: Kích hoạt Môi trường Ảo (venv) & Chạy Backend
Mở một cửa sổ Terminal mới (PowerShell) tại thư mục dự án và chạy:
```powershell
cd "e:\AIoT\Home-Work\week-6\lab6_cv_as_iot_sensor"
# Kích hoạt venv
.venv\Scripts\activate
# Khởi chạy server FastAPI trên cổng 8001
uvicorn app:app --host 0.0.0.0 --port 8001 --reload
```

### Bước 2: Khởi chạy Giao diện Frontend
* Chỉ cần click đúp vào file [index.html](file:///e:/AIoT/Home-Work/week-6/lab6_cv_as_iot_sensor/index.html) để mở trực tiếp trên trình duyệt.
* **Giao diện Light/Dark Theme:** Sử dụng nút chuyển đổi giao diện ở góc trên bên phải màn hình để thay đổi phong cách (Swiss Industrial / Dark Mode). Lựa chọn của bạn sẽ được lưu tự động bằng `localStorage`.

---

## 2. Dự án 2: PhoneGuard AIoT
Dự án giám sát tình trạng thiết bị Android (pin, gia tốc, mạng) và phát hiện bất thường.

### Cách A: Khởi chạy nhanh bằng Docker Compose (Khuyên dùng)
Cách này sẽ chạy cả Backend FastAPI và Frontend React trong các Docker container độc lập.
```powershell
cd "e:\AIoT\Home-Work\phoneguard-aiot"
# Build và chạy ngầm các container
docker compose up --build -d
```
* **Dashboard React:** Truy cập tại [http://localhost:3000](http://localhost:3000).
* **Kiểm tra trạng thái:** Dùng lệnh `docker ps` hoặc `docker compose logs -f`.

---

### Cách B: Khởi chạy Thủ công từng Thành phần (Dành cho Debug)
Nếu muốn chạy trực tiếp trên môi trường Windows mà không qua Docker:

#### 1. Chạy Backend FastAPI (Port 8005)
Mở một cửa sổ Terminal mới:
```powershell
cd "e:\AIoT\Home-Work\phoneguard-aiot\backend"
# Kích hoạt venv
.venv\Scripts\activate
# Khởi chạy FastAPI trên cổng 8005
uvicorn app.main:app --host 0.0.0.0 --port 8005 --reload
```
* **API Docs:** Truy cập [http://localhost:8005/docs](http://localhost:8005/docs).

#### 2. Chạy Phone Web Client (Mô phỏng điện thoại Android)
* Mở trực tiếp file [index.html](file:///e:/AIoT/Home-Work/phoneguard-aiot/phone-web/index.html) trong trình duyệt (hoặc mở trên điện thoại kết nối cùng mạng Wi-Fi với PC).
* **Cấu hình URL:** Nhập URL Backend tương ứng (ví dụ: `http://localhost:8005` nếu chạy trên cùng máy tính, hoặc `http://<IP_MÁY_TÍNH>:8005` nếu chạy trên điện thoại).
* Nhập **Device ID** và nhấn **Start Sending** để bắt đầu gửi dữ liệu telemetry.

#### 3. Chạy Dashboard React Frontend (Vite)
Mở một cửa sổ Terminal mới:
```powershell
cd "e:\AIoT\Home-Work\phoneguard-aiot\frontend"
# Cài đặt thư viện nếu chạy lần đầu
npm install
# Khởi chạy Vite Dev Server
npm run dev
```
* Truy cập Dashboard tại [http://localhost:5173](http://localhost:5173).

#### 4. Chạy Streamlit Dashboard (Tùy chọn)
Mở một cửa sổ Terminal mới:
```powershell
cd "e:\AIoT\Home-Work\phoneguard-aiot\dashboard"
# Kích hoạt venv (sử dụng chung venv của backend hoặc venv riêng)
..\backend\.venv\Scripts\activate
# Khởi chạy Streamlit
streamlit run streamlit_app.py --server.port 8501
```
* Truy cập Dashboard tại [http://localhost:8501](http://localhost:8501).

---

## 🧹 Lệnh tắt nhanh (Dọn dẹp hệ thống)
* **Để tắt các Server chạy thủ công (Uvicorn / Streamlit / Vite):** Nhấn tổ hợp phím `Ctrl + C` trong các cửa sổ terminal tương ứng.
* **Để tắt Docker Compose:**
  ```powershell
  cd "e:\AIoT\Home-Work\phoneguard-aiot"
  docker compose down
  ```
