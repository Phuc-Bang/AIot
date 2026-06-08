# RUN GUIDE - Lab 4 v4

## 1. Chuẩn bị dữ liệu
```bash
python src/download_data.py
python src/prepare_datasets.py
```

## 2. Train model truyền thống và model ML
```bash
python src/train_classical_models.py
```

Script này train các model sau trên cả hai dataset:
- Last Value baseline
- Moving Average baseline
- Linear Regression
- Ridge Regression
- Random Forest Regressor
- Gradient Boosting Regressor

Ngoài ra script còn tuning thủ công Random Forest trên validation set và ghi `outputs/tuning_log.csv`.

## 3. Vẽ biểu đồ và so sánh
```bash
python src/plot_results.py
python src/compare_two_datasets.py
```

## 4. Chạy LSTM mở rộng
```bash
pip install -r requirements_lstm.txt
python src/train_lstm.py --datasets appliances --epochs 12
```

LSTM không phải phần bắt buộc. Sinh viên khá/giỏi dùng để khám phá mô hình chuỗi thời gian sâu hơn. Mặc định script chạy LSTM trên dataset Appliances; muốn thử cả CO2 thì dùng `--datasets appliances,co2`.

## 5. Kiểm tra nhanh
```bash
python src/test_local_pipeline.py
```

Nếu thấy `LOCAL_PIPELINE_TEST_PASS`, project đã có đủ output chính.
