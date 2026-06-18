# 04 — Bổ sung Gemini API & các tính năng mở rộng (nhóm A & C)

> Tài liệu này bổ sung cho bản Lab 8 v3 gốc. Nó mô tả **những phần đã thêm**: tích hợp **Gemini API** thật cho `mode=api`, **vision thật**, **streaming**, **so sánh model**, **theo dõi token**, **ground-truth** và **harness đánh giá**. Dùng để viết/bổ sung vào tài liệu Word.

---

## A. Tổng quan thay đổi so với bản gốc

| Hạng mục | Bản gốc | Bản đã bổ sung |
|---|---|---|
| `mode=api` | placeholder → chạy mock | **Gọi Google Gemini thật** (REST, structured JSON), tự fallback mock nếu lỗi |
| `/vision-reason` | chỉ ghi metadata ảnh (mock) | **Vision thật**: gửi ảnh vào Gemini (đa phương thức) khi `mode=api` |
| Cấu hình | chỉ `OLLAMA_*` | thêm `GEMINI_*`, app tự nạp `.env` qua `python-dotenv` |
| Latency log | chỉ thời gian | thêm **token usage** (prompt/output/total) |
| So sánh | 3 tầng | thêm **so sánh nhiều model song song** (`/compare-models`) |
| Giải thích | trả 1 lần | thêm **streaming SSE** (`/reason-stream`) |
| Đánh giá | không có | **ground-truth + eval_harness.py** (đo accuracy/latency/đổi quyết định) |
| File mới | — | `eval_harness.py`, `.env`, `.gitignore`, `CLAUDE.md`, `outputs/eval_report.csv` |

---

## B. Hướng dẫn chạy (cập nhật mục VI)

### B1. Tạo môi trường & cài thư viện
```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS/Linux/WSL
source .venv/bin/activate
pip install -r requirements.txt
```
`requirements.txt` hiện gồm: `fastapi`, `uvicorn[standard]`, `pydantic`, `requests`, `python-multipart`, `httpx`, `python-dotenv`.

### B2. Chạy smoke test (bắt buộc)
```bash
python run_lab8_demo.py     # phải in: LOCAL_PIPELINE_TEST_PASS
```

### B3. Tạo file `.env` (chỉ cần khi dùng `mode=api` hoặc `local`)
- `mode=mock` chạy được ngay, **không cần** `.env`.
- App **tự nạp `.env`** lúc khởi động (qua `python-dotenv` — xem mục C3), không cần truyền `--env-file`.

### B4. Chạy service
```bash
uvicorn app:app --reload --host 0.0.0.0 --port 8000
```
Mở `http://127.0.0.1:8000/` (và `http://127.0.0.1:8000/docs` để xem API).

---

## C. CÁCH THÊM API (Google Gemini) — chi tiết nhất

### C1. Lấy API key
Vào **Google AI Studio**: https://aistudio.google.com/apikey → **Create API key** → bấm **Copy key**.
> Nếu key lấy từ **Google Cloud Console** (có Project number): phải **bật "Generative Language API"** cho project và đảm bảo key không bị API restrictions chặn.

### C2. Khai báo trong `.env`
Tạo file `.env` ở thư mục gốc lab (cùng cấp `app.py`):
```ini
# Cloud "api" mode — Google Gemini
GEMINI_API_KEY=<DÁN_KEY_CỦA_BẠN>
GEMINI_MODEL=gemini-2.5-flash
GEMINI_TEMPERATURE=0.2
GEMINI_TIMEOUT_SEC=60
GEMINI_THINKING_BUDGET=0
```

| Biến | Ý nghĩa | Mặc định |
|---|---|---|
| `GEMINI_API_KEY` | Khóa truy cập (bắt buộc) | (rỗng) |
| `GEMINI_MODEL` | Model Gemini | `gemini-2.5-flash` |
| `GEMINI_TEMPERATURE` | Độ "sáng tạo" | `0.2` |
| `GEMINI_TIMEOUT_SEC` | Timeout mỗi request | `60` |
| `GEMINI_THINKING_BUDGET` | `0` = tắt "thinking" (nhanh); >0 = reasoning sâu hơn (chậm hơn) | `0` |

> **Bảo mật:** `.env` đã được `.gitignore`, KHÔNG commit. Nếu key từng bị lộ (chụp màn hình, dán vào chat) → vào AI Studio **xóa và tạo key mới**.

