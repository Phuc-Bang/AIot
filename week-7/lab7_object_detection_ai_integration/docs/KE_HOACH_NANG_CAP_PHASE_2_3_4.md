# Kế hoạch nâng cấp chi tiết — Phase 2, 3, 4

Tài liệu này là bản thiết kế kỹ thuật (spec) để hoàn thiện các phase còn lại của Lab 7.
Mỗi phase ghi rõ: mục tiêu, state/dữ liệu mới, thay đổi backend (`app.py`), thay đổi
frontend (`index.html`), các bước thực hiện theo thứ tự, cách test, và rủi ro.

> Trạng thái nền tảng (đã xong Phase 1): YOLO detection, tracking IOU + track ID,
> Zone/ROI, WebSocket real-time, Chart.js analytics, dwell-time alert, event snapshot
> gallery, FPS HUD. Bug `IndexError` trong `tracker.update()` đã được sửa.

## Nguyên tắc chung khi thực hiện

1. **Không phá stream đang chạy ổn.** Mỗi tính năng thêm vào dạng cộng dồn (additive), bọc `try/except` ở vòng lặp stream.
2. **Verify từng bước** bằng smoke test Python (`python - <<PY ... PY`) trước khi sang bước kế.
3. **Tránh smart quotes** — editor đang tự đổi `"` thành `"`. Sau mỗi lần sửa chạy `grep` kiểm tra.
4. **Tái dùng pattern có sẵn**: Zone (vẽ canvas + POST/DELETE) là khuôn mẫu cho Line; `save_event_snapshot` cho mọi loại snapshot.

---

# PHASE 2 — Phân tích giám sát nâng cao

## Phase 2a — Line-crossing counter (đếm ra/vào)

### Mục tiêu
Vẽ một vạch ảo; khi tâm một track đi qua vạch, tăng bộ đếm IN hoặc OUT theo hướng.

### State mới (app.py)
```
_active_line: Optional[Dict] = None   # {"x1","y1","x2","y2"} normalized, "in_label","out_label"
```
Track thêm thuộc tính:
```
self.prev_centroid: Optional[Tuple[float,float]] = None   # tâm chuẩn hoá frame trước
self.counted_line = False                                  # đã đếm cho lần cắt này chưa
```
ObjectTracker thêm:
```
self.line_in_count = 0
self.line_out_count = 0
self.line_counts_by_class: Dict[str,Dict[str,int]] = {}   # {cls: {"in":n,"out":n}}
```

### Hàm hình học (thêm gần calculate_iou)
```
def point_side(line, px, py) -> int:
    # dấu tích chéo: >0 một phía, <0 phía kia, 0 nằm trên vạch
    ax,ay,bx,by = line["x1"],line["y1"],line["x2"],line["y2"]
    cross = (bx-ax)*(py-ay) - (by-ay)*(px-ax)
    return 1 if cross > 0 else (-1 if cross < 0 else 0)

def segments_intersect(p1,p2,p3,p4) -> bool:
    # kiểm tra đoạn p1p2 có cắt đoạn p3p4 không (orientation test)
    ...
```

### Logic đếm (method mới ObjectTracker.check_line)
- Tính tâm chuẩn hoá của mỗi detection: `cx=(x1+x2)/2/w`, `cy=(y1+y2)/2/h`.
- Map detection -> track theo `track_id`. Với mỗi track có `prev_centroid`:
  - `side_prev = point_side(line, *prev_centroid)`, `side_now = point_side(line, cx, cy)`.
  - Nếu `side_prev != 0 and side_now != 0 and side_prev != side_now` **VÀ** đoạn di chuyển `prev_centroid -> (cx,cy)` cắt đoạn vạch (`segments_intersect`):
    - Hướng: `side_prev < 0 and side_now > 0` => IN, ngược lại => OUT.
    - Tăng `line_in_count`/`line_out_count` + per-class. Sinh event `LINE_CROSS_IN/OUT` (severity INFO), broadcast WebSocket, lưu snapshot (dùng `save_event_snapshot`).
  - Cập nhật `track.prev_centroid = (cx,cy)`.
- Chỉ chạy khi `_active_line` khác None.

### Vẽ (draw_detections)
- Nếu `_active_line`: vẽ đường `cv2.line` màu tím + nhãn IN/OUT + 2 số đếm ở góc.

