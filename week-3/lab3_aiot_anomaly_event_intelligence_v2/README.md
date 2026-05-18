# LAB 3: Anomaly Detection & Event Intelligence cho chuỗi thời gian IoT

## 1. Mục tiêu
Project này giúp sinh viên chạy một bài mẫu hoàn chỉnh:

Telemetry public dataset → xử lý dữ liệu → train anomaly model → test model → đánh giá metric → sinh event log → deploy API `/detect-anomaly`.

## 2. Dataset
Bài mẫu dùng dataset public từ Numenta Anomaly Benchmark (NAB):

- Dataset: `ambient_temperature_system_failure.csv`
- Nguồn: https://github.com/numenta/NAB/tree/master/data/realKnownCause
- File raw: https://raw.githubusercontent.com/numenta/NAB/master/data/realKnownCause/ambient_temperature_system_failure.csv
- Label windows: https://raw.githubusercontent.com/numenta/NAB/master/labels/combined_windows.json

Nếu máy không có Internet, project sẽ dùng file sample kèm theo trong `data/`.

## 3. Cấu trúc project

```text
lab3_aiot_anomaly_event_intelligence_v2/
├─ data/                         # dữ liệu public hoặc sample fallback
├─ notebooks/                    # notebook hướng dẫn từng bước
├─ src/
│  ├─ download_data.py            # tải dữ liệu public NAB
│  ├─ train_anomaly.py            # train/test Isolation Forest + autoencoder demo
│  ├─ app.py                      # FastAPI deploy model
│  ├─ test_api.py                 # test API sau khi deploy
│  ├─ plot_results.py             # vẽ biểu đồ kết quả
│  └─ utils.py                    # hàm dùng chung
├─ models/                       # model .joblib sau khi train
├─ outputs/                      # metrics, prediction, anomaly_event_log
├─ figures/                      # biểu đồ kết quả
└─ requirements.txt
```

## 4. Cài môi trường

```bash
cd lab3_aiot_anomaly_event_intelligence_v2
python -m venv .venv
```

Windows:

```bash
.venv\Scripts\activate
```

macOS/Linux:

```bash
source .venv/bin/activate
```

Cài thư viện:

```bash
pip install -r requirements.txt
```

## 5. Chạy bài mẫu bằng script

Tải dataset public hoặc dùng fallback sample:

```bash
python src/download_data.py
```

Train, test, đánh giá model:

```bash
python src/train_anomaly.py
```

Vẽ biểu đồ:

```bash
python src/plot_results.py
```

Kết quả cần thấy:

```text
models/isolation_forest_iforest_v1.joblib
models/mlp_autoencoder_demo.joblib
outputs/iforest_metrics.json
outputs/autoencoder_metrics.json
outputs/iforest_test_predictions.csv
outputs/anomaly_event_log.csv
figures/anomaly_detection_result.png
figures/anomaly_score_over_time.png
```

## 6. Chạy notebook

```bash
jupyter notebook notebooks/01_anomaly_detection_event_intelligence.ipynb
```

Chạy từng cell từ trên xuống. Sau mỗi phần, đọc kỹ mục "Cần quan sát gì".

## 7. Deploy model bằng FastAPI

Sau khi train model xong:

```bash
uvicorn src.app:app --reload
```

Mở trình duyệt:

```text
http://127.0.0.1:8000/docs
```

Test API bằng script ở terminal khác:

```bash
python src/test_api.py
```

## 8. Kiểm tra hoàn thành

Bạn hoàn thành bài mẫu khi có đủ:

- Notebook chạy hết không lỗi.
- Có `iforest_metrics.json` và `autoencoder_metrics.json`.
- Có `anomaly_event_log.csv`.
- Có ít nhất 2 biểu đồ trong `figures/`.
- API `/health` trả `model_loaded: true`.
- API `/detect-anomaly` trả `anomaly_score`, `is_anomaly`, `severity`, `decision`.
- Bạn giải thích được: test model khác deploy model ở điểm nào.
