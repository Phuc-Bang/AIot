# 03 Data and Features

## Dataset đang dùng

Project dùng dataset `ambient_temperature_system_failure` từ Numenta Anomaly Benchmark. Đây là chuỗi thời gian nhiệt độ môi trường có một số khoảng bất thường đã được gắn nhãn.

Trong project hiện tại, file chính là:

```text
data/ambient_temperature_system_failure_labeled.csv
```

Nếu không tải được từ Internet, project dùng:

```text
data/sample_ambient_temperature_system_failure.csv
```

## Schema dữ liệu

Schema tối thiểu:

| Cột | Ý nghĩa |
| --- | --- |
| `timestamp` | Thời điểm ghi nhận telemetry |
| `value` | Giá trị nhiệt độ |
| `label` | Nhãn anomaly, `0` là normal, `1` là anomaly |

Ví dụ:

```text
timestamp            value   label
2013-07-04 00:00:00  22.107  0
2013-07-04 00:05:00  21.703  0
```

Trong hệ thống AIoT thật, schema thường có thêm:

- `device_id`
- `site_id`
- `sensor_type`
- `unit`
- `gateway_id`
- `firmware_version`
- `quality_flag`

Lab giữ schema nhỏ để tập trung vào anomaly detection.

## `timestamp`

`timestamp` là cột sống của bài toán time-series. Code parse timestamp bằng `pd.to_datetime()`, sort theo thời gian và drop duplicate timestamp.

Với IoT, thứ tự thời gian rất quan trọng vì feature hiện tại phụ thuộc dữ liệu quá khứ:

- rolling mean 12 điểm gần nhất.
- rolling std 12 điểm gần nhất.
- rolling mean 36 điểm gần nhất.
- delta so với điểm trước.
- z-score so với cửa sổ gần đây.

Nếu timestamp sai, trùng, lệch timezone hoặc bị đảo thứ tự, feature sẽ sai.

## `value`

`value` là giá trị cảm biến nhiệt độ. Model không chỉ học giá trị tuyệt đối, mà học thêm hành vi xung quanh giá trị đó.

Ví dụ:

- `value = 28` có thể bình thường nếu cả ngày quanh 27 đến 29.
- `value = 28` có thể bất thường nếu 30 phút trước quanh 20.
- `value = 22` có thể đáng nghi nếu sensor giữ nguyên quá lâu và rolling std gần 0.

## `label`

`label` dùng để đánh giá model:

- `0`: normal.
- `1`: anomaly.

Trong `download_data.py`, label được tạo từ `combined_windows.json` của NAB. Script lấy các anomaly window, sau đó set `label = 1` cho các timestamp nằm trong window đó.

Trong anomaly detection thực tế, label thường thiếu hoặc không hoàn hảo. Vì vậy metric cần đọc cẩn thận. Label không hoàn hảo có thể làm một cảnh báo đúng bị tính thành false positive.

## Train/test split theo thời gian

Project dùng:

```python
time_split(df, train_ratio=0.65)
```

Nghĩa là:

- 65 phần trăm đầu chuỗi thời gian dùng làm train.
- 35 phần trăm sau dùng làm test.

Đây là cách đúng cho time-series vì mô phỏng thực tế:

```text
quá khứ -> train
tương lai -> test
```

## Vì sao không random split time-series?

Random split sẽ trộn điểm quá khứ và tương lai. Điều này tạo data leakage.

Ví dụ sai:

- Model train trên dữ liệu ngày 10.
- Model test trên dữ liệu ngày 5.

Trong vận hành thật, model không thể biết tương lai. Nếu random split, metric có thể đẹp hơn thực tế vì model gián tiếp nhìn thấy pattern của giai đoạn sau.

Với IoT, random split còn làm hỏng ngữ cảnh:

- Rolling feature phụ thuộc điểm trước đó.
- Chu kỳ ngày/đêm bị trộn.
- Drift theo thời gian bị che mất.
- Giai đoạn sự cố có thể bị chia vào cả train và test.

