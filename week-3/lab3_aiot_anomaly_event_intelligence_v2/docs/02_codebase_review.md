# 02 Codebase Review

## Cách đọc project

Thứ tự đọc khuyến nghị:

1. `README.md` để hiểu mục tiêu và command chạy.
2. `notebooks/01_anomaly_detection_event_intelligence.ipynb` để học từng bước.
3. `src/utils.py` để hiểu data, feature và event utility.
4. `src/train_anomaly.py` để hiểu training pipeline.
5. `src/app.py` để hiểu deploy API.
6. `src/test_api.py`, `src/test_api_local.py`, `src/plot_results.py` để hiểu kiểm thử và artifact.

## `data/`

### Vai trò

Chứa dữ liệu đầu vào cho lab. Project hiện có:

- `ambient_temperature_system_failure_labeled.csv`
- `sample_ambient_temperature_system_failure.csv`

### Input

- Dữ liệu public NAB tải từ GitHub.
- File sample fallback nếu không có Internet.

### Output

- CSV có schema chính: `timestamp`, `value`, `label`.

### Phụ thuộc

- `src/download_data.py` ghi vào thư mục này.
- `src/utils.py` đọc dữ liệu từ thư mục này.
- `src/train_anomaly.py`, notebook và test API phụ thuộc dữ liệu này.

### Nên đọc phần nào trước

Mở vài dòng đầu của CSV để nắm schema. Sau đó đọc `load_dataset()` trong `src/utils.py`.

## `notebooks/`

### Vai trò

Chứa notebook hướng dẫn từng bước cho sinh viên. Notebook giải thích pipeline từ nạp data, vẽ dữ liệu, tạo feature, train model, đánh giá, tạo event và deploy API.

### Input

- Dataset trong `data/`.
- Utility trong `src/utils.py`.

### Output

- Model `.joblib`.
- Metrics JSON.
- Prediction CSV.
- Event log CSV.
- Biểu đồ.

### Phụ thuộc

- Phụ thuộc `src/utils.py`.
- Có logic tương đương `src/train_anomaly.py`.

### Nên đọc phần nào trước

Đọc các section:

- `Nạp dataset public`
- `Tạo feature cho anomaly model`
- `Train baseline model: Isolation Forest`
- `Từ model output sang AIoT event`
- `Test model trong notebook khác deploy model như thế nào`
- `Deploy API /detect-anomaly`

## `src/download_data.py`

### Vai trò

Tải dataset NAB và file label windows từ GitHub. Nếu tải label được, script gắn `label = 1` cho các khoảng anomaly. Nếu không tải được public data, script dùng sample local.

### Input

- `RAW_DATA_URL`: file telemetry NAB.
- `LABELS_URL`: file `combined_windows.json`.
- `data/sample_ambient_temperature_system_failure.csv` nếu fallback.

### Output

- `data/ambient_temperature_system_failure.csv`
- `data/ambient_temperature_system_failure_labeled.csv`

### Phụ thuộc

- `src/train_anomaly.py` cần file labeled.
- Notebook cần file labeled.
- `src/test_api.py` và `src/test_api_local.py` dùng file labeled hoặc sample.

### Nên đọc phần nào trước

Đọc `main()` để hiểu cách label được gắn theo window thời gian.

### Nhận xét kỹ thuật

- Fallback sample giúp lab chạy được trong lớp học khi mạng không ổn định.
- Script đang catch exception rộng. Với production nên log lỗi rõ hơn và phân biệt lỗi mạng, lỗi parse JSON, lỗi schema.

## `src/utils.py`

### Vai trò

Đây là file nền tảng của project. Nó chứa:

- Đường dẫn project.
- Hàm load dataset.
- Feature engineering.
- Danh sách `FEATURE_COLUMNS`.
- Split train/test theo thời gian.
- Sinh event từ model output.
- Đánh giá metric.
- Tạo sliding windows cho autoencoder.
- Lưu JSON.

### Input

- CSV telemetry.
- DataFrame đã có `timestamp`, `value`, tùy chọn `label`.
- Prediction DataFrame có `anomaly_score`, `is_anomaly`.

### Output

- DataFrame đã chuẩn hóa.
- DataFrame đã có feature.
- Train/test DataFrame.
- Event DataFrame.
- Metric dictionary.