### C3. App tự nạp `.env`
Ở đầu `app.py` (sau khi xác định `APP_DIR`):
```python
APP_DIR = Path(__file__).resolve().parent
try:
    from dotenv import load_dotenv
    load_dotenv(APP_DIR / '.env')   # nạp GEMINI_API_KEY, OLLAMA_*, ...
except Exception:
    pass
```

### C4. Cơ chế hoạt động
```
mode=api ──▶ call_gemini(context, image?)
              │  POST https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent
              │  header: x-goog-api-key: <KEY>
              │  body:   systemInstruction + contents + generationConfig{
              │            responseMimeType:"application/json", responseSchema, thinkingConfig}
              ▼
            JSON đúng GEMINI_DECISION_SCHEMA ──▶ validate_llm_output() ──▶ apply_safety_gate() ──▶ final_decision
  (mọi lỗi: thiếu key / mạng / 4xx ──▶ except ──▶ fallback mock + need_human_review=True)
```
Điểm mấu chốt: **structured output** (`responseMimeType=application/json` + `responseSchema`) bắt Gemini chỉ trả JSON đúng 7 trường + `risk_level` thuộc {LOW,MEDIUM,HIGH,CRITICAL}, nên backend luôn parse/validate được.

### C5. Code chính (`call_gemini` trong `app.py`)
Schema (lưu ý Gemini dùng **type CHỮ HOA**, KHÔNG có `additionalProperties`):
```python
GEMINI_DECISION_SCHEMA = {
    'type': 'OBJECT',
    'properties': {
        'situation_summary': {'type': 'STRING'},
        'risk_level': {'type': 'STRING', 'enum': ['LOW','MEDIUM','HIGH','CRITICAL']},
        'recommended_action': {'type': 'STRING'},
        'control_allowed': {'type': 'BOOLEAN'},
        'need_human_review': {'type': 'BOOLEAN'},
        'blocked_reason': {'type': 'STRING'},
        'evidence_used': {'type': 'ARRAY', 'items': {'type': 'STRING'}},
    },
    'required': ['situation_summary','risk_level','recommended_action',
                 'control_allowed','need_human_review','blocked_reason','evidence_used'],
    'propertyOrdering': ['situation_summary','risk_level','recommended_action',
                         'control_allowed','need_human_review','blocked_reason','evidence_used'],
}

def call_gemini(context, model=None, image=None):
    api_key = os.getenv('GEMINI_API_KEY') or os.getenv('GOOGLE_API_KEY')
    if not api_key:
        raise RuntimeError('GEMINI_API_KEY is not set')
    model = model or os.getenv('GEMINI_MODEL', 'gemini-2.5-flash')
    base = os.getenv('GEMINI_BASE_URL', 'https://generativelanguage.googleapis.com/v1beta')
    parts = [{'text': build_prompt(context)}]
    if image is not None:   # vision thật: đính kèm ảnh
        parts.append({'inline_data': {'mime_type': image['mime_type'], 'data': image['data']}})
    payload = {
        'systemInstruction': {'parts': [{'text': load_system_prompt()}]},
        'contents': [{'role': 'user', 'parts': parts}],
        'generationConfig': {
            'temperature': float(os.getenv('GEMINI_TEMPERATURE', '0.2')),
            'responseMimeType': 'application/json',
            'responseSchema': GEMINI_DECISION_SCHEMA,
            'thinkingConfig': {'thinkingBudget': int(os.getenv('GEMINI_THINKING_BUDGET', '0'))},
        },
    }
    r = requests.post(f'{base}/models/{model}:generateContent',
                      headers={'x-goog-api-key': api_key, 'Content-Type': 'application/json'},
                      json=payload, timeout=int(os.getenv('GEMINI_TIMEOUT_SEC', '60')))
    r.raise_for_status()
    data = r.json()
    text = data['candidates'][0]['content']['parts'][0]['text']
    um = data.get('usageMetadata', {}) or {}
    usage = {'prompt_tokens': um.get('promptTokenCount', 0),
             'output_tokens': um.get('candidatesTokenCount', 0),
             'total_tokens': um.get('totalTokenCount', 0)}
    return json.loads(text), usage
```
Nối vào `reason_with_llm` (giữ nguyên try/except để fallback an toàn):
```python
elif mode == 'api':
    raw, usage = call_gemini(context, image=image)
    provider = f"api-gemini:{os.getenv('GEMINI_MODEL', 'gemini-2.5-flash')}"
```

