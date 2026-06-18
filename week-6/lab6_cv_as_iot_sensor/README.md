# Lab 6 - Computer Vision as IoT Sensor

Lab này đưa camera/ảnh vào hệ thống AIoT như một cảm biến trực quan. Gốc Lab 6 dùng OpenCV processing cơ bản để chạy live stream, chụp ảnh, ghi video, phát hiện chuyển động, xử lý ảnh, ghi metadata, sinh event và quan sát trên dashboard HTML.

Bản nâng cấp hiện tại phát hiện **người đang chuyển động** bằng OpenCV built-in: MOG2/KNN/simple tạo motion mask và HOG people detector xác nhận bbox người. Không dùng YOLO, ONNX, MediaPipe, Ultralytics hoặc model tải ngoài.

## Cấu trúc file chính

```text
app.py              # backend FastAPI: stream, snapshot, video, person motion, preprocess, metadata, event
index.html          # giao diện dashboard: stream, upload ảnh, quan sát ảnh/metadata/event
run_lab6_demo.py    # chạy thử nhanh không cần camera thật
```

## Chạy nhanh

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS/Linux/WSL
source .venv/bin/activate
pip install -r requirements.txt
python run_lab6_demo.py
uvicorn app:app --reload --host 0.0.0.0 --port 8000
```

Mở trình duyệt:

```text
http://127.0.0.1:8000/
http://127.0.0.1:8000/docs
```

## Cần quan sát sau khi chạy

- `data/raw_images/`: ảnh gốc từ upload/snapshot/motion.
- `data/processed_images/`: ảnh tổng hợp bốn bước xử lý.
- `data/videos/`: video ngắn ghi từ camera hoặc stream mô phỏng.
- `outputs/lab6.db`: database SQLite lưu trữ thông tin camera, metadata ảnh, events và detections.
- `outputs/lab6.log`: file log hoạt động của hệ thống.
- Dashboard tại `/`: live stream, ảnh gốc, ảnh xử lý, bảng metadata và event.

## Phát hiện người đang chuyển động

Luồng motion nâng cấp:

```text
camera frame
→ MOG2/KNN/simple motion mask
→ lọc nhiễu bằng morphology
→ chọn best frame theo motion score
→ OpenCV HOG phát hiện person bbox
→ kiểm tra pixel motion nằm trong bbox người
→ chỉ lưu ảnh khi PERSON_MOTION_CONFIRMED
```

Nếu không xác nhận được người đang chuyển động, hệ thống ghi event `NO_PERSON_MOTION` kèm `reason_code` và không lưu ảnh thường. Bật `debug=true` ở `/motion-capture` để lưu frame/mask/annotated/json vào `data/debug_frames/`.

Hạn chế của HOG: dễ bỏ sót người bị che khuất, đang ngồi, quá gần camera, ánh sáng kém, ảnh mờ hoặc góc nhìn lạ.