### Endpoints
```
POST /line   body {x1,y1,x2,y2,in_label?,out_label?}  -> set _active_line (clamp 0..1)
DELETE /line -> _active_line=None, reset đếm? (tuỳ chọn giữ số)
GET  /line-counts -> {in,out,by_class}
```
- `/video_feed`: gọi `tracker.check_line(...)` trong vòng lặp (tương tự `check_dwell`).
- Thêm `line_counts` vào broadcast `detection_update`.

### Frontend (index.html)
- Nút "Bật vẽ Line" + "Xóa Line" (giống Zone) — thêm canvas mode thứ 2 hoặc dùng chung `zoneCanvas` với biến `drawMode = 'zone' | 'line'`.
- Khi kéo: 'line' chỉ lưu 2 điểm (điểm đầu, điểm cuối) thay vì hình chữ nhật.
- Panel "Đếm ra/vào" hiển thị 2 ô số lớn IN/OUT + bảng per-class, cập nhật từ WebSocket.
- Xử lý event `LINE_CROSS_IN/OUT` -> banner + cập nhật số.

### Các bước thực hiện
1. Thêm `_active_line`, hàm `point_side`, `segments_intersect`.
2. Thêm thuộc tính Track + counters ObjectTracker.
3. Viết `ObjectTracker.check_line()`.
4. Cập nhật `draw_detections` vẽ line + số.
5. Endpoint `POST/DELETE /line`, `GET /line-counts`.
6. Gọi `check_line` trong stream loop + thêm `line_counts` vào broadcast.
7. UI: canvas dual-mode, panel đếm, xử lý WebSocket.
8. Smoke test: giả lập 1 track đi từ trái sang phải qua vạch -> IN=1.

### Test
```
# track đi qua vạch dọc giữa khung
line = {"x1":0.5,"y1":0.0,"x2":0.5,"y2":1.0}
# frame1 tâm bên trái (0.3), frame2 tâm bên phải (0.7) -> phải đếm IN hoặc OUT = 1
```

### Rủi ro
- Đếm trùng khi vật dao động quanh vạch -> dùng `segments_intersect` + reset cờ. **Thấp.**

---

## Phase 2b — Activity heatmap

### Mục tiêu
Phủ lớp màu nóng/lạnh cho biết vùng hay có hoạt động.

### State mới
```
HMAP_H, HMAP_W = 90, 160
HEATMAP_DECAY = 0.97
HEATMAP_ALPHA = 0.5
_heatmap_accum: Optional[np.ndarray] = None   # float32 (HMAP_H, HMAP_W)
```

### Hàm
```
def update_heatmap(detections, frame_shape):
    global _heatmap_accum
    if _heatmap_accum is None: _heatmap_accum = np.zeros((HMAP_H,HMAP_W), np.float32)
    _heatmap_accum *= HEATMAP_DECAY
    h,w = frame_shape[:2]
    for det in detections:
        cx = int((bbox tâm x)/w * HMAP_W); cy = ...
        cv2.circle(_heatmap_accum, (cx,cy), 3, 1.0, -1)  # splat

def render_heatmap_overlay(frame):
    if _heatmap_accum is None or max==0: return frame
    norm = (_heatmap_accum / _heatmap_accum.max() * 255).astype(uint8)
    colored = cv2.applyColorMap(norm, cv2.COLORMAP_JET)
    colored = cv2.resize(colored, (w,h))
    mask = norm resize > 10
    return cv2.addWeighted(frame, 1, colored, HEATMAP_ALPHA, 0) chỉ ở mask
```

### Wiring
- `/video_feed?heatmap=1` -> trong stream loop: `update_heatmap(...)`; nếu bật thì `annotated = render_heatmap_overlay(annotated)` sau `draw_detections`.
- Endpoint `GET /heatmap.png` -> trả ảnh heatmap chuẩn hoá riêng (StreamingResponse image/png).
- `POST /heatmap/reset` -> `_heatmap_accum=None`.

### Frontend
- Checkbox "Bật heatmap" -> thêm `&heatmap=1` vào URL stream (restart stream khi đổi).
- (Tuỳ chọn) ô ảnh hiển thị `/heatmap.png` cập nhật mỗi vài giây.

