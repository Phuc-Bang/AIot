# CLAUDE.md

File này cung cấp hướng dẫn cho Claude Code (claude.ai/code) khi làm việc trong repository này.

## Khởi chạy hệ thống

Tất cả lệnh chạy từ thư mục `smart_classroom_aiot/`.

**Khởi động hạ tầng (bắt buộc chạy trước):**
```bash
docker-compose up -d
# Mosquitto MQTT: TCP :1884, WebSocket :9001
# InfluxDB: :8086
```

**Backend (FastAPI + rule engine + phát hiện bất thường):**
```bash
cd backend && pip install -r requirements.txt
python main.py
# Chạy tại http://127.0.0.1:8000 (dashboard tại /)
```

**Simulator (chạy ở các terminal riêng biệt):**
```bash
cd simulator && pip install -r requirements.txt
python sensor_simulator.py      # gửi dữ liệu cảm biến mỗi 5 giây
python actuator_simulator.py    # nhận lệnh điều khiển
```

**Huấn luyện lại mô hình AI (tùy chọn — model.pkl đã có sẵn):**
```bash
cd ai && pip install -r requirements.txt
python train_anomaly_model.py
# Sao chép model.pkl và feature_names.pkl vào thư mục backend/ thủ công
```

## Kiến trúc hệ thống

Năm module giao tiếp qua MQTT và HTTP:

```
Dashboard (Trình duyệt)
  ├─ MQTT WS → ws://127.0.0.1:9001 (Mosquitto)
  └─ REST    → http://127.0.0.1:8000 (FastAPI backend)

FastAPI Backend (backend/main.py)
  ├─ MQTT client  → subscribe classroom/+/sensors, classroom/status
  ├─ InfluxDB     → lưu telemetry + bất thường (org: smartclass, bucket: smart_classroom)
  ├─ Rule Engine  → chạy mỗi 10s (tự động bật/tắt AC/đèn theo nhiệt độ, ánh sáng, sĩ số)
  └─ Anomaly task → chạy mỗi 5 phút (Isolation Forest trên cửa sổ 10 mẫu)

Mosquitto MQTT Broker (docker)
  Topics:
    classroom/A203/sensors  ← sensor_simulator publish
    classroom/control       → actuator_simulator subscribe; backend publish
    classroom/status        ← actuator_simulator publish phản hồi
    classroom/anomaly       → backend publish cảnh báo; dashboard subscribe

InfluxDB (docker)
  Token: smart-classroom-token | User: admin / admin123
```

## Các quyết định thiết kế quan trọng

**Chế độ điều khiển** — Biến toàn cục `control_mode` trong `backend/main.py` nhận giá trị `"auto"` hoặc `"manual"`. Rule Engine bỏ qua mọi lệnh thiết bị khi `control_mode == "manual"`. Thay đổi chế độ qua endpoint `/api/mode` (GET/POST), không sửa trực tiếp biến.

**Đồng bộ trạng thái thiết bị** — `sensor_simulator.py` duy trì dict `state` chứa `ac_state` và `light_state`. Nó subscribe `classroom/control` và cập nhật các giá trị này để mức tiêu thụ điện trong telemetry phản ánh đúng lệnh thực tế.

**Xử lý lệnh toggle** — `actuator_simulator.py` lưu dict `device_states` và đảo trạng thái khi nhận lệnh `toggle`. Dashboard (`app.js`) đọc `deviceStates` (đồng bộ từ MQTT) và gửi lệnh `ON`/`OFF` rõ ràng — **không thay đổi dashboard để gửi `"toggle"`** vì cách đó đã từng gây lỗi mất đồng bộ trạng thái.

**Trường payload bất thường** — Backend publish `{"reason": "..."}` cho tin nhắn anomaly. Hàm `showAnomaly()` trong `app.js` đọc `data.reason`. Nếu đổi tên trường ở backend, phải cập nhật `app.js` tương ứng.

**Anomaly chặn Rule Engine** — Khi phát hiện bất thường, Rule Engine sẽ không phát lệnh tự động cho phòng đó cho đến khi hết cửa sổ bất thường.

## Cổng dịch vụ

| Dịch vụ   | Cổng | Giao thức |
|-----------|------|-----------|
| FastAPI   | 8000 | HTTP      |
| Mosquitto | 1884 | MQTT TCP  |
| Mosquitto | 9001 | WebSocket |
| InfluxDB  | 8086 | HTTP      |

## Mô hình AI

Isolation Forest huấn luyện trên 5000 mẫu tổng hợp (tỷ lệ nhiễu 5%). Đặc trưng: mean/std/min/max của nhiệt độ, độ ẩm, ánh sáng và công suất trên cửa sổ 10 mẫu (16 đặc trưng). Ngưỡng bình thường: nhiệt độ 28±2°C, độ ẩm 60±5%, ánh sáng 400±50 lux, công suất 2±0.5 kW.
