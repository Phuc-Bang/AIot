# 00 Project Overview

## Project này làm gì?

Lab 3 là một project mẫu về **Anomaly Detection & Event Intelligence cho AIoT**. Project lấy dữ liệu telemetry nhiệt độ theo thời gian, tạo feature từ chuỗi thời gian, train model phát hiện bất thường, đánh giá kết quả, sinh event log có cấu trúc và deploy API `/detect-anomaly` bằng FastAPI.

Luồng tổng quát:

```text
telemetry data -> feature engineering -> anomaly model -> anomaly_score -> event -> severity -> decision -> API
```

Trong bối cảnh AIoT, project này mô phỏng một cảm biến nhiệt độ phòng hoặc thiết bị công nghiệp. Hệ thống không chỉ hỏi "giá trị này có lạ không?", mà còn hỏi tiếp:

- Lạ ở mức nào?
- Có nên tạo cảnh báo không?
- Có cần con người kiểm tra không?
- Có nên tự động điều khiển thiết bị không?
- Kết quả có thể log lại để audit và cải tiến model không?

Đây là điểm khác biệt giữa một notebook ML đơn thuần và một pipeline AIoT có tư duy vận hành.

## Vì sao cần anomaly detection trong AIoT?

Trong AIoT, dữ liệu đến từ cảm biến, gateway, thiết bị edge hoặc hệ thống SCADA thường có các vấn đề sau:

- Cảm biến đo sai do hỏng, lệch chuẩn hoặc bị kẹt giá trị.
- Thiết bị thay đổi hành vi do quá nhiệt, quá tải, rung bất thường hoặc môi trường thay đổi.
- Dữ liệu có tính mùa vụ theo giờ, ngày, ca vận hành.
- Ngưỡng if-else cố định không bắt được những bất thường phụ thuộc ngữ cảnh.
- Cảnh báo quá nhiều gây mệt mỏi cho người vận hành.

Ví dụ thực tế: nhiệt độ 28 độ C có thể bình thường vào buổi trưa, nhưng bất thường nếu trước đó thiết bị ổn định quanh 20 độ C và đột ngột tăng nhanh. Anomaly detection giúp nhìn vào **mẫu hành vi theo thời gian**, không chỉ nhìn một giá trị đơn lẻ.

## Mục tiêu Lab 3

Mục tiêu kỹ thuật của Lab 3:

- Hiểu bài toán anomaly detection trên chuỗi thời gian IoT.
- Biết cách tải và gắn nhãn dataset public từ NAB.
- Biết tạo feature từ timestamp và giá trị cảm biến.
- Biết train baseline model bằng Isolation Forest.
- Biết đánh giá model bằng Precision, Recall, F1 và Confusion Matrix khi có label.
- Biết biến model output thành event intelligence.
- Biết deploy model qua API để hệ thống khác gọi được.

Mục tiêu tư duy hệ thống:

- Phân biệt **test model offline** và **deploy model online**.
- Hiểu vì sao `anomaly_score` chưa đủ để ra quyết định vận hành.
- Hiểu vai trò của event layer, severity layer và safety rule.
- Nhìn thấy đường phát triển từ lab nhỏ thành hệ thống AIoT thật.

## Bài toán project đang giải quyết

Dataset chính là `ambient_temperature_system_failure` từ Numenta Anomaly Benchmark. Dữ liệu gồm các điểm nhiệt độ theo timestamp. Một số khoảng thời gian được đánh dấu là anomaly.

Bài toán:

```text
Input: lịch sử telemetry nhiệt độ
Output: điểm mới nhất có bất thường không, mức độ nghiêm trọng, loại event và quyết định xử lý
```

Ở mức model, output là:

- `anomaly_score`: điểm bất thường.
- `is_anomaly`: cờ 0/1 sau khi so với threshold.

Ở mức AIoT event, output được mở rộng thành:

- `event_type`: ví dụ `TEMPERATURE_ANOMALY`.
- `severity`: `LOW`, `MEDIUM`, `HIGH`.
- `decision`: log, warning hoặc yêu cầu kiểm tra thủ công.
- `explanation`: lý do sơ bộ dựa trên score, z-score, delta hoặc stuck flag.

## Sản phẩm đầu ra

Sau khi chạy đầy đủ project, các artifact chính gồm:

- `models/isolation_forest_iforest_v1.joblib`: model Isolation Forest được deploy bởi API.
- `models/mlp_autoencoder_demo.joblib`: model autoencoder demo bằng `MLPRegressor`.
- `outputs/iforest_metrics.json`: metric của Isolation Forest.
- `outputs/autoencoder_metrics.json`: metric của autoencoder demo.
- `outputs/iforest_test_predictions.csv`: prediction trên tập test.
- `outputs/autoencoder_test_predictions.csv`: prediction autoencoder trên tập test.
- `outputs/anomaly_event_log.csv`: event log đã qua event intelligence.
- `figures/anomaly_detection_result.png`: biểu đồ giá trị và điểm anomaly.
- `figures/anomaly_score_over_time.png`: biểu đồ anomaly score theo thời gian.
- API FastAPI với endpoint `/health`, `/model-info`, `/detect-anomaly`.

## Project này chưa phải production system

Project hiện tại là lab học tập, không phải hệ thống production. Các phần đã đủ tốt cho mục tiêu giảng dạy:

- Pipeline chạy được từ data đến API.
- Code gọn, dễ đọc.
- Có notebook và script tương ứng.
- Có output để kiểm tra kết quả.

Các phần cần nâng cấp nếu muốn dùng gần production:

- Lưu score distribution và threshold calibration cùng model.
- Đồng bộ cách chuẩn hóa score giữa training và API.
- Validate input API chặt hơn, đặc biệt số lượng history tối thiểu và timestamp lỗi.
- Thêm database hoặc message queue để log event.
- Thêm cooldown, deduplication và aggregation để tránh alert fatigue.
- Thêm monitoring data drift và model drift.
- Tách config thay vì hard-code threshold, device_id, model version.

## Nhận xét kỹ thuật

- Thiết kế hiện tại đúng hướng cho lab: model không trả quyết định cuối cùng trực tiếp, mà đi qua event layer.
- `train_anomaly.py` đang dùng threshold theo quantile trên tập test để demo. Trong thực tế nên chọn threshold trên validation set hoặc historical calibration set.
- `app.py` dùng sigmoid trên raw score để chuẩn hóa API score, trong khi training dùng min-max theo test raw scores. Hai cách này không đồng nhất.
- Autoencoder demo giúp sinh viên hiểu reconstruction error, nhưng chưa được tích hợp vào API.
- Event decision hiện là rule-based đơn giản. Đây là lựa chọn hợp lý cho lab, nhưng cần policy rõ hơn nếu dùng thật.

## Đề xuất cải tiến ngắn hạn

1. Lưu một object model artifact gồm scaler, detector, threshold, score min/max hoặc quantile calibration.
2. Dùng cùng một hàm scoring cho cả training và API.
3. Thêm response lỗi HTTP rõ ràng thay vì trả JSON thường khi model chưa load.
4. Thêm test tự động cho schema response `/detect-anomaly`.
5. Viết tài liệu vận hành: chạy train, chạy API, đọc output, debug lỗi thường gặp.
