# Lab 4 v4 Upgrade: AI Model Training for IoT Forecasting

## Mục tiêu
Lab này tập trung vào **model AI** thay vì đi nhanh sang API. Sinh viên học cách biến dữ liệu IoT thành bài toán học máy, train model, test model, đọc metric, tinh chỉnh tham số và so sánh hành vi model trên hai dataset.

## Hai dataset
1. **UCI Appliances Energy Prediction**: dự báo `Appliances` trong tương lai gần.
2. **UCI Occupancy Detection / CO2 Forecasting**: dùng dữ liệu môi trường phòng để dự báo `CO2` trong tương lai gần.

Nếu có Internet, chạy `python src/download_data.py` để tải dữ liệu từ UCI. Nếu không có Internet, project tự dùng dữ liệu sample trong `data/sample/` để toàn bộ pipeline vẫn chạy được.

## Cài đặt
```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate
pip install -r requirements.txt
```

Nếu muốn chạy LSTM:
```bash
pip install -r requirements_lstm.txt
```

## Chạy nhanh toàn bộ phần bắt buộc
```bash
python src/download_data.py
python src/prepare_datasets.py
python src/train_classical_models.py
python src/plot_results.py
python src/compare_two_datasets.py
python src/test_local_pipeline.py
```

## Chạy phần khám phá LSTM
```bash
python src/train_lstm.py --datasets appliances --epochs 12
```

## Output chính
```text
outputs/metrics_all_models.csv
outputs/model_comparison.csv
outputs/tuning_log.csv
outputs/predictions_appliances.csv
outputs/predictions_co2.csv
outputs/lstm_metrics.csv                 # nếu chạy LSTM
outputs/model_card_appliances.md
outputs/model_card_co2.md
figures/model_comparison_mae.png
figures/forecast_vs_actual_appliances.png
figures/forecast_vs_actual_co2.png
figures/error_over_time_appliances.png
figures/error_over_time_co2.png
```

## Câu hỏi trung tâm
- Model AI học gì từ dữ liệu IoT?
- Vì sao cần baseline trước khi dùng model phức tạp?
- Vì sao train/test phải theo thời gian?
- Metric nào cho biết model sai nhiều hay ít?
- Model tốt trên một dataset có chắc tốt trên dataset khác không?
- LSTM có luôn tốt hơn Random Forest không? Vì sao?
