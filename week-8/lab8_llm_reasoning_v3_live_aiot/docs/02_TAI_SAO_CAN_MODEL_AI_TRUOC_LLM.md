# Vì sao có LLM rồi vẫn cần các model AI trước đó?

LLM là lớp reasoning. Các model anomaly, forecasting và vision là lớp evidence.

- Lab 3 tạo anomaly evidence.
- Lab 4 tạo forecast evidence.
- Lab 6 tạo camera/motion/metadata evidence.
- Lab 7 tạo vision/class/confidence/bbox evidence.

Không có evidence tốt, LLM chỉ đọc dữ liệu thô và dễ suy đoán.

## LLM thật (mode=api) cũng không thay thế các model trước
Trong bản mở rộng, `mode=api` gọi **Google Gemini** thật và `/vision-reason` có thể gửi **ảnh** vào Gemini (đa phương thức). Dù vậy:

- Gemini vẫn nhận **context packet** chứa evidence từ Lab 3/4/6/7 — nó *reasoning trên bằng chứng*, không tự sinh anomaly/forecast.
- Ngay cả vision của Gemini cũng chỉ mô tả ảnh tại một thời điểm; nó **không thay** pipeline phát hiện/đo đạc liên tục của Lab 6/7.
- Sau khi LLM trả kết quả, **safety gate** vẫn chặn điều khiển và ép human review khi confidence thấp/mâu thuẫn.

Có thể kiểm chứng định lượng bằng `eval_harness.py`: tầng *sensor + AI models* thường chính xác hơn *sensor only*, cho thấy evidence của các lab trước là cần thiết trước khi đưa vào LLM.
