# CLAUDE.md — Lab 8 v3: LLM Reasoning & Context-aware Decision for AIoT

Hướng dẫn cho Claude Code khi làm việc trong thư mục lab này.

## Lab này là gì

Dashboard FastAPI một-process minh hoạ **pipeline 3 tầng ra quyết định** cho AIoT:
**① Sensor only → ② Sensor + AI models → ③ Sensor + AI models + LLM.**
Thông điệp sư phạm: LLM *bổ sung reasoning* trên bằng chứng từ các lab trước (Lab 3/4/6/7),
**không thay thế** chúng. Lab luôn chạy được offline nhờ `mock` LLM fallback.

## Chạy & kiểm thử

```bash
pip install -r requirements.txt
python run_lab8_demo.py                  # smoke test → in "LOCAL_PIPELINE_TEST_PASS"
uvicorn app:app --reload --port 8000     # http://127.0.0.1:8000/
```

- `run_lab8_demo.py` dùng `fastapi.testclient.TestClient` ⇒ **cần `httpx`** (đã có trong requirements).
- Không có test framework (pytest...). `run_lab8_demo.py` LÀ bộ kiểm thử — chạy nó sau mỗi thay đổi.
- App chạy `uvicorn` thì KHÔNG cần `httpx`.
- **Harness đánh giá:** `python eval_harness.py [--modes mock,api]` → accuracy/mean-gap từng tầng vs `GROUND_TRUTH`, số lần LLM đổi quyết định, latency; xuất `outputs/eval_report.csv`.

## Kiến trúc (toàn bộ backend nằm trong `app.py`)

```
LiveState (RAM, có Lock)
   sensors dict  ── 1 trong 5 SCENARIOS
        │
        ├─① sensor_only_decision()          rule cứng theo ngưỡng
        │
        ├─② previous_ai_model_outputs()      giả lập output Lab 3/4/6/7
        │   └─ sensor_ai_decision()          nâng risk theo evidence
        │
        └─③ build_context_packet()           đóng gói context + safety_rules + output_schema
            └─ reason_with_llm(mode)          mock | local(Ollama) | api(Gemini/Google)
                ├─ mock_llm_reason()          fallback luôn chạy được
                ├─ call_ollama()              POST /api/chat, format=json
                ├─ call_gemini()              REST generateContent + responseSchema (GEMINI_DECISION_SCHEMA)
                ├─ validate_llm_output()      kiểm tra schema JSON
                └─ apply_safety_gate()        CHỐT CHẶN cuối → final_decision
```

### Bản đồ hàm trong `app.py`
- `SCENARIOS` (dict): 5 kịch bản, mỗi cái có `editable_sensors`, `timeline`, `safety_rules`.
- `LiveState`: state cảm biến trong RAM, thread-safe bằng `self.lock`; `step()` chạy theo timeline, `update_sensor()` chỉnh tay, ghi `telemetry_timeseries.csv`.
- Tầng 1: `sensor_only_decision()`.
- Tầng 2: `previous_ai_model_outputs()` + `sensor_ai_decision()` + helper `max_risk()`/`risk_order()`.
- Tầng 3: `build_context_packet()`, `build_prompt()`, `load_system_prompt()`, `mock_llm_reason()`, `call_ollama()`, `reason_with_llm()`, `validate_llm_output()`, `apply_safety_gate()`.
- `_runner()` + `start_background()`: thread nền chạy timeline mỗi `interval_sec`.

## 5 kịch bản
`lab_overcrowded_high_co2`, `fire_alarm_conflict`, `fall_or_bending_ambiguity`,
`ppe_danger_zone`, `greenhouse_leaf_disease_risk`.

## Endpoint chính
- Live: `/live/{state,reset,start,stop,step,update-sensor}`, `/stream/events` (SSE, đẩy state mỗi giây).
- Từng tầng: `/baseline/{id}?level=sensor|ai`, `/ai-models/{id}`, `/context/{id}`, `/reason/{id}?mode=`.
- So sánh (UI dùng): `/compare-three-levels/{id}?mode=` và `/live/compare-three-levels`.
- Ảnh (vision thật khi mode=api): `POST /vision-reason/{id}?mode=api` (gửi ảnh upload vào Gemini).
- So sánh model song song: `GET /compare-models/{id}?modes=mock,local,api`.
- Streaming giải thích (SSE): `GET /reason-stream/{id}?mode=api` (Gemini `streamGenerateContent`).

## Quy ước & lưu ý quan trọng
- **An toàn là số một:** `apply_safety_gate()` LUÔN ép `control_allowed=False` (lab mode),
  bật `need_human_review` khi confidence < 0.6 hoặc bằng chứng mâu thuẫn. Đừng nới lỏng điều này.
- **Mọi lỗi LLM phải fallback an toàn** về `mock_llm_reason()` + human review — giữ nguyên pattern try/except trong `reason_with_llm()`.
- **JSON schema bắt buộc:** `OUTPUT_SCHEMA` / `validate_llm_output()` — nếu đổi field, sửa đồng bộ cả mock, validate, safety gate, và `index.html`.
- **Mode LLM chọn theo request** (UI dropdown hoặc `?mode=`), KHÔNG đọc từ env. Env cấu hình provider: `OLLAMA_*`/`LLM_*` cho mode `local`; `GEMINI_*` (`GEMINI_API_KEY`, `GEMINI_MODEL`, `GEMINI_TEMPERATURE`, `GEMINI_TIMEOUT_SEC`, `GEMINI_THINKING_BUDGET`) cho mode `api`. App tự nạp `.env` qua `python-dotenv` (`load_dotenv` ở đầu `app.py`).
- **`GEMINI_THINKING_BUDGET=0`** tắt "thinking" của Gemini 2.5 → latency thấp cho lab; tăng lên để reasoning sâu hơn.
- **Mode `api` = Gemini qua REST** (`generateContent`, header `x-goog-api-key`) với structured output (`responseMimeType=application/json` + `responseSchema=GEMINI_DECISION_SCHEMA`, dùng type CHỮ HOA, không `additionalProperties`) — không hardcode model ID; mặc định `gemini-2.5-flash`. Lỗi key/mạng tự fallback về mock (giữ nguyên try/except trong `reason_with_llm`).
- **System prompt** đọc từ `data/prompt_templates/system_prompt.txt` qua `load_system_prompt()` — chỉnh prompt ở file đó, không hardcode.
- **`outputs/`** là artifact tự sinh (đã gitignore). Xoá thoải mái; chạy lại app/test sẽ tạo lại.
- Frontend `index.html` là SPA một file (HTML+CSS+JS thuần, không build step). Control panel tự sinh từ `editable_sensors`.
- Toàn bộ là một process, state trong RAM ⇒ restart là mất live state. Không có DB.

## Khi thêm kịch bản mới
1. Thêm entry vào `SCENARIOS` (đủ `editable_sensors` / `timeline` / `safety_rules`).
2. Thêm nhánh `scenario_id` tương ứng trong `sensor_only_decision()` và `previous_ai_model_outputs()`.
3. (Tuỳ chọn) thêm nhánh trong `mock_llm_reason()` để có summary/action sát kịch bản.
4. Chạy `python run_lab8_demo.py` để verify.