### C6. Cách test
- **Dashboard:** chọn `LLM mode = api - Gemini (Google)` → "So sánh 3 tầng". Cột 3 là reasoning thật; `provider` = `api-gemini:gemini-2.5-flash`.
- **Trình duyệt/curl:** `GET /compare-three-levels/fire_alarm_conflict?mode=api`
- **curl trực tiếp Gemini (kiểm tra key):**
```bash
curl -s "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent" \
  -H "x-goog-api-key: $GEMINI_API_KEY" -H "Content-Type: application/json" \
  -d '{"contents":[{"role":"user","parts":[{"text":"ping"}]}]}'
```

### C7. Lỗi thường gặp
| Triệu chứng | Nguyên nhân & cách xử lý |
|---|---|
| `provider=api-failed-fallback-mock`, lỗi `GEMINI_API_KEY is not set` | Chưa tạo `.env` / thiếu biến / chưa cài `python-dotenv`. |
| 403 `PERMISSION_DENIED` "unregistered callers" | Key sai (chép nhầm 1 ký tự `I`/`l`/`1`), key đã xóa, hoặc chưa bật Generative Language API. Copy lại key bằng nút "Copy key". |
| 401 / `API_KEY_INVALID` | Key không hợp lệ → tạo key mới ở AI Studio. |
| 429 | Hết quota → đợi hoặc giảm số lần gọi. |
| Latency cao (~10s) | Gemini 2.5 bật "thinking". Đặt `GEMINI_THINKING_BUDGET=0` để nhanh (~3s). |

### C8. Cách thêm provider khác (OpenAI/Claude/…)
Mẫu chung — chỉ 3 chỗ:
1. Viết hàm `call_<provider>(context, ...)` trả về `dict` đúng 7 trường (hoặc `(dict, usage)`).
2. Thêm 1 nhánh trong `reason_with_llm`: `elif mode == '<provider>': raw = call_<provider>(context)`.
3. Thêm biến cấu hình vào `.env` + tùy chọn vào dropdown `index.html`.
Giữ nguyên `try/except → mock` để không bao giờ làm lab chết.

---

## D. Chạy với LLM tải model về máy (local Ollama + quantization)

### D1. Cài Ollama
Tải tại https://ollama.com → cài → kiểm tra: `ollama --version`.

### D2. Tải model (theo cấu hình máy)
| Mức máy | Model | Lệnh |
|---|---|---|
| Máy yếu | `qwen3:0.6b`, `gemma3:1b` | `ollama pull qwen3:0.6b` |
| Phổ thông (mặc định) | `qwen3:1.7b` | `ollama pull qwen3:1.7b` |
| Khá/gaming | `qwen3:4b`, `gemma3:4b` | `ollama pull qwen3:4b` |
| Thử quantization QAT | `gemma3:1b-it-qat`, `gemma3:4b-it-qat` | `ollama pull gemma3:4b-it-qat` |

### D3. Cấu hình `.env` cho local
```ini
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=qwen3:1.7b
LLM_TEMPERATURE=0.2
LLM_NUM_CTX=4096
LLM_TIMEOUT_SEC=60
```

### D4. Chạy
Mở Ollama (chạy nền), rồi trên dashboard chọn `LLM mode = local - Ollama` → "So sánh 3 tầng". Hoặc `GET /reason/{id}?mode=local`. Nếu Ollama tắt → tự fallback mock (`provider=local-failed-fallback-mock`).

### D5. Quantization & GGUF
- **Lượng tử hóa** = nén trọng số (FP16 → 4/5/8-bit) để model chạy nhẹ trên laptop, đổi lại chính xác giảm chút ít.
- **Chọn mức:** `Q4_K_M` (nhẹ nhất), `Q5_K_M` (cân bằng), `Q8_0` (máy mạnh). `QAT` = quantization-aware training, giữ chất lượng tốt hơn ở bit thấp.
- **Tìm GGUF** trên Hugging Face: từ khóa `Qwen3 1.7B GGUF Q4_K_M`, `Gemma 3 1B GGUF Q5_K_M`, `Llama 3.2 1B GGUF Q4_K_M`. Ưu tiên model card rõ ràng, license rõ, nhiều lượt tải. Đặt file vào `models/pretrained/` nếu tự import.

### D6. `call_ollama` hoạt động thế nào
POST `http://localhost:11434/api/chat` với `format:'json'` (ép JSON), `options.temperature`/`num_ctx`, rồi `json.loads` nội dung trả về — sau đó cùng đi qua validate + safety gate như Gemini.

---

## E. Tính năng mở rộng — Nhóm A (chiều sâu AI/LLM)

