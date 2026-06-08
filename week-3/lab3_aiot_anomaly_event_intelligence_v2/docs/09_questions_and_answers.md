# 09 Questions and Answers

## 1. Lab 3 phát hiện bất thường hay dự báo tương lai?

Lab 3 phát hiện bất thường, không dự báo tương lai.

Model trả lời câu hỏi:

```text
Điểm telemetry hiện tại có khác pattern bình thường đã học không?
```

Model không trả lời:

```text
Nhiệt độ 10 phút tới sẽ là bao nhiêu?
```

Autoencoder demo cũng không dự báo tương lai. Nó học tái tạo lại window đầu vào. Nếu tái tạo kém, MSE cao, window đó có thể bất thường.

## 2. Vì sao không random split?

Vì đây là time-series. Random split sẽ trộn quá khứ và tương lai, gây data leakage.

Trong thực tế:

```text
model chỉ được học từ quá khứ để đánh giá tương lai
```

Nếu random split, model có thể được train trên pattern xảy ra sau thời điểm test. Metric sẽ thiếu trung thực.

Ngoài ra, feature rolling phụ thuộc thứ tự thời gian. Trộn dữ liệu làm mất ngữ cảnh vận hành.

## 3. If-else threshold có đủ không?

Có thể đủ cho bài toán rất đơn giản, ví dụ:

```text
nếu nhiệt độ > 80 độ C thì cảnh báo
```

Nhưng if-else cố định thường không đủ khi:

- Dữ liệu có pattern theo giờ.
- Mức bình thường thay đổi theo thiết bị.
- Cần phát hiện nhảy đột ngột dù giá trị vẫn trong ngưỡng.
- Sensor có thể bị kẹt.
- Bất thường phụ thuộc rolling context.

Trong project này, rule threshold vẫn được dùng ở event layer. Điểm khác là threshold không áp trực tiếp lên raw value, mà áp lên score và context sau khi model đã học pattern.

## 4. Anomaly detection hơn if-else ở đâu?

Anomaly detection học hành vi bình thường từ dữ liệu. Nó có thể phát hiện các trường hợp if-else khó viết:

- Giá trị không vượt ngưỡng vật lý nhưng lệch khỏi pattern gần đây.
- Tăng giảm đột ngột so với các điểm trước.
- Pattern bất thường theo giờ/ngày.
- Tổ hợp nhiều feature cùng đáng nghi.

Ví dụ:

```text
Nhiệt độ 26 độ C không cao.
Nhưng nếu 3 giờ gần nhất quanh 18 độ C và đột ngột lên 26 độ C,
đó có thể là anomaly.
```

If-else vẫn quan trọng cho safety rule. Cách tốt là kết hợp:

```text
ML anomaly score + rule vật lý + event policy
```

## 5. Precision thấp nguy hiểm như nào?

Precision thấp nghĩa là trong các cảnh báo model tạo ra, nhiều cảnh báo là sai.

Hậu quả:

- Người vận hành mất niềm tin.
- Dashboard bị nhiễu.
- Ticket bảo trì bị tạo quá nhiều.
- Chi phí xử lý tăng.
- Alert quan trọng có thể bị bỏ qua vì quá nhiều alert sai.

Trong hệ thống sản xuất, precision thấp gây alert fatigue.

## 6. Recall thấp nguy hiểm như nào?

Recall thấp nghĩa là trong các anomaly thật, model bỏ sót nhiều.

Hậu quả:

- Sự cố không được cảnh báo.
- Thiết bị có thể hỏng nặng hơn.
- Mất cơ hội bảo trì sớm.
- Rủi ro an toàn tăng.
- Hệ thống nhìn có vẻ yên ổn nhưng thực tế đang bỏ sót vấn đề.

Trong output hiện tại, Isolation Forest có recall 0.439, nghĩa là còn bỏ sót đáng kể theo label.

## 7. False alert và missed alert cái nào nguy hiểm hơn?

Không có câu trả lời chung. Phụ thuộc bài toán.

False alert nguy hiểm khi:

- Cảnh báo nhiều làm người vận hành mất niềm tin.
- Hệ thống tự động dừng thiết bị gây gián đoạn.
- Chi phí kiểm tra mỗi alert cao.

Missed alert nguy hiểm khi:

- Thiết bị liên quan an toàn.
- Sự cố gây thiệt hại lớn.
- Cần phát hiện sớm để tránh hỏng hóc.
- Dữ liệu liên quan y tế, năng lượng, kho lạnh, dây chuyền sản xuất.

