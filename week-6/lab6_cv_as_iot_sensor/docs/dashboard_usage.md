# Hướng dẫn sử dụng Dashboard Lab 6

Dashboard nằm tại:

```text
http://127.0.0.1:8000/
```

Chạy backend:

```bash
uvicorn app:app --reload --host 0.0.0.0 --port 8000
```

## 1. Kiểm tra trạng thái

Ở góc trên có các nhãn trạng thái (badges):

- `WebSocket`: Trạng thái kết nối WebSocket thời gian thực (connected / reconnecting).
- `Detection`: Trạng thái của bộ phát hiện vật thể (ONNX / contour fallback / tắt).
- `MQTT`: Trạng thái kết nối đến MQTT broker (connected / tắt).
- `Server`: Trạng thái phản hồi của backend.

Dưới đó là các thẻ số liệu thống kê (metrics):
- `Ảnh đã ghi metadata`: Tổng số ảnh đã ghi nhận thông tin trong bảng `images`.
- `Event đã sinh`: Tổng số sự kiện vận hành được tạo trong bảng `events`.
- `Detection`: Tổng số lượt phát hiện vật thể trong bảng `detections`.

Nếu API offline, kiểm tra terminal chạy `uvicorn` và mở lại trang.

Dashboard có nút `Chế độ sáng` / `Chế độ tối` ở đầu trang. Khi demo trong lớp học hoặc qua máy chiếu, nên dùng chế độ sáng để bảng và ảnh dễ quan sát hơn. Lựa chọn theme được lưu trong trình duyệt.

Ngay dưới phần tiêu đề có thanh tóm tắt pipeline gồm bốn bước:

1. Camera hoặc upload.
2. Raw image.
3. Processed image.
4. Metadata và event.

Thanh này giúp giải thích nhanh camera đang đóng vai trò như một IoT sensor: dữ liệu đi vào, được lưu, được xử lý, rồi được ghi log.

## 2. Bật live camera stream

1. Nhập `0` vào ô `Camera source` để dùng camera laptop.
2. Nếu dùng IP camera, nhập URL camera hoặc RTSP stream.
3. Bấm `Bật stream`.
4. Bấm `Dừng stream` khi muốn ngắt stream trên dashboard.

Nếu không mở được camera thật, backend sẽ tự dùng simulated frame để lab vẫn demo được.

## 3. Chụp snapshot

1. Bấm `Snapshot`.
2. Dashboard sẽ gọi API `/snapshot`.
3. Kết quả sẽ hiển thị ở:
   - Preview ảnh gốc mới nhất.
   - Preview ảnh xử lý bốn bước.
   - Bảng metadata.
   - Bảng visual event.
   - Khung JSON response.

Ảnh gốc được lưu ở:

```text
data/raw_images/
```

Ảnh xử lý được lưu ở:

```text
data/processed_images/
```

## 4. Upload image

1. Chọn một file ảnh ở khu vực `Upload image`.
2. Kiểm tra tên file và dung lượng hiển thị dưới ô chọn file.
3. Bấm `Upload`.
4. Dashboard sẽ gọi API `/upload-image`.
5. Ảnh được xử lý qua cùng pipeline với snapshot.

Cách này hữu ích khi máy không có camera hoặc cần demo bằng ảnh mẫu.

## 5. Object detection

Khu vực `Upload image` có thêm hai nút:

- `Detect JSON`: gọi API `/detect-objects` và hiển thị danh sách object dưới dạng JSON/bảng.
- `Detect annotated`: gọi API `/detect-objects-annotated`, vẽ bounding box và hiển thị ảnh annotated.

Kết quả nằm ở khu vực `Object detection result`:

- `image_id`
- `event_type`
- `severity`
- `decision`
- `class_name`
- `confidence`
- `bbox`

Nếu dashboard hiển thị `detector_mode = fallback_contour`, nghĩa là chưa có file `models/yolov8n.onnx`. Đây là fallback để lab vẫn chạy được. Khi thêm model ONNX, backend sẽ ưu tiên YOLO.

## 6. Record video

1. Bấm `Record video 5s`.
2. Dashboard sẽ gọi API `/record-video?seconds=5`.
3. Trong lúc ghi, trạng thái operation chuyển sang loading.
4. Sau khi hoàn tất, video được lưu ở:

```text
data/videos/
```

Record video sinh event `VIDEO_RECORDED`, nhưng không sinh metadata ảnh vì output chính là video.

## 7. Motion capture

1. Bấm `Motion capture`.
2. Backend quan sát frame trong khoảng 8 giây.
3. Hệ thống chọn frame có thay đổi lớn nhất.
4. Frame đó được lưu như ảnh gốc và đi qua pipeline xử lý ảnh.
5. Dashboard hiển thị thêm event:
   - `MOTION_DETECTED` nếu motion score vượt ngưỡng.
   - `NO_SIGNIFICANT_MOTION` nếu chưa có chuyển động đáng kể.

Motion capture thường tạo hai event:

- Event xử lý ảnh, ví dụ `IMAGE_PROCESSED`.
- Event motion, ví dụ `MOTION_DETECTED`.

## 8. Đọc bảng metadata và event

Bảng metadata cho biết ảnh đến từ đâu và có đặc tính gì:

- `image_id`
- `timestamp`
- `source`
- `width`
- `height`
- `brightness`
- `status`

Bảng visual event cho biết hệ thống diễn giải điều gì từ ảnh/video:

- `event`
- `timestamp`
- `severity`
- `score`
- `explanation`
- `action`

Ví dụ:

- `LOW_LIGHT`: ảnh quá tối, cần cải thiện ánh sáng.
- `IMAGE_PROCESSED`: ảnh đã được lưu và xử lý.
- `VIDEO_RECORDED`: video đã ghi xong.
- `MOTION_DETECTED`: phát hiện chuyển động.
- `OBJECTS_DETECTED`: YOLO phát hiện object.
- `OBJECT_DETECTION_FALLBACK`: fallback contour được dùng vì model chưa sẵn sàng.

## 9. Khi demo lab

Thứ tự demo gợi ý:

1. Chọn chế độ sáng nếu demo trên máy chiếu.
2. Chỉ vào thanh pipeline 4 bước để giới thiệu luồng dữ liệu.
3. Bật stream để chứng minh camera là sensor.
4. Bấm snapshot để tạo một mẫu dữ liệu ảnh.
5. Quan sát raw image và processed image.
6. Giải thích metadata khác event.
7. Upload một ảnh khác để so sánh pipeline.
8. Bấm `Detect annotated` để giới thiệu bước chuẩn bị cho Lab 7 object detection.
9. Bấm motion capture để tạo visual event.
10. Mở database SQLite `outputs/lab6.db` (bảng `images`, `events`, `detections`) để chỉ ra dữ liệu đã được lưu trữ có cấu trúc đầy đủ.
