# Hướng dẫn chạy từng bước

1. Giải nén project.
2. Tạo môi trường ảo (`python -m venv .venv` → kích hoạt).
3. Cài requirements: `pip install -r requirements.txt` (đã gồm `python-dotenv`).
4. Chạy `python run_lab8_demo.py`. Nếu thấy `LOCAL_PIPELINE_TEST_PASS` thì nền đã chạy.
5. (Tuỳ chọn) Tạo file `.env` nếu muốn dùng LLM thật:
   - `mode=mock` chạy được ngay, **không cần** `.env`.
   - `mode=api` (Gemini): đặt `GEMINI_API_KEY=...` trong `.env` — xem `04_BO_SUNG_GEMINI_API_VA_MO_RONG.md` (mục C).
   - `mode=local` (Ollama): đặt `OLLAMA_*` trong `.env` — xem `03_LOCAL_LLM_VA_QUANTIZATION.md`.
   - App **tự nạp `.env`** lúc khởi động (qua `python-dotenv`), không cần `--env-file`.
6. Chạy `uvicorn app:app --reload --host 0.0.0.0 --port 8000`.
7. Mở `http://127.0.0.1:8000/`.
8. Chọn kịch bản, bấm `Next step` hoặc `Start timeline`.
9. Chỉnh sensor bằng slider và bấm `Apply sensors`.
10. Chọn `LLM mode` (mock / local / api) rồi bấm `So sánh 3 tầng` để thấy khác biệt giữa không có AI model, có AI model, và có LLM.

## Các nút mở rộng trên dashboard
- **So sánh model**: chạy mock/local/api song song trên cùng telemetry (latency + token + risk).
- **Giải thích trực tiếp (stream)**: Gemini sinh giải thích theo thời gian thực (mode=api).
- **Vision reason (ảnh)**: chọn 1 ảnh rồi gửi vào Gemini để reasoning trên ảnh thật (mode=api).

## Đánh giá định lượng (tuỳ chọn)
- `python eval_harness.py` (mock, miễn phí) hoặc `python eval_harness.py --modes mock,api` (chấm cả Gemini).
- Kết quả: accuracy/độ lệch từng tầng, số lần LLM đổi quyết định; xuất `outputs/eval_report.csv`.
