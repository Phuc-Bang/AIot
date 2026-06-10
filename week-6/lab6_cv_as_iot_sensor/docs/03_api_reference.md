# API Reference Lab 6

Base URL khi chạy local:

```text
http://127.0.0.1:8000
```

---

## 1. Web Page & Health Endpoints

### `GET /`
- **Mô tả**: Trả về file giao diện `index.html` (Dashboard chính).
- **Output**: HTML page.

### `GET /dashboard`
- **Mô tả**: Alias của `GET /`, trả về giao diện dashboard `index.html`.
- **Output**: HTML page.

### `GET /health`
- **Mô tả**: Kiểm tra trạng thái hoạt động của hệ thống backend.
- **Output mẫu**:
  ```json
  {
    "status": "ok",
    "lab": "Lab 6 Enhanced - Computer Vision as IoT Sensor",
    "version": "2.0.0",
    "cameras": 1,
    "websockets": 0,
    "detection": false,
    "mqtt": false
  }
  ```

---

## 2. Camera Management Endpoints

### `GET /cameras`
- **Mô tả**: Lấy danh sách các camera đang được đăng ký trong hệ thống.
- **Output mẫu**:
  ```json
  [
    {
      "camera_id": "cam_xxxxxx",
      "source": "0",
      "label": "Camera mặc định",
      "status": "online",
      "last_seen": "2026-06-09T22:15:00"
    }
  ]
  ```

### `POST /cameras`
- **Mô tả**: Đăng ký thêm một camera mới.
- **Query Parameters**:
  - `source` (bắt buộc): Đường dẫn nguồn (ví dụ: `0` cho webcam máy tính, hoặc RTSP/HTTP URL).
  - `label` (không bắt buộc): Tên định danh camera.
- **Output**: Thông tin camera vừa đăng ký.

### `DELETE /cameras/{camera_id}`
- **Mô tả**: Xóa (hủy đăng ký) một camera.
- **Output**: `{"status": "removed", "camera_id": "..."}`

---

## 3. Core Processing & Action Endpoints

### `POST /upload-image`
- **Mô tả**: Upload một file ảnh để đẩy qua image pipeline và nhận kết quả phân tích.
- **Body**: File ảnh (`multipart/form-data`).
- **Query Parameters**:
  - `device_id` (mặc định: `upload_client`): ID thiết bị gửi ảnh.
  - `camera_id` (không bắt buộc): ID camera liên kết.
  - `run_detection` (mặc định: `false`): Chạy phát hiện vật thể (ONNX YOLO / Contours fallback).
- **Database updates**:
  - Chèn bản ghi metadata vào bảng `images`.
  - Sinh sự kiện trong bảng `events`.
  - (Tùy chọn) Chèn kết quả phát hiện vật thể vào bảng `detections`.

### `GET /snapshot`
- **Mô tả**: Chụp một frame từ camera chỉ định (hoặc simulated frame nếu không mở được camera), chạy qua image pipeline.
- **Query Parameters**:
  - `camera_id` (không bắt buộc): ID camera muốn snapshot.
  - `source` (không bắt buộc): Nếu không truyền `camera_id`, hệ thống sẽ tìm/đăng ký camera theo `source`.
  - `run_detection` (mặc định: `false`): Chạy phát hiện vật thể.

### `GET /record-video`
- **Mô tả**: Ghi một video ngắn dài `seconds` giây từ camera chỉ định.
- **Query Parameters**:
  - `camera_id` (không bắt buộc): ID camera ghi hình.
  - `seconds` (mặc định: `5`, từ 1-30): Thời lượng video.
- **Database updates**:
  - Ghi sự kiện loại `VIDEO_RECORDED` vào bảng `events`.

### `GET /motion-capture`
- **Mô tả**: Theo dõi chuyển động bằng MOG2/Frame difference, trích xuất frame có độ chuyển động cao nhất để lưu và phân tích qua pipeline.
- **Query Parameters**:
  - `camera_id` (không bắt buộc): ID camera theo dõi.
  - `seconds` (mặc định: `8`): Thời lượng theo dõi.
  - `method` (mặc định: `mog2`): Phương pháp trừ nền (`mog2` hoặc `simple`).
  - `min_area` (mặc định: `800`): Diện tích contour tối thiểu để xem là chuyển động.

### `GET /video_feed`
- **Mô tả**: Stream live MJPEG của camera chỉ định phục vụ hiển thị lên giao diện web.
- **Query Parameters**:
  - `camera_id` / `source` (không bắt buộc).
- **Output**: Stream dạng `multipart/x-mixed-replace`.

---

## 4. Database Queries & Stats Endpoints

### `GET /metadata`
- **Mô tả**: Truy vấn danh sách lịch sử metadata ảnh từ SQLite.
- **Query Parameters**:
  - `limit` (mặc định: `20`, tối đa `100`).
  - `camera_id` (không bắt buộc): Lọc theo camera.

### `GET /events`
- **Mô tả**: Truy vấn lịch sử sự kiện (event logs) từ SQLite.
- **Query Parameters**:
  - `limit` (mặc định: `20`).
  - `event_type` (không bắt buộc): Lọc theo loại sự kiện.
  - `severity` (không bắt buộc): Lọc theo độ nghiêm trọng.

### `GET /detections`
- **Mô tả**: Truy vấn lịch sử phát hiện vật thể từ SQLite.
- **Query Parameters**:
  - `limit` (mặc định: `20`).
  - `label` (không bắt buộc): Lọc theo nhãn vật thể.

### `GET /latest`
- **Mô tả**: Lấy bản ghi metadata và event mới nhất cùng các đường dẫn ảnh tương ứng để cập nhật UI nhanh chóng.
- **Output**: JSON chứa metadata, event và tổng số lượng bản ghi trong DB.

### `GET /stats`
- **Mô tả**: Trả về thống kê tổng hợp (tổng số lượng ảnh, sự kiện, phát hiện vật thể, tần suất các loại event/vật thể).

---

## 5. Configuration Endpoints

### `GET /config`
- **Mô tả**: Lấy cấu hình YAML hiện tại của hệ thống.

### `PUT /config`
- **Mô tả**: Cập nhật nóng các tham số cấu hình (chẳng hạn như danh sách filters, threshold_value, canny_low, canny_high, resize_width, resize_height).

---

## 6. Real-time & Static Serving

### `WebSocket /ws`
- **Mô tả**: Cung cấp kênh truyền thông hai chiều thời gian thực (đẩy sự kiện tự động khi chụp ảnh, phát hiện chuyển động).

### `GET /files/{file_path:path}`
- **Mô tả**: Endpoint phục vụ các static files (chỉ cho phép các file nằm dưới thư mục `data/` như ảnh gốc, ảnh xử lý và video) để bảo mật.
