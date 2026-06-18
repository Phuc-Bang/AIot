# Lab 8 v3 - LLM Reasoning & Context-aware Decision for AIoT

## Chạy nhanh

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate
pip install -r requirements.txt
python run_lab8_demo.py
uvicorn app:app --reload --host 0.0.0.0 --port 8000
```

Mở trình duyệt: http://127.0.0.1:8000/

## Ý tưởng chính

Dashboard có ba tầng so sánh:

1. Sensor only: chỉ cảm biến và rule cứng.
2. Sensor + AI models: thêm evidence từ Lab 3 anomaly, Lab 4 forecasting, Lab 6 motion/camera, Lab 7 vision.
3. Sensor + AI models + LLM: LLM tổng hợp context, giải thích, trả JSON decision, sau đó safety gate kiểm tra.

## Chế độ chạy LLM

- `mock`: luôn chạy được, không cần Internet/API key/Ollama.
- `local`: gọi Ollama tại `http://localhost:11434`, ví dụ model `qwen3:1.7b`.
- `api`: gọi Google Gemini qua REST API với structured JSON output. Cần đặt `GEMINI_API_KEY` trong `.env`; model mặc định `gemini-2.5-flash`. Nếu thiếu key hoặc lỗi mạng, tự fallback về `mock` (lab vẫn chạy).

## Tính năng mở rộng

**Nhóm A — chiều sâu AI/LLM**
- **Vision thật**: tải ảnh lên (nút "Vision reason") → mode `api` gửi ảnh vào Gemini (đa phương thức) để đưa vào reasoning. `POST /vision-reason/{id}?mode=api`.
- **Streaming**: nút "Giải thích trực tiếp" hiển thị Gemini sinh chữ theo thời gian thực (SSE). `GET /reason-stream/{id}?mode=api`.
- **So sánh model**: nút "So sánh model" chạy mock/local/api song song trên cùng telemetry. `GET /compare-models/{id}?modes=mock,local,api`.

**Nhóm C — đánh giá & giảng dạy**
- **Theo dõi token**: usageMetadata của Gemini (prompt/output/total tokens) ghi vào `outputs/latency_report.csv`.
- **Ground-truth**: nhãn risk "đúng" cho từng bước timeline (`GROUND_TRUTH` trong `app.py`).
- **Harness đánh giá**: `python eval_harness.py [--modes mock,api]` → đo accuracy/mean-gap từng tầng, số lần LLM đổi quyết định, latency; xuất `outputs/eval_report.csv`.