### E1. Vision thật (A1)
- **Dùng:** trên dashboard chọn `mode=api`, chọn file ảnh ở ô **Vision**, bấm **"Vision reason (ảnh)"**.
- **API:** `POST /vision-reason/{scenario_id}?mode=api` (multipart, field `image`).
- **Cơ chế:** endpoint đọc bytes ảnh → base64 → `call_gemini(..., image=...)` đính kèm `inline_data`. Gemini "nhìn" ảnh và đưa mô tả vào `evidence_used`. Với `mock/local` chỉ ghi observation, không gửi ảnh thật.

### E2. Streaming (A2)
- **Dùng:** bấm **"Giải thích trực tiếp (stream)"** → chữ hiện dần.
- **API:** `GET /reason-stream/{scenario_id}?mode=api` (SSE). Dùng `streamGenerateContent?alt=sse` của Gemini, trả văn xuôi (không JSON) để dễ đọc khi đang sinh.

### E3. So sánh model song song (A3)
- **Dùng:** bấm **"So sánh model"** → bảng mock/local/api cạnh nhau.
- **API:** `GET /compare-models/{scenario_id}?modes=mock,local,api`. Chạy các mode bằng **threads song song**, so provider/latency/token/risk/summary.

---

## F. Tính năng mở rộng — Nhóm C (đánh giá & giảng dạy)

### F1. Theo dõi token (C8)
`call_gemini` đọc `usageMetadata` (prompt/output/total tokens), trả trong response và ghi thêm cột vào `outputs/latency_report.csv`. Dùng để ước tính chi phí.

### F2. Ground-truth (C9)
`GROUND_TRUTH` trong `app.py`: nhãn risk "đúng" cho từng bước timeline (23 bước/5 kịch bản), ví dụ:
```python
GROUND_TRUTH = {
  'lab_overcrowded_high_co2': ['LOW','MEDIUM','HIGH','HIGH','CRITICAL'],
  'fire_alarm_conflict':      ['LOW','LOW','MEDIUM','MEDIUM','CRITICAL'],
  ...
}
```

### F3. Harness đánh giá (C7)
```bash
python eval_harness.py                  # LLM tier = mock (offline, miễn phí)
python eval_harness.py --modes mock,api # chấm cả Gemini thật (tốn quota)
```
In bảng **accuracy / mean risk gap / latency** cho từng tầng + số lần LLM đổi quyết định, và xuất `outputs/eval_report.csv`. Ví dụ (mock):
```
sensor_only        78%   gap 0.22
sensor+ai          83%   gap 0.22     ← AI cải thiện
sensor+ai+llm:mock 74%   gap 0.30
```

---

## G. Endpoint mới (bổ sung mục X)

| Endpoint | Vai trò |
|---|---|
| `POST /vision-reason/{id}?mode=api` | Vision thật: gửi ảnh upload vào Gemini |
| `GET /compare-models/{id}?modes=mock,local,api` | So sánh nhiều model song song |
| `GET /reason-stream/{id}?mode=api` | Stream giải thích (SSE) từ Gemini |

---

## H. Cấu trúc file cập nhật
```
lab8_llm_reasoning_v3_live_aiot/
├─ app.py                 # + call_gemini / call_gemini_stream / GROUND_TRUTH / endpoint mới / load_dotenv
├─ eval_harness.py        # MỚI — harness đánh giá
├─ .env                   # MỚI — chứa GEMINI_API_KEY (gitignored)
├─ .env.example           # + GEMINI_*
├─ .gitignore             # MỚI — bỏ qua .env, outputs/*, __pycache__
├─ CLAUDE.md              # MỚI — ghi chú kiến trúc cho dev
├─ requirements.txt       # + python-dotenv
├─ index.html             # + nút Vision / Stream / So sánh model
└─ outputs/
   └─ eval_report.csv     # MỚI — kết quả harness
```

---

## I. Checklist viết vào báo cáo
1. Ảnh dashboard so sánh 3 tầng với `mode=api` (Gemini thật).
2. Ảnh kết quả **Vision reason** (gửi 1 ảnh) — nêu Gemini mô tả gì.
3. Ảnh/loga **So sánh model** (mock vs local vs api): latency & token khác nhau.
4. Bảng kết quả `python eval_harness.py` (mock và/hoặc api) + nhận xét tầng nào chính xác hơn.
5. Giải thích: vì sao dùng structured output (JSON schema) + safety gate + fallback.
6. So sánh **local LLM (Ollama/quantized)** vs **cloud API (Gemini)**: tốc độ, chi phí, riêng tư, chất lượng.
