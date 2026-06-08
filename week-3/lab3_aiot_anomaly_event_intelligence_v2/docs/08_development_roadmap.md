# 08 Development Roadmap

## Mục tiêu phát triển tiếp

Lab hiện tại là demo end-to-end. Nếu muốn phát triển thành hệ thống AIoT gần thực tế, nên nâng cấp theo hướng:

```text
data reliability -> model quality -> event intelligence -> API robustness -> storage/dashboard -> deployment/monitoring -> real sensor integration
```

Không nên nhảy ngay vào model phức tạp. Với AIoT, lỗi thường nằm ở data, feature, threshold, event routing và vận hành.

## Giai đoạn 1: Củng cố data pipeline

### Thay dataset

Thử các dataset khác:

- Nhiệt độ phòng khác.
- Dòng điện motor.
- Độ rung máy.
- Độ ẩm nhà kính.
- Dữ liệu từ ESP32.

Cần chuẩn hóa schema tối thiểu:

```text
timestamp, device_id, value, label
```

Nếu có nhiều loại sensor:

```text
timestamp, device_id, sensor_type, value, unit, label
```

### Kiểm tra chất lượng dữ liệu

Thêm các kiểm tra:

- Missing timestamp.
- Duplicate timestamp.
- Gap quá dài.
- Value ngoài khoảng vật lý.
- Tần suất sampling thay đổi.
- Timezone không thống nhất.

## Giai đoạn 2: Chỉnh feature

Feature hiện tại đủ cho baseline. Có thể thêm:

- Rolling median.
- Rolling min/max.
- Rolling quantile.
- Exponential moving average.
- Rate of change theo phút.
- Sin/cos cho hour và dayofweek.
- Feature theo từng `device_id`.
- Sensor quality flag.

Với dữ liệu nhiều sensor, tuyệt đối tránh tính rolling chung toàn bộ dataset. Phải group theo `device_id`.

## Giai đoạn 3: Chỉnh threshold

Threshold quyết định số cảnh báo. Đây là phần rất quan trọng trong vận hành.

Hướng nâng cấp:

- Tách train/validation/test theo thời gian.
- Chọn threshold trên validation set.
- So sánh nhiều threshold theo Precision, Recall, F1.
- Chọn threshold theo chi phí vận hành.
- Cho phép threshold khác nhau theo device hoặc site.

Ví dụ:

```text
Kho lạnh vaccine: ưu tiên recall cao, chấp nhận nhiều false alert hơn.
Phòng học: ưu tiên precision cao hơn để tránh spam cảnh báo.
```

## Giai đoạn 4: Cooldown chống alert fatigue

Alert fatigue xảy ra khi hệ thống cảnh báo quá nhiều khiến người vận hành bỏ qua.

Thêm cooldown rule:

```text
Nếu device_id + event_type đã alert trong 10 phút gần nhất,
không tạo alert mới, chỉ update incident hiện tại.
```

Gợi ý state:

- `first_seen`
- `last_seen`
- `count`
- `max_score`
- `current_severity`
- `status`

## Giai đoạn 5: Event aggregation

Thay vì mỗi điểm anomaly là một event riêng, gộp các anomaly gần nhau thành incident.

Ví dụ:

```text
10 điểm bất thường liên tiếp trong 30 phút -> 1 incident TEMPERATURE_ANOMALY
```

Lợi ích:

- Giảm spam.
- Dễ hiển thị trên dashboard.
- Dễ gán trách nhiệm xử lý.
- Dễ đo thời gian sự cố.

## Giai đoạn 6: Dashboard

Dashboard nên có:

- Time-series chart theo device.
- Marker anomaly.
- Bảng event/incident.
- Filter theo severity, device, time range.
- Metric model.
- Trạng thái API và model version.

Công nghệ có thể dùng:

- Streamlit cho lab nhanh.
- Grafana nếu dữ liệu vào time-series database.
- React hoặc Next.js nếu muốn dashboard custom.

## Giai đoạn 7: Database log

CSV đủ cho lab, nhưng hệ thống thật cần database.

Gợi ý đơn giản:

- SQLite cho local prototype.
- PostgreSQL cho backend nghiêm túc.
- TimescaleDB hoặc InfluxDB cho time-series.

Bảng nên có:

```text
telemetry
model_predictions
events
incidents
device_registry
model_registry
```

## Giai đoạn 8: Docker

Docker giúp chạy API ổn định hơn.

Các thành phần có thể đóng gói:

- FastAPI service.
- Model artifact.
- Config.
- Database.
- Dashboard.

Tối thiểu nên có:

- `Dockerfile`
- `docker-compose.yml`
- `.env`

## Giai đoạn 9: Monitoring model và data drift

Model tốt hôm nay có thể kém sau vài tuần vì:

- Sensor thay đổi.
- Môi trường thay đổi.
- Thiết bị được bảo trì.
- Firmware đổi cách đo.
- Data distribution đổi.

Cần monitor:

- Distribution của `value`.
- Distribution của feature.
- Distribution của `anomaly_score`.
- Số alert theo ngày.
- Precision/Recall nếu có feedback label.
- Tỉ lệ missing data.

## Giai đoạn 10: Kết nối ESP32 hoặc sensor thật

Hướng tích hợp:

```text
ESP32 sensor -> MQTT/HTTP -> backend ingest -> feature window -> anomaly API -> event store -> dashboard
```

Các điểm cần xử lý:

- Device identity.
- Timestamp từ device hay server.
- Retry khi mất mạng.
- Buffer ở edge.
- Chuẩn hóa unit.
- Calibration sensor.
- Security: API key hoặc token.

## Roadmap đề xuất theo thứ tự ưu tiên

1. Đồng bộ scoring giữa train và API.
2. Lưu threshold/calibration metadata cùng model.
3. Thêm validation split và threshold tuning report.
4. Thêm schema validation cho API.
5. Thêm event rule riêng và cooldown.
6. Ghi event vào SQLite.
7. Thêm dashboard đơn giản.
8. Docker hóa API.
9. Thêm monitoring drift.
10. Kết nối ESP32 hoặc nguồn telemetry thật.

## Nhận xét kỹ thuật

- Không nên bắt đầu bằng deep learning phức tạp. Baseline hiện tại còn nhiều điểm vận hành cần làm trước.
- Nên làm cho pipeline có thể lặp lại và đo được trước khi tối ưu model.
- Với AIoT, event quality quan trọng không kém model quality.
- Dashboard và database sẽ giúp phát hiện vấn đề dữ liệu nhanh hơn việc chỉ nhìn metric JSON.

## Đề xuất cải tiến đầu tiên nên làm

Tạo artifact mới:

```text
models/iforest_v1_artifact.joblib
```

Bên trong lưu:

```python
{
    "model": pipeline,
    "feature_columns": FEATURE_COLUMNS,
    "threshold": threshold,
    "score_min": min_s,
    "score_max": max_s,
    "model_version": "iforest_v1"
}
```

Sau đó sửa API để dùng cùng cách normalize với training. Đây là cải tiến có tác động lớn nhất đến tính nhất quán offline/online.
