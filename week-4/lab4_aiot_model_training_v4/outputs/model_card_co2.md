# Model card - UCI Occupancy Detection / CO2 Forecasting

## Bài toán
- Target: `CO2`
- Forecast horizon: 15 phút
- Đơn vị: ppm

## Model tốt nhất theo validation MAE
- Model: Ridge_alpha_1
- Test MAE: 35.0759
- Test RMSE: 45.5183
- Test MAPE: 5.47%
- Test R2: 0.9006
- Bias pred-actual: -15.4265

## Cách đọc nhanh
- MAE cho biết trung bình model lệch bao nhiêu đơn vị.
- RMSE nhạy với các lỗi lớn. Nếu RMSE cao hơn MAE nhiều, có một số thời điểm model sai mạnh.
- Bias dương nghĩa là model có xu hướng dự báo cao hơn thực tế. Bias âm nghĩa là model dự báo thấp hơn thực tế.

## Feature importance
Xem file: `outputs/feature_importance_co2.csv`.

## Câu hỏi sinh viên phải trả lời
1. Model tốt nhất có hơn Last Value baseline nhiều không?
2. Nếu không hơn nhiều, lý do có thể là gì?
3. Feature nào quan trọng nhất? Feature đó có hợp lý về mặt IoT không?
4. Có giai đoạn nào model sai nhiều hơn bình thường không?
5. Với sai số hiện tại, model có đủ an toàn để điều khiển thiết bị tự động không?
