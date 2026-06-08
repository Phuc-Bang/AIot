# 04 Model Training Review

## File training chính

Training pipeline nằm trong:

```text
src/train_anomaly.py
```

File này gọi utility từ `src/utils.py` để:

- Load dataset.
- Tạo feature.
- Split train/test theo thời gian.
- Train model.
- Tính score.
- Đánh giá metric.
- Lưu model và output.
- Tạo event log.

## Isolation Forest dùng để làm gì?

Isolation Forest là baseline model cho anomaly detection. Ý tưởng chính:

- Điểm bình thường thường nằm trong vùng dữ liệu dày đặc.
- Điểm bất thường thường dễ bị tách ra hơn.
- Model xây nhiều cây ngẫu nhiên để đo mức độ "dễ cô lập" của một điểm.

Trong project này, Isolation Forest học pattern bình thường của telemetry nhiệt độ từ các feature:

```text
value, hour, dayofweek, rolling_mean_12, rolling_std_12,
rolling_mean_36, delta_1, delta_3, zscore_rolling, is_stuck_candidate
```

Model không dự báo nhiệt độ tương lai. Nó đánh giá điểm hiện tại có giống pattern bình thường đã học hay không.

## Model học gì?

Model học phân bố hành vi bình thường:

- Nhiệt độ thường nằm trong khoảng nào.
- Nhiệt độ thay đổi nhanh hay chậm.
- Mức dao động rolling thông thường.
- Pattern theo giờ và ngày trong tuần.
- Điểm nào có z-score hoặc delta bất thường.
- Dấu hiệu sensor stuck.

Trong code, nếu có label, training ưu tiên:

```text
train_normal = train_df[train_df["label"] == 0]
```

Đây là cách hợp lý. Với anomaly detection, ta thường muốn model học normal behavior trước, sau đó điểm lệch khỏi normal sẽ bị score cao.

## Input và output của Isolation Forest

### Input

Input là DataFrame feature:

```text
test_df[FEATURE_COLUMNS]
```

Trước khi vào detector, data đi qua:

```text
StandardScaler -> IsolationForest
```

### Output raw

Isolation Forest có `score_samples()`. Trong scikit-learn, score càng thấp thì càng bất thường. Code đảo dấu:

```python
raw_scores = -model.named_steps["detector"].score_samples(...)
```

Sau khi đảo dấu:

```text
raw_score càng cao -> càng bất thường
```

### `anomaly_score`

Code normalize raw score về khoảng 0 đến 1:

```python
anomaly_score = (raw_scores - min_s) / (max_s - min_s + 1e-9)
```

Ý nghĩa trong lab:

- Gần 0: giống normal hơn.
- Gần 1: bất thường hơn.

Lưu ý: đây là score đã normalize theo tập test hiện tại. Nó không phải xác suất lỗi thật.

## Threshold được dùng ra sao?

Code chọn threshold:

```python
threshold = np.quantile(anomaly_score, 0.92)
```

Nghĩa là khoảng 8 phần trăm điểm có score cao nhất trong tập test bị đánh dấu là anomaly.

Sau đó:

```python
is_anomaly = anomaly_score >= threshold
```

Trong output hiện có, threshold Isolation Forest là:

```text
0.5956
```

## Đọc Precision, Recall, F1, Confusion Matrix

Output hiện có trong `outputs/iforest_metrics.json`:

```json
{
  "precision": 0.6429,
  "recall": 0.439,
  "f1_score": 0.5217,
  "tn": 299,
  "fp": 10,
  "fn": 23,
  "tp": 18
}
```

### Precision

Precision trả lời:

```text
Trong các cảnh báo model tạo ra, bao nhiêu phần là đúng?
```

Precision 0.6429 nghĩa là khoảng 64.29 phần trăm cảnh báo là đúng theo label.

Precision thấp dẫn đến nhiều false alert. Trong AIoT, false alert làm người vận hành mất niềm tin vào hệ thống.

### Recall

Recall trả lời:

```text
Trong các anomaly thật, model bắt được bao nhiêu phần?
```

Recall 0.439 nghĩa là model bắt được khoảng 43.9 phần trăm anomaly theo label.

Recall thấp nghĩa là bỏ sót sự cố. Với hệ thống an toàn, missed alert có thể nguy hiểm hơn false alert.

### F1-score

F1 là trung bình điều hòa của Precision và Recall. Nó hữu ích khi cần cân bằng giữa false alert và missed alert.

F1 hiện tại 0.5217 cho thấy baseline chạy được nhưng còn nhiều dư địa cải tiến.

### Confusion Matrix

Confusion matrix hiện tại:

```text
TN = 299
FP = 10
FN = 23
TP = 18
```

Ý nghĩa:

- `TN`: normal và model đoán normal.
- `FP`: normal nhưng model cảnh báo anomaly.
- `FN`: anomaly thật nhưng model bỏ sót.
- `TP`: anomaly thật và model bắt đúng.

Trong AIoT, cần phân tích FP và FN theo ngữ cảnh vận hành. Một FN trong thiết bị nguy hiểm có thể nghiêm trọng hơn nhiều FP ở cảm biến ít quan trọng.

## Autoencoder demo

Project có thêm:

```python
train_neural_autoencoder_demo(window_size=24)
```

Đây là demo autoencoder bằng `MLPRegressor`, không phải LSTM.

Ý tưởng:

```text
window dữ liệu -> autoencoder -> window tái tạo -> reconstruction MSE
```

Nếu model tái tạo kém, MSE cao. Khi MSE cao hơn threshold, điểm cuối window được coi là anomaly.

## MSE nghĩa là gì?

MSE là lỗi tái tạo trung bình:

```text
MSE cao -> window hiện tại khác pattern model đã học -> có thể bất thường
```

Trong output hiện tại:

```json
{
  "precision": 0.037,
  "recall": 0.0244,
  "f1_score": 0.0294,
  "threshold_mse": 0.378569
}
```

Kết quả này rất yếu so với Isolation Forest trong dataset hiện tại. Điều đó không có nghĩa autoencoder luôn kém. Nó cho thấy demo hiện tại chưa tune tốt và chỉ dùng `value` theo sliding window đơn giản.

## Test notebook khác train script như nào?

Notebook giúp học và quan sát từng bước. Script giúp chạy pipeline lặp lại.

Nếu phát triển tiếp, nên coi `src/train_anomaly.py` là entrypoint chính và notebook là tài liệu giải thích. Không nên để logic notebook lệch khỏi script quá xa.

## Nhận xét kỹ thuật

- Isolation Forest là baseline hợp lý cho lab vì dễ chạy, ít phụ thuộc, không cần label để train.
- Metrics hiện tại cho thấy model chưa đủ tốt cho hệ thống an toàn, đặc biệt recall còn thấp.
- Threshold chọn trên tập test chỉ phù hợp demo. Với quy trình ML nghiêm túc, test set không nên dùng để chọn threshold.
- API không dùng threshold đã lưu từ training. API dùng score sigmoid và threshold 0.55, nên kết quả online có thể không tương thích metric offline.
- Autoencoder demo hiện không được API sử dụng.

## Đề xuất cải tiến

- Tách train, validation, test theo thời gian.
- Chọn threshold trên validation set theo mục tiêu vận hành: giảm FP hay giảm FN.
- Lưu threshold và calibration metadata cùng model.
- Thêm báo cáo theo từng khoảng thời gian, không chỉ metric tổng.
- So sánh thêm rule baseline như z-score threshold để chứng minh model hơn if-else ở đâu.
- Với autoencoder, thử thêm nhiều feature, window size khác và model sequence phù hợp hơn.