### Phụ thuộc

- `src/train_anomaly.py` dùng gần như toàn bộ utility.
- `src/app.py` dùng `FEATURE_COLUMNS`, `MODEL_DIR`, `OUTPUT_DIR`, `add_time_features()`.
- Notebook dùng các hàm này để giải thích pipeline.

### Nên đọc phần nào trước

Đọc theo thứ tự:

1. `load_dataset()`
2. `add_time_features()`
3. `FEATURE_COLUMNS`
4. `time_split()`
5. `build_events()`
6. `evaluate_detection()`

### Nhận xét kỹ thuật

- `add_time_features()` là contract quan trọng giữa training và API. Nếu sửa feature ở đây, phải retrain model.
- `build_events()` đang hard-code `device_id`. Với hệ thống thật, nên lấy device_id từ data.
- `mean_squared_error` được import nhưng không dùng trong file này.

## `src/train_anomaly.py`

### Vai trò

Train và test model. File này là pipeline ML chính.

Nó có hai nhánh:

- `train_isolation_forest()`: baseline anomaly detection chính.
- `train_neural_autoencoder_demo()`: demo autoencoder bằng `MLPRegressor`.

### Input

- Dataset từ `load_dataset()`.
- Feature từ `add_time_features()`.
- `FEATURE_COLUMNS`.

### Output

- `models/isolation_forest_iforest_v1.joblib`
- `models/mlp_autoencoder_demo.joblib`
- `outputs/iforest_metrics.json`
- `outputs/autoencoder_metrics.json`
- `outputs/iforest_test_predictions.csv`
- `outputs/autoencoder_test_predictions.csv`
- `outputs/anomaly_event_log.csv`

### Phụ thuộc

- `src/app.py` phụ thuộc model Isolation Forest được lưu.
- `src/plot_results.py` phụ thuộc `iforest_test_predictions.csv`.
- `src/test_api.py` cần model đã train để `/health` báo `model_loaded: true`.

### Nên đọc phần nào trước

Đọc `train_isolation_forest()` trước. Sau khi hiểu baseline, đọc `train_neural_autoencoder_demo()`.

### Nhận xét kỹ thuật

- Training ưu tiên dữ liệu normal nếu label có sẵn. Đây là cách đúng cho anomaly detection.
- Threshold hiện lấy quantile 0.92 trên score tập test. Với production nên chọn threshold trên validation set hoặc dữ liệu calibration riêng.
- Model artifact chỉ lưu pipeline sklearn, chưa lưu threshold và score calibration metadata.
- `mean_squared_error`, `PROJECT_ROOT`, `DATA_DIR` được import nhưng không cần thiết trong file hiện tại.

## `src/app.py`

### Vai trò

Deploy model Isolation Forest bằng FastAPI. File này biến model đã train thành service HTTP.

Endpoint:

- `GET /health`
- `GET /model-info`
- `POST /detect-anomaly`

### Input

- `models/isolation_forest_iforest_v1.joblib`
- `outputs/iforest_metrics.json`
- JSON request chứa `history` telemetry.

### Output

- JSON health status.
- JSON model info.
- JSON anomaly detection result gồm `model_output`, `event`, `api_check`.

### Phụ thuộc

- Cần model từ `src/train_anomaly.py`.
- Dùng feature từ `src/utils.py`.
- Được test bởi `src/test_api.py` và `src/test_api_local.py`.

### Nên đọc phần nào trước

Đọc theo thứ tự:

1. `TelemetryPoint`
2. `AnomalyRequest`
3. `decision_from_score()`
4. `/health`
5. `/model-info`
6. `/detect-anomaly`

### Nhận xét kỹ thuật

- API load model khi module được import. Nếu model chưa tồn tại lúc start, cần restart API sau khi train.
- API trả `{"error": ...}` với HTTP 200 khi thiếu model. Production nên dùng HTTP 503 hoặc 500.
- API không enforce tối thiểu 36 điểm history dù description khuyến nghị.
- API dùng `p.dict()`. Với Pydantic v2 nên cân nhắc `model_dump()`.
- Score normalization trong API chưa đồng nhất với training.

## `src/test_api.py`

### Vai trò

Test API thật qua HTTP. Script đọc 40 dòng cuối của dataset, gọi `/health`, `/model-info`, `/detect-anomaly` trên `http://127.0.0.1:8000`.

