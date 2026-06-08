# 07 Run and Test Guide

## Hướng dẫn chạy trên Windows PowerShell

Tài liệu này giả định project nằm tại:

```powershell
E:\AIoT\Day-3\lab3_aiot_anomaly_event_intelligence_v2
```

## 1. Mở PowerShell và vào thư mục project

```powershell
cd E:\AIoT\Day-3\lab3_aiot_anomaly_event_intelligence_v2
```

Kiểm tra file:

```powershell
Get-ChildItem
```

Nên thấy:

```text
data
notebooks
src
models
outputs
figures
requirements.txt
README.md
```

## 2. Tạo virtual environment

```powershell
python -m venv .venv
```

Kích hoạt:

```powershell
.\.venv\Scripts\Activate.ps1
```

Nếu PowerShell chặn script, chạy:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

Khi activate thành công, prompt thường có `(.venv)`.

## 3. Cài dependencies

```powershell
pip install -r requirements.txt
```

Kiểm tra nhanh:

```powershell
python -c "import pandas, sklearn, fastapi; print('OK')"
```

## 4. Tải data hoặc dùng fallback sample

```powershell
python src/download_data.py
```

Kết quả mong đợi:

```text
data/ambient_temperature_system_failure_labeled.csv
```

Nếu máy không có Internet, script sẽ dùng file sample trong `data/`.

## 5. Train model

```powershell
python src/train_anomaly.py
```

Kết quả mong đợi:

```text
models/isolation_forest_iforest_v1.joblib
models/mlp_autoencoder_demo.joblib
outputs/iforest_metrics.json
outputs/autoencoder_metrics.json
outputs/iforest_test_predictions.csv
outputs/autoencoder_test_predictions.csv
outputs/anomaly_event_log.csv
```

Kiểm tra:

```powershell
Get-ChildItem models
Get-ChildItem outputs
```

## 6. Đọc metric

```powershell
Get-Content outputs/iforest_metrics.json
```

Cần chú ý:

- `precision`
- `recall`
- `f1_score`
- `confusion_matrix`
- `threshold`

Với output hiện tại, Isolation Forest có recall chưa cao. Đây là điểm tốt để thảo luận cách tune feature và threshold.

## 7. Vẽ biểu đồ kết quả

```powershell
python src/plot_results.py
```

Kết quả mong đợi:

```text
figures/anomaly_detection_result.png
figures/anomaly_score_over_time.png
```

Kiểm tra:

```powershell
Get-ChildItem figures
```

## 8. Chạy API

Mở terminal PowerShell thứ nhất:

```powershell
cd E:\AIoT\Day-3\lab3_aiot_anomaly_event_intelligence_v2
.\.venv\Scripts\Activate.ps1
uvicorn src.app:app --reload
```

Mở trình duyệt:

```text
http://127.0.0.1:8000/docs
```

Kiểm tra `/health`. Kết quả cần có:

```json
{
  "model_loaded": true
}
```

## 9. Test API bằng script

Mở terminal PowerShell thứ hai:

```powershell
cd E:\AIoT\Day-3\lab3_aiot_anomaly_event_intelligence_v2
.\.venv\Scripts\Activate.ps1
python src/test_api.py
```

Script sẽ gọi:

- `/health`
- `/model-info`
- `/detect-anomaly`

Nếu API đang chạy đúng, terminal sẽ in JSON response.

## 10. Test API không cần mở port

Nếu không muốn chạy uvicorn:

```powershell
python src/test_api_local.py
```

Cách này dùng `TestClient` để gọi app trực tiếp trong process Python.

## 11. Chạy notebook

```powershell
jupyter notebook notebooks/01_anomaly_detection_event_intelligence.ipynb
```

Chạy từng cell từ trên xuống. Notebook phù hợp để học logic, còn script phù hợp để chạy lại pipeline nhanh.

## 12. Checklist hoàn thành

Một lượt chạy thành công cần có:

- `data/ambient_temperature_system_failure_labeled.csv`
- `models/isolation_forest_iforest_v1.joblib`
- `models/mlp_autoencoder_demo.joblib`
- `outputs/iforest_metrics.json`
- `outputs/autoencoder_metrics.json`
- `outputs/iforest_test_predictions.csv`
- `outputs/autoencoder_test_predictions.csv`
- `outputs/anomaly_event_log.csv`
- `figures/anomaly_detection_result.png`
- `figures/anomaly_score_over_time.png`
- `/health` trả `model_loaded: true`
- `/detect-anomaly` trả `model_output`, `event`, `api_check`

## Lỗi thường gặp

### `ModuleNotFoundError`

Nguyên nhân: chưa activate venv hoặc chưa cài requirements.

Cách xử lý:

```powershell
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### API báo model chưa train

Nguyên nhân: chưa có file model trong `models/`.

Cách xử lý:

```powershell
python src/train_anomaly.py
```

Sau đó restart uvicorn.

### `Run python src/train_anomaly.py first`

Nguyên nhân: `src/plot_results.py` không tìm thấy `outputs/iforest_test_predictions.csv`.

Cách xử lý:

```powershell
python src/train_anomaly.py
python src/plot_results.py
```

### Không mở được Swagger UI

Nguyên nhân thường gặp:

- Uvicorn chưa chạy.
- Port 8000 bị chiếm.
- Firewall hoặc môi trường lớp học chặn port.

Cách xử lý:

```powershell
uvicorn src.app:app --reload --port 8001
```

Hoặc dùng:

```powershell
python src/test_api_local.py
```

## Nhận xét kỹ thuật

- Thứ tự chạy quan trọng: data -> train -> plot -> API -> test.
- API load model lúc start, nên train xong cần restart API nếu trước đó API đang chạy.
- Khi thay feature trong `utils.py`, phải train lại model. Model cũ không còn tương thích feature mới.