### Bước & test
1. Thêm state + 2 hàm. 2. Param `heatmap`. 3. Endpoint png + reset. 4. UI checkbox.
5. Test: chạy update_heatmap nhiều lần ở 1 điểm -> điểm đó giá trị cao nhất.

### Rủi ro: thấp (chỉ là mảng nhỏ + blend).

---

# PHASE 3 — Vận hành & triển khai

## Phase 3a — Chọn model YOLO (n/s/m) lúc chạy

### Mục tiêu
Đổi model không restart, thấy rõ tradeoff accuracy vs FPS.

### State mới
```
import threading
AVAILABLE_MODELS = ["yolov8n.pt","yolov8s.pt","yolov8m.pt","yolo11n.pt"]
_current_model_name = DEFAULT_MODEL_NAME
_model_lock = threading.Lock()
```

### Thay đổi
- `load_detector()` dùng `_current_model_name` thay cho hằng `DEFAULT_MODEL_NAME`.
- `yolo_detect()` bọc lời gọi `model(frame...)` trong `with _model_lock:` (tránh race khi swap).
- Endpoint:
```
GET  /available-models -> {current, available}
POST /set-model?name=yolov8s.pt:
    if name not in AVAILABLE_MODELS: 400
    with _model_lock:
        _current_model_name = name
        _detector = None
        _detector_status = {"backend":"not_loaded", ...}
    model, status = load_detector()   # nạp lại (có thể tải weights lần đầu)
    return status
```
- `/model-info` đã có — bổ sung `available_models` + `current_model`.

### Frontend
- Dropdown `<select id="modelSelect">` đổ từ `/available-models` + nút "Đổi model".
- Hiện model hiện tại + cảnh báo "model s/m chậm hơn, lần đầu cần internet tải weights".
- Sau khi đổi: nếu đang stream thì `startStream()` lại; FPS HUD sẽ tự phản ánh tốc độ mới.

### Bước & test
1. State + lock. 2. Sửa `load_detector`/`yolo_detect`. 3. 2 endpoint. 4. UI dropdown.
5. Test: gọi `/set-model?name=yolov8n.pt` -> status backend ultralytics/fallback OK, không crash khi đang detect.

### Rủi ro
- Race khi swap giữa lúc inference -> đã xử lý bằng `_model_lock`. **Thấp-TB.**
- Tải weights s/m cần internet -> bắt exception, fallback giữ model cũ.

## Phase 3b — Docker hóa

### File mới
**Dockerfile**
```
FROM python:3.11-slim
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 libglib2.0-0 && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 8000
CMD ["uvicorn","app:app","--host","0.0.0.0","--port","8000"]
```
**docker-compose.yml**
```
services:
  lab7:
    build: .
    ports: ["8000:8000"]
    volumes:
      - ./data:/app/data
      - ./outputs:/app/outputs
```
**.dockerignore**: `.venv`, `__pycache__`, `*.pyc`, `data/input_images/*`, `data/annotated_images/*`.

### Lưu ý / giới hạn
- **Windows: webcam `source=0` KHÔNG vào được container.** Chỉ chạy upload / ảnh mẫu / IP camera URL.
- Image nặng (~vài GB) do torch+ultralytics. Giảm bằng torch CPU-only nếu cần.
- Lần đầu chạy cần internet tải YOLO weights (hoặc COPY sẵn file `.pt` vào image).

### Bước & test
1. Viết 3 file. 2. `docker build -t lab7 .`. 3. `docker compose up`. 4. Mở `:8000`, test upload + ảnh mẫu. 5. Ghi chú giới hạn webcam vào README.

### Rủi ro: TB (build lâu, webcam hạn chế). Giá trị demo live trên Windows thấp.

---

# PHASE 4 — Multi-camera grid (REFACTOR LỚN)

### Mục tiêu
Giám sát nhiều camera cùng lúc, mỗi camera có tracker/zone/line/heatmap riêng.

### Vấn đề cốt lõi
Hiện mọi state là global đơn lẻ: `_active_zone`, `tracker`, `_active_line`,
`_heatmap_accum`, `_last_snapshot_ts`. Multi-camera cần **đóng gói state theo từng camera**.

