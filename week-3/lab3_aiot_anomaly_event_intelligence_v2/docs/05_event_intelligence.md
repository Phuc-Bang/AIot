# 05 Event Intelligence

## Event intelligence là gì?

Event intelligence là lớp biến output kỹ thuật của model thành thông tin có thể vận hành.

Model trả:

```text
anomaly_score, is_anomaly
```

Hệ thống AIoT cần:

```text
event_type, severity, decision, explanation, safety_note
```

Nói cách khác, model trả tín hiệu. Event intelligence biến tín hiệu đó thành event có ngữ cảnh và hành động tiếp theo.

## `is_anomaly` khác `event_type` như nào?

`is_anomaly` là kết quả nhị phân:

```text
0 = không bất thường
1 = bất thường
```

`event_type` nói rõ loại event:

```text
TEMPERATURE_ANOMALY
NORMAL_TELEMETRY
SENSOR_STUCK
SUDDEN_DROP
SUDDEN_RISE
```

Trong code hiện tại:

- Nếu anomaly: `TEMPERATURE_ANOMALY`.
- Nếu normal trong API: `NORMAL_TELEMETRY`.

Với hệ thống thật, một `is_anomaly = 1` nên được phân loại tiếp. Ví dụ nhiệt độ tăng nhanh khác với sensor bị kẹt, dù cả hai đều là anomaly.

## `anomaly_score` khác `severity` như nào?

`anomaly_score` là điểm model, thường là số liên tục.

`severity` là mức nghiêm trọng vận hành:

```text
LOW
MEDIUM
HIGH
CRITICAL
```

Score cao không tự động đồng nghĩa nguy hiểm cao. Cần thêm ngữ cảnh:

- Thiết bị có quan trọng không?
- Giá trị có vượt ngưỡng an toàn vật lý không?
- Anomaly kéo dài bao lâu?
- Anomaly có lặp lại nhiều lần không?
- Có nhiều sensor cùng xác nhận không?

Ví dụ:

- Score 0.82 trong phòng học có thể là `MEDIUM`.
- Score 0.70 trong kho lạnh vaccine có thể là `HIGH`.

## `severity` khác `decision` như nào?

`severity` mô tả mức độ nghiêm trọng.

`decision` mô tả hành động hệ thống nên làm.

Ví dụ mapping hiện tại:

| Severity | Decision |
| --- | --- |
| `LOW` | `LOG_FOR_MONITORING` |
| `MEDIUM` | `CREATE_WARNING_EVENT` |
| `HIGH` | `CREATE_ALERT_AND_REQUIRE_HUMAN_CHECK` |

Hai event cùng `HIGH` có thể có decision khác nhau tùy hệ thống:

- Gửi SMS cho kỹ thuật viên.
- Tạo ticket bảo trì.
- Bật chế độ an toàn.
- Yêu cầu xác nhận thủ công.
- Chỉ log nếu đang bảo trì định kỳ.

## Vì sao không tự động điều khiển thiết bị ngay khi anomaly cao?

Trong AIoT, model có thể sai. Nếu tự động điều khiển thiết bị chỉ dựa vào anomaly score, hệ thống có thể gây hậu quả ngoài ý muốn.

Rủi ro:

- False positive làm thiết bị dừng không cần thiết.
- Sensor lỗi làm hệ thống phản ứng sai.
- Model drift khiến score không còn đáng tin.
- Dữ liệu thiếu hoặc timestamp sai làm feature sai.
- Hành động điều khiển có thể ảnh hưởng an toàn con người hoặc tài sản.

Vì vậy code hiện tại có `safety_note`:

```text
Không tự động điều khiển thiết bị khi anomaly cao; cần xác nhận hoặc rule an toàn.
```

Đây là tư duy đúng. Với AIoT thật, action tự động phải qua safety rule độc lập với ML.

## `anomaly_event_log.csv` dùng để làm gì?

File:

```text
outputs/anomaly_event_log.csv
```

Lưu các event anomaly đã qua event layer. Các cột chính:

- `timestamp`
- `device_id`
- `value`
- `anomaly_score`
- `severity`
- `event_type`
- `decision`
- `explanation`
- `model_version`

Ứng dụng:

- Audit quyết định của hệ thống.
- Làm dữ liệu cho dashboard.
- Phân tích false alert và missed alert.
- Gửi cho team vận hành kiểm tra.
- Dùng làm dữ liệu feedback để cải thiện model.
- Làm nguồn event cho downstream service.

## Rule severity hiện tại

Trong `build_events()`:

```text
score >= 0.80 -> HIGH
score >= 0.55 -> MEDIUM
else -> LOW
```

Trong `app.py`, `decision_from_score()` dùng logic tương tự.

Đây là rule đơn giản, phù hợp lab. Nhưng rule production nên có thêm:

- Loại sensor.
- Device criticality.
- Site criticality.
- Khoảng thời gian xảy ra.
- Số lần lặp lại trong N phút.
- Có đang trong maintenance window không.
- Có sensor khác xác nhận không.

## Gợi ý rule severity thực tế

Ví dụ cho cảm biến nhiệt độ:

```text
LOW:
  score >= 0.55
  không vượt ngưỡng vật lý
  chỉ xảy ra một lần

MEDIUM:
  score >= 0.70
  hoặc abs(zscore) > 3
  hoặc delta_1 lớn
  lặp lại ít nhất 2 lần trong 10 phút

HIGH:
  score >= 0.85
  hoặc vượt ngưỡng an toàn vật lý
  hoặc anomaly kéo dài hơn 15 phút
  hoặc nhiều sensor cùng bất thường

CRITICAL:
  vượt ngưỡng nguy hiểm
  và liên quan thiết bị quan trọng
  và rule an toàn xác nhận
```

## Gợi ý safety rule

Safety rule nên tách khỏi model:

- Không tự động bật/tắt thiết bị nếu chỉ có một sensor bất thường.
- Cần xác nhận từ ít nhất hai nguồn hoặc rule vật lý.
- Nếu sensor quality flag xấu, chỉ log và yêu cầu kiểm tra sensor.
- Nếu đang maintenance, giảm severity hoặc route event sang maintenance log.
- Nếu cùng loại alert lặp lại, dùng cooldown để tránh spam.
- Nếu vượt ngưỡng vật lý nguy hiểm, ưu tiên rule an toàn hơn model score.

## Nhận xét kỹ thuật

- Event layer trong project là điểm rất đáng học vì nó đưa ML gần với backend và vận hành.
- `build_events()` chỉ ghi event anomaly, không ghi normal telemetry. Điều này hợp lý cho event log, nhưng nếu muốn audit đầy đủ cần log cả decision cho normal sampling.
- `device_id` đang hard-code trong event log. API thì lấy từ request. Nên đồng nhất.
- Severity rule hiện dựa chủ yếu vào score. Nên kết hợp z-score, delta, stuck flag và context.

## Đề xuất cải tiến

- Tách event rule thành file riêng, ví dụ `event_rules.py`.
- Thêm cooldown theo `device_id + event_type`.
- Thêm event aggregation: gộp nhiều anomaly liên tiếp thành một incident.
- Thêm state machine cho incident: `OPEN`, `ACKNOWLEDGED`, `RESOLVED`.
- Thêm event sink: CSV, SQLite, PostgreSQL, Kafka hoặc MQTT.
