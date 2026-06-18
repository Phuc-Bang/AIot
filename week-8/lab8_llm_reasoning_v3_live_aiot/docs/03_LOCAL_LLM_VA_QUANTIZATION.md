# Local LLM và quantization

## Gợi ý model cho laptop
- qwen3:0.6b: máy yếu, test pipeline.
- qwen3:1.7b: mặc định cho lớp.
- qwen3:4b: máy mạnh hơn.
- gemma3:1b: nhẹ.
- gemma3:4b: có text-image trên Ollama.
- gemma3:1b-it-qat hoặc 4b-it-qat: trải nghiệm quantization-aware trained model.

Tìm GGUF: dùng từ khóa `Qwen3 1.7B GGUF Q4_K_M`, `Gemma 3 1B GGUF Q5_K_M`.

## Chạy mode=local từng bước
1. Cài Ollama (https://ollama.com), kiểm tra `ollama --version`.
2. Tải model: `ollama pull qwen3:1.7b` (Ollama chạy nền ở `http://localhost:11434`).
3. Cấu hình `.env`:
   ```ini
   OLLAMA_BASE_URL=http://localhost:11434
   OLLAMA_MODEL=qwen3:1.7b
   OLLAMA_THINK=false          # tắt "thinking" của qwen3/gemma3 → nhanh hơn nhiều
   LLM_TEMPERATURE=0.2
   LLM_NUM_CTX=4096
   LLM_TIMEOUT_SEC=60          # tăng lên 120 nếu chạy model 4B trên CPU
   ```
4. Trên dashboard chọn `LLM mode = local - Ollama` → `So sánh 3 tầng` (hoặc `GET /reason/{id}?mode=local`).
5. Nếu Ollama tắt hoặc model chưa tải → tự fallback mock (`provider=local-failed-fallback-mock`), lab vẫn chạy.

> **Lưu trữ model sang ổ khác** (đỡ chật ổ C): đặt biến môi trường `OLLAMA_MODELS=D:\ollama\models` (lưu vĩnh viễn cho user) rồi khởi động lại `ollama serve`.
>
> **Chống lỗi JSON sai schema:** `call_ollama` truyền JSON schema vào `format` (structured output của Ollama), ép cả model nhỏ trả đúng 7 trường. Model nhỏ bật "thinking" rất chậm trên máy ít VRAM → nên để `OLLAMA_THINK=false`.

## Quantization (vì sao cần)
- Lượng tử hóa nén trọng số (FP16 → 4/5/8-bit) để model chạy nhẹ trên laptop, đổi lại độ chính xác giảm nhẹ.
- Chọn mức: `Q4_K_M` (nhẹ nhất), `Q5_K_M` (cân bằng), `Q8_0` (máy mạnh). `QAT` = quantization-aware training, giữ chất lượng tốt hơn ở bit thấp.
- Đặt file GGUF tự tải vào `models/pretrained/`. Ưu tiên model card rõ ràng, license rõ, nhiều lượt tải.

## Local vs Cloud API
| | Local (Ollama/quantized) | Cloud API (Gemini, mode=api) |
|---|---|---|
| Cài đặt | Tải model về máy | Chỉ cần `GEMINI_API_KEY` |
| Chi phí | Miễn phí, tốn tài nguyên máy | Tính theo token |
| Riêng tư | Dữ liệu ở máy | Gửi lên Google |
| Chất lượng/đa phương thức | Phụ thuộc model nhỏ | Mạnh hơn, có **vision** thật |

Chi tiết cách thêm Gemini: xem `04_BO_SUNG_GEMINI_API_VA_MO_RONG.md`.