### Thiết kế: class CameraSession
```
class CameraSession:
    def __init__(self, cam_id, source, conf=0.35, classes="", flip=1, dwell=5.0):
        self.cam_id = cam_id
        self.source = source
        self.tracker = ObjectTracker()
        self.zone = None
        self.line = None
        self.heatmap = None
        self.last_snapshot_ts = 0.0
        self.conf, self.classes, self.flip, self.dwell = ...
        self.fps = 0.0

_sessions: Dict[str, CameraSession] = {}
_sessions_lock = threading.Lock()
```

### Refactor cần làm (đây là phần tốn công)
1. **Bỏ global** `_active_zone`, `_active_line`, `_heatmap_accum`, `_last_snapshot_ts`
   -> chuyển thành thuộc tính của `CameraSession`.
2. `run_detection`, `draw_detections`, `check_dwell`, `check_line`, `update_heatmap`,
   `save_event_snapshot` -> nhận `session` (hoặc zone/line) làm tham số thay vì đọc global.
3. `stream_detect_frames(cam_id)` -> lấy session từ registry, dùng state của session.
4. Endpoint scoped theo camera:
```
POST   /cameras           {cam_id, source, ...}   -> tạo session
GET    /cameras                                   -> liệt kê
DELETE /cameras/{cam_id}                          -> xoá + release
GET    /video_feed?cam=front
POST   /zone?cam=front , /line?cam=front , ...
```
5. WebSocket: mỗi message gắn `cam_id`; client lọc theo tile.

### Concurrency
- Nhiều stream = nhiều `to_thread` inference đồng thời. Dùng **shared model + `_model_lock`**
  (serial hoá inference) cho model nano; hoặc per-camera model nếu đủ RAM.

### Frontend
- Layout lưới (CSS grid) — mỗi ô: `<img>` stream riêng + panel counts riêng + controls.
- Form thêm/xoá camera (tái dùng CRUD của Lab 6 nếu port được).

### Bước thực hiện (thứ tự an toàn)
1. Tạo `CameraSession` + registry, GIỮ nguyên đường cũ (1 camera "default") để không vỡ.
2. Refactor dần các hàm nhận `session` (test sau mỗi hàm).
3. Thêm endpoint `/cameras` CRUD.
4. Sửa `/video_feed` + các endpoint nhận `cam`.
5. UI grid.
6. Test 2 camera (source=0 + 1 ảnh/URL giả lập).

### Rủi ro: **CAO** — đụng gần hết global + UI. Làm CUỐI CÙNG, mỗi bước test kỹ.
> Gợi ý: Lab 6 đã có camera CRUD + WebSocket + auto đổi stream — port kiến trúc đó sang.

---

# Thứ tự thực hiện tổng thể & ước lượng

| Thứ tự | Phase | Nội dung | Độ khó | Rủi ro |
|--------|-------|----------|--------|--------|
| 1 | 2a | Line-crossing đếm ra/vào | TB | Thấp |
| 2 | 3a | Chọn model n/s/m | Thấp | Thấp-TB |
| 3 | 2b | Activity heatmap | TB | Thấp |
| 4 | 3b | Docker | Thấp | TB |
| 5 | 4 | Multi-camera (refactor) | Cao | Cao |

Lý do thứ tự: 2a + 3a giá trị/công cao, rủi ro thấp, xây trên tracking vừa sửa.
Heatmap nhẹ làm kèm. Docker và Multi-camera để cuối vì nặng/rủi ro.

# Chiến lược test xuyên suốt
- Sau mỗi phase: `python -c "import ast; ast.parse(open('app.py').read())"` + smoke test logic.
- `grep` smart quotes cả `app.py` và `index.html`.
- Chạy `run_lab7_demo.py` -> phải vẫn `LOCAL_PIPELINE_TEST_PASS`.
- Test thủ công trên dashboard: stream + zone + line + dwell + gallery + đổi model.

# Bảng rủi ro & giảm thiểu
| Rủi ro | Ảnh hưởng | Giảm thiểu |
|--------|-----------|------------|
| Đếm line trùng | Số sai | segments_intersect + cờ counted |
| Race khi đổi model | Crash inference | _model_lock |
| Webcam trong Docker (Windows) | Không stream cam | Document; dùng upload/IP-cam |
| Refactor multi-camera vỡ app | Mất chức năng | Giữ đường "default", test từng hàm |
| Smart quotes editor | HTML/JS vỡ | grep sau mỗi sửa, tắt smart quotes |