### Input

- API FastAPI đang chạy.
- Dataset trong `data/`.

### Output

- In JSON response ra terminal.

### Phụ thuộc

- Cần `uvicorn src.app:app --reload` đang chạy.
- Cần model đã train.

### Nên đọc phần nào trước

Đọc cách tạo `history` và cách gọi `requests.post()`.

### Nhận xét kỹ thuật

- Phù hợp smoke test thủ công.
- Chưa assert schema hoặc status code. `test_api_local.py` kiểm tra schema tốt hơn.

## `src/test_api_local.py`

### Vai trò

Test logic FastAPI bằng `TestClient` mà không cần mở port. Phù hợp khi máy học viên bị chặn port hoặc muốn kiểm tra nhanh response schema.

### Input

- `app` từ `src/app.py`.
- Dataset trong `data/`.

### Output

- In response.
- Assert có `model_output`, `event`, `anomaly_score`, `decision`.

### Phụ thuộc

- Cần model đã train để response có ý nghĩa.
- Import `app.py`, nên phụ thuộc cách app load model.

### Nên đọc phần nào trước

Đọc phần assert cuối file để hiểu schema tối thiểu API phải giữ.

### Nhận xét kỹ thuật

- Đây là test hữu ích nhất để giữ contract response.
- Nên chuyển thành test framework như `pytest` nếu phát triển tiếp.

## `src/plot_results.py`

### Vai trò

Vẽ biểu đồ kết quả Isolation Forest.

### Input

- `outputs/iforest_test_predictions.csv`

### Output

- `figures/anomaly_detection_result.png`
- `figures/anomaly_score_over_time.png`

### Phụ thuộc

- Cần chạy `src/train_anomaly.py` trước.
- Output dùng trong báo cáo, notebook, docs hoặc thuyết trình.

### Nên đọc phần nào trước

Đọc đoạn lọc `df[df["is_anomaly"] == 1]` để hiểu cách điểm anomaly được highlight.

### Nhận xét kỹ thuật

- Biểu đồ đủ cho lab.
- Nếu dùng vận hành thật, cần dashboard cập nhật theo thời gian và zoom theo device/time range.

## `models/`

### Vai trò

Lưu model sau train.

### Input

- Output của `src/train_anomaly.py`.

### Output

- `.joblib` model artifact.

### Phụ thuộc

- `src/app.py` load `isolation_forest_iforest_v1.joblib`.

### Nên đọc phần nào trước

Không đọc trực tiếp bằng text. Hiểu cách tạo trong `train_anomaly.py` và cách load trong `app.py`.

## `outputs/`

### Vai trò

Lưu kết quả đánh giá và prediction.

### Input

- Output của model trên tập test.
- Event từ `build_events()`.

### Output

- Metrics JSON.
- Prediction CSV.
- Event log CSV.

### Phụ thuộc

- `src/plot_results.py` đọc prediction.
- `src/app.py` đọc metrics cho `/model-info`.

### Nên đọc phần nào trước

Đọc `iforest_metrics.json`, sau đó mở `anomaly_event_log.csv`.

## `figures/`

### Vai trò

Lưu hình ảnh kết quả để quan sát trực quan.

### Input

- `outputs/iforest_test_predictions.csv`.

### Output

- Biểu đồ PNG.

### Phụ thuộc

- Dùng cho báo cáo và notebook.

### Nên đọc phần nào trước

Xem `anomaly_detection_result.png` để hiểu model bắt điểm nào.

## `requirements.txt`

### Vai trò

Khai báo thư viện Python cần cài.

### Input

- Không có.

### Output

- Môi trường chạy project sau khi `pip install -r requirements.txt`.

### Phụ thuộc

- Tất cả script Python và notebook.

### Nên đọc phần nào trước

Đọc trước khi tạo môi trường để biết project dùng pandas, numpy, scikit-learn, matplotlib, FastAPI, uvicorn, requests và Jupyter.

## Tổng nhận xét codebase

Codebase gọn và hợp lý cho lab. Điểm mạnh là có đủ vòng đời: data, train, evaluate, event, plot, API, test. Điểm cần nâng nếu phát triển tiếp là chuẩn hóa model artifact, tách scoring dùng chung, thêm config, test tự động và event storage.