Trong AIoT, thường cần phân loại theo severity:

```text
LOW: ưu tiên precision
HIGH/CRITICAL: ưu tiên recall và safety
```

## 8. Test notebook khác deploy API như nào?

Notebook test model offline:

- Chạy trên tập test nhiều dòng.
- Có label để tính metric.
- Có biểu đồ.
- Có event log.
- Mục tiêu là đánh giá chất lượng model.

API deploy online:

- Nhận telemetry mới qua HTTP.
- Thường không có label ngay.
- Trả JSON cho hệ thống khác.
- Mục tiêu là tích hợp model vào backend AIoT.

Bảng so sánh:

| Tiêu chí | Notebook/test offline | API deploy |
| --- | --- | --- |
| Dữ liệu | Tập test có sẵn | Request mới |
| Label | Có thể có | Thường không có |
| Output | Metric, chart, CSV | JSON response |
| Mục tiêu | Đánh giá model | Tích hợp hệ thống |
| Vấn đề chính | Model quality | Contract, latency, reliability |

## 9. Vì sao có anomaly_score nhưng vẫn cần severity?

Vì score là tín hiệu model, còn severity là mức độ nghiêm trọng vận hành.

Score không biết:

- Thiết bị nào quan trọng.
- Bối cảnh sản xuất.
- Ngưỡng an toàn vật lý.
- Sự kiện có kéo dài không.
- Có nhiều sensor cùng xác nhận không.

Severity là cách backend biến score thành ngôn ngữ vận hành.

## 10. Vì sao có severity nhưng vẫn cần decision?

Severity nói sự kiện nghiêm trọng đến đâu. Decision nói hệ thống sẽ làm gì.

Ví dụ:

```text
severity = HIGH
decision = CREATE_ALERT_AND_REQUIRE_HUMAN_CHECK
```

Cùng severity `HIGH`, decision có thể khác nhau nếu thiết bị đang bảo trì, nếu operator đã acknowledge, hoặc nếu alert đang trong cooldown.

## 11. Tại sao API cần history chứ không chỉ một điểm?

Vì feature rolling cần dữ liệu gần đây:

- `rolling_mean_12`
- `rolling_std_12`
- `rolling_mean_36`
- `delta_1`
- `delta_3`
- `zscore_rolling`

Nếu chỉ gửi một điểm, API vẫn tính được một số feature nhờ `min_periods`, nhưng score sẽ kém tin cậy vì thiếu context.

## 12. Kết quả model có phải xác suất không?

Không. `anomaly_score` trong project là điểm bất thường được normalize để dễ hiểu. Nó không phải xác suất "thiết bị hỏng".

Với Isolation Forest:

- Raw score đến từ cơ chế isolation.
- Code đảo dấu để score cao hơn nghĩa là bất thường hơn.
- Training normalize min-max theo tập test.
- API hiện dùng sigmoid cho demo.

Vì vậy cần cẩn thận khi diễn giải score.

## 13. Khi nào nên retrain model?

Nên retrain khi:

- Thay feature.
- Thay dataset.
- Thêm sensor mới.
- Distribution dữ liệu thay đổi.
- Alert quá nhiều hoặc bỏ sót nhiều.
- Có feedback label mới từ vận hành.
- Model version cũ không còn phù hợp.

Trong project này, nếu sửa `FEATURE_COLUMNS` hoặc `add_time_features()`, bắt buộc train lại.

## 14. Code hiện tại có vấn đề gì đáng chú ý?

Có vài điểm cần ghi nhớ:

- Training và API normalize score khác nhau.
- Threshold training chưa được lưu trong model artifact.
- API không enforce số điểm history tối thiểu.
- API trả lỗi thiếu model bằng HTTP 200.
- `device_id` trong event log batch đang hard-code.
- Autoencoder demo chưa được deploy.

Các điểm này bình thường với lab, nhưng cần sửa nếu phát triển tiếp.

## 15. Nên học file nào trước?

Thứ tự học tốt nhất:

1. `README.md`
2. `notebooks/01_anomaly_detection_event_intelligence.ipynb`
3. `src/utils.py`
4. `src/train_anomaly.py`
5. `src/app.py`
6. `outputs/iforest_metrics.json`
7. `outputs/anomaly_event_log.csv`

Đọc theo thứ tự này sẽ giúp hiểu từ bài toán đến data, model, event và API.
