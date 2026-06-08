# So sánh hành vi model trên hai dataset

Bảng `model_comparison.csv` cho biết model tốt nhất theo validation MAE và kết quả trên test set.

## UCI Appliances Energy Prediction

- Target: `Appliances`; horizon: 30 phút.
- Best model by validation MAE: `GradientBoosting_advanced`.
- Test MAE: 23.4664; Last Value MAE: 27.4348.
- Improvement vs Last Value: 14.46%.

Câu hỏi: Nếu cải thiện không nhiều, có phải model AI vô dụng không? Hay Last Value là baseline rất mạnh vì chuỗi biến thiên chậm?

## UCI Occupancy Detection / CO2 Forecasting

- Target: `CO2`; horizon: 15 phút.
- Best model by validation MAE: `Ridge_alpha_1`.
- Test MAE: 35.0759; Last Value MAE: 36.1299.
- Improvement vs Last Value: 2.92%.

Câu hỏi: Nếu cải thiện không nhiều, có phải model AI vô dụng không? Hay Last Value là baseline rất mạnh vì chuỗi biến thiên chậm?

## Câu hỏi tổng hợp

1. Dataset nào Last Value baseline đã mạnh? Vì sao?
2. Dataset nào model phi tuyến cải thiện rõ hơn?
3. Nếu model phức tạp hơn nhưng test MAE không giảm, nên chọn model nào khi triển khai thật?
4. Kết quả này nói gì về việc không nên đánh giá AI chỉ bằng cảm giác?