## Feature engineering

Feature được tạo trong `add_time_features()` của `src/utils.py`.

### `hour`

Giờ trong ngày, lấy từ timestamp.

Ý nghĩa: nhiệt độ có thể có pattern theo ngày đêm. Ví dụ phòng có điều hòa hoạt động trong giờ làm việc.

### `dayofweek`

Thứ trong tuần, lấy từ timestamp.

Ý nghĩa: hành vi thiết bị có thể khác giữa ngày làm việc và cuối tuần.

### `rolling_mean_12`

Trung bình 12 điểm gần nhất.

Nếu dữ liệu cách nhau 5 phút, 12 điểm tương đương khoảng 1 giờ.

Ý nghĩa: mô tả mức nền gần đây của nhiệt độ.

### `rolling_std_12`

Độ lệch chuẩn 12 điểm gần nhất.

Ý nghĩa: mô tả mức dao động gần đây. Nếu std cao, cảm biến đang biến động mạnh. Nếu std rất thấp, có thể sensor bị kẹt.

### `rolling_mean_36`

Trung bình 36 điểm gần nhất.

Nếu dữ liệu cách nhau 5 phút, 36 điểm tương đương khoảng 3 giờ.

Ý nghĩa: tạo baseline dài hơn để so với giá trị hiện tại.

### `delta_1`

Chênh lệch với điểm ngay trước đó.

Ý nghĩa: phát hiện nhảy đột ngột. Ví dụ nhiệt độ tăng 5 độ trong 5 phút có thể là bất thường.

### `delta_3`

Chênh lệch với 3 điểm trước.

Ý nghĩa: phát hiện thay đổi trong cửa sổ ngắn hơn nhưng bớt nhạy hơn `delta_1`.

### `zscore_rolling`

Z-score của `value` so với rolling mean và rolling std của cửa sổ 36 điểm.

Ý nghĩa:

```text
zscore cao -> value lệch mạnh so với pattern gần đây
```

Quy ước thường gặp:

- `abs(zscore) > 2`: đáng chú ý.
- `abs(zscore) > 3`: bất thường mạnh.

### `is_stuck_candidate`

Cờ phát hiện sensor có thể bị kẹt nếu rolling std 6 điểm nhỏ hơn 0.03.

Ý nghĩa: một cảm biến giữ gần như cùng một giá trị quá lâu có thể không phải hệ thống ổn định, mà là sensor bị lỗi.

## Danh sách feature đưa vào model

`FEATURE_COLUMNS` gồm:

```text
value
hour
dayofweek
rolling_mean_12
rolling_std_12
rolling_mean_36
delta_1
delta_3
zscore_rolling
is_stuck_candidate
```

Model học từ vector feature này, không học trực tiếp từ raw CSV.

## Nhận xét kỹ thuật

- Feature hiện tại đủ tốt cho baseline vì kết hợp giá trị hiện tại, thời gian và ngữ cảnh rolling.
- Cửa sổ 12, 36, 6 đang hard-code. Nên biến thành config nếu dùng nhiều loại sensor.
- Feature rolling trong API cần đủ history. Nếu gửi quá ít điểm, rolling feature vẫn tính được do `min_periods=1`, nhưng chất lượng kém.
- Dữ liệu hiện không có `device_id`, nên event layer hard-code device. Với nhiều sensor, đây là điểm cần sửa.

## Đề xuất cải tiến

- Thêm kiểm tra frequency dữ liệu, missing timestamp và gap bất thường.
- Thêm feature theo mùa vụ: sin/cos của hour để tránh coi 23 giờ và 0 giờ quá xa nhau.
- Thêm feature rate-of-change theo đơn vị thời gian thật, không chỉ theo số dòng.
- Thêm feature rolling median và quantile để chống nhiễu.
- Với nhiều thiết bị, tính rolling feature theo từng `device_id`.
