# 06. Triển Khai Với Docker & Docker Compose (Docker Deployment)

Triển khai container hóa (Containerization) là bước quan trọng nhất để đưa dịch vụ AIoT lên môi trường doanh nghiệp Cloud/Edge Server ổn định.

---

## 1. Giải Mã Dockerfile (Công Thức Xây Dựng Image)

File `Dockerfile` quy định các bước biên dịch và tạo lập Docker Image từ trên xuống dưới:

* **`FROM python:3.11-slim`**: Chọn hệ điều hành Linux siêu rút gọn Debian có sẵn Python 3.11 để giảm kích thước lưu đĩa.
* **`ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 ...`**: Cấu hình biến môi trường giúp Python không sinh file `.pyc` dư thừa và in logs trực tiếp ra màn hình terminal ngay lập tức để dễ theo dõi.
* **`WORKDIR /app`**: Thiết lập thư mục làm việc mặc định trong container là `/app`.
* **`RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*`**: Cài đặt thêm thư viện mạng `curl` hỗ trợ chạy test và script giám sát.
* **`COPY requirements.txt .` & `RUN pip install --no-cache-dir -r requirements.txt`**: Cài đặt thư viện Python sạch sẽ, không lưu cache để tối ưu dung lượng.
* **`COPY app/ app/` ...**: Sao chép toàn bộ mã nguồn của bạn vào trong container.
* **`EXPOSE 8000`**: Khai báo cổng ứng dụng `8000` mà container sẽ mở.
* **`CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]`**: Khởi chạy ứng dụng bằng Uvicorn lắng nghe trên cổng `8000` của tất cả các dải IP nội bộ.

---

## 2. Giải Mã docker-compose.yml (Điều Phối Vận Hành)

Tệp Compose giúp điều phối việc chạy container dễ dàng thông qua các tệp cấu hình thay vì viết các dòng lệnh `docker run` dài:

```yaml
services:
  aiot-api:
    build: .
    container_name: lab5-aiot-api
    ports:
      - "8001:8000"
    environment:
      - MODEL_DIR=/app/models
      - OUTPUT_DIR=/app/outputs
      - VISION_MODEL_PATH=/app/models/vision/squeezenet1.1-7.onnx
      - VISION_LABELS_PATH=/app/models/vision/imagenet_classes.txt
    volumes:
      - ./outputs:/app/outputs
      - ./models/vision:/app/models/vision
    restart: unless-stopped
```

### Các cấu hình quan trọng cần lưu ý:
1. **Port Mapping (`"8001:8000"`)**:
   * **Cú pháp**: `"[Host Cổng]:[Container Cổng]"`
   * **Ý nghĩa**: Ánh xạ cổng `8001` của máy thật (máy host của bạn) vào cổng `8000` nội bộ của Docker container. Mọi request gửi tới cổng `8001` của máy bạn sẽ được chuyển tiếp vào cổng `8000` của dịch vụ FastAPI chạy trong container. Thiết lập này giúp bạn tránh xung đột với ứng dụng `cardioguard-ai` đang chạy cổng `8000`.
2. **Volume Mapping (Mount ổ đĩa ảo)**:
   * **`./outputs:/app/outputs`**: Đồng bộ thư mục ghi log. Tất cả các file log cảm biến (`service_log.csv`) và log ảnh (`vision_inference_log.csv`) ghi bởi container sẽ được đồng bộ lập tức ra đĩa cứng vật lý của bạn. Nếu container bị lỗi hay bị xóa, **dữ liệu log trên máy host vẫn được bảo toàn**.
   * **`./models/vision:/app/models/vision`**: Chia sẻ tệp mô hình. Giúp container đọc trực tiếp file mô hình ONNX từ máy host mà không cần phải đóng gói file mô hình nặng đó vào bên trong Image, giúp Image của bạn cực kỳ nhẹ và build nhanh hơn.
3. **Restart Policy (`restart: unless-stopped`)**:
   * Tự động khởi động lại container nếu nó gặp lỗi crash, trừ khi người dùng chủ động tắt nó. Đảm bảo tính sẵn sàng cao của dịch vụ AIoT.

---

## 3. Các Lệnh Điều Khiển Vận Hành Docker

Mở Terminal tại thư mục chứa tệp `docker-compose.yml` và sử dụng các lệnh sau:

* **Khởi chạy container ở chế độ chạy nền (Detached mode)**:
  ```bash
  docker compose up -d
  ```
* **Khởi chạy kèm bắt buộc build lại Image khi có thay đổi code**:
  ```bash
  docker compose up -d --build
  ```
* **Xem logs hoạt động trực tiếp của container**:
  ```bash
  docker compose logs -f
  ```
* **Tắt dịch vụ và dọn dẹp các tài nguyên mạng ảo ảo**:
  ```bash
  docker compose down
  ```
* **Kiểm tra trạng thái container đang chạy**:
  ```bash
  docker compose ps
  ```
