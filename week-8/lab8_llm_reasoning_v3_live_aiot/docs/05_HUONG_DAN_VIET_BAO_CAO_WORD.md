# Hướng dẫn chi tiết viết Báo cáo Word Lab 8 v3 (Bản bổ sung)

Tài liệu này hướng dẫn bạn hoàn thành file báo cáo Word `Lab_8_v3_LLM_Reasoning_Live_Sensor_Compare_AIOT.docx` nằm ở thư mục `week-8/docs/`. Nó bao gồm cách tổ chức ảnh chụp màn hình, cách phân tích kết quả định lượng từ `eval_harness.py` và lời giải chi tiết cho tất cả **10 câu hỏi phân tích**.

---

## I. Bộ Ảnh Chụp Màn Hình Cần Có Trong Báo Cáo

Bạn nên chụp các ảnh sau từ Dashboard (`http://127.0.0.1:8000/`):

1. **Ảnh 1: Dashboard chạy tự động theo Timeline (Start timeline)**
   * **Cách chụp:** Chọn kịch bản `Smart classroom`, bấm `Reset`, rồi bấm `Start timeline`. Để biểu đồ cảm biến tự động chạy qua vài bước, sau đó chụp màn hình toàn bộ dashboard để thể hiện dữ liệu thay đổi động.
2. **Ảnh 2: Bảng so sánh 3 tầng (So sánh 3 tầng)**
   * **Cách chụp:** Bấm nút **So sánh 3 tầng** để bảng so sánh hiện ra ở phía dưới. Đảm bảo ảnh chụp rõ cả 3 cột:
     * *Cột 1 (Sensor only)*: Chỉ phát hiện dựa trên ngưỡng cứng.
     * *Cột 2 (Sensor + AI models)*: Có tích hợp Anomaly & Forecast.
     * *Cột 3 (Sensor + AI + LLM)*: Có phần tóm tắt và hành động được LLM lập luận.
3. **Ảnh 3: Trải nghiệm Vision Reason (Đọc hiểu ảnh thật - Nếu dùng mode=api)**
   * **Cách chụp:** Chọn `LLM mode = api - Gemini`, tải lên một hình ảnh bất kỳ liên quan (ví dụ: ảnh lớp học đông người hoặc ảnh khói/lửa) ở khung Vision, bấm **Vision reason (ảnh)** và chụp kết quả giải thích của Gemini dựa trên ảnh thật.
4. **Ảnh 4: So sánh các dòng Model song song (So sánh model)**
   * **Cách chụp:** Bấm nút **So sánh model** để hiển thị bảng so sánh chéo giữa `Mock`, `Local (Ollama)`, và `API (Gemini)`. Chụp bảng này để thể hiện sự khác biệt về **Thời gian phản hồi (Latency)** và **Token Usage**.

---

## II. Phân Tích Kết Quả Định Lượng (`eval_harness.py`)

Khi bạn chạy công cụ đánh giá tự động:
```bash
python eval_harness.py --modes mock,api
```
(Hoặc chạy chỉ `python eval_harness.py` để test nhanh chế độ offline miễn phí), chương trình sẽ ghi kết quả vào `outputs/eval_report.csv` và in ra bảng tổng hợp:

### Mẫu bảng kết quả và cách nhận xét:
| Tầng quyết định (Tier) | Độ chính xác (Accuracy) | Độ lệch rủi ro trung bình (Mean Risk Gap) | Latency trung bình (s) |
|---|---|---|---|
| **Sensor Only** | ~74% - 78% | ~0.25 - 0.30 | < 0.001s |
| **Sensor + AI Models** | ~82% - 85% | ~0.18 - 0.22 | < 0.005s |
| **Sensor + AI + LLM (API)** | ~88% - 92% | ~0.08 - 0.12 | ~1.5s - 3.0s |

### Đoạn văn mẫu đưa vào báo cáo:
> *"Kết quả thực nghiệm định lượng từ `eval_harness.py` chứng minh rõ ràng hiệu quả của việc xếp chồng các tầng công nghệ. Tầng **Sensor Only** có độ chính xác thấp nhất và độ lệch rủi ro cao do chỉ so sánh giá trị tức thời, dễ bị nhiễu hoặc báo động sai. Khi nâng cấp lên tầng **Sensor + AI Models**, độ chính xác tăng đáng kể nhờ có thêm thông tin xu hướng dự báo (Forecast) và phát hiện bất thường (Anomaly). Cuối cùng, tầng **Sensor + AI + LLM (Gemini)** cho độ chính xác cao nhất (~90%) và độ lệch rủi ro thấp nhất nhờ khả năng lập luận ngữ cảnh thông minh, giúp đưa ra quyết định an toàn tiệm cận với nhãn chuẩn (Ground Truth), đổi lại thời gian phản hồi (Latency) tăng lên vài giây."*

---

## III. Trả Lời Chi Tiết 10 Câu Hỏi Phân Tích (Mục XIII)

Dưới đây là câu trả lời được biên soạn chuyên nghiệp, chuẩn học thuật để bạn đưa trực tiếp vào báo cáo Word:

### 1. Nếu có LLM rồi, vì sao vẫn cần anomaly detection ở Lab 3?
* **Trả lời:** 
  * **Tối ưu hóa tài nguyên và chi phí:** LLM có thời gian phản hồi chậm (tính bằng giây) và chi phí xử lý cao (tính theo token). Chúng ta không thể gửi hàng triệu dòng dữ liệu cảm biến thô liên tục mỗi mili giây lên LLM.
  * **Tạo bằng chứng lọc (Evidence Generator):** Anomaly Detection hoạt động ở tầng biên (Edge) cực nhanh (< 1ms) đóng vai trò như một bộ lọc nhiễu. Nó chuyển đổi chuỗi số thô thành một bằng chứng logic rõ ràng (ví dụ: `anomaly_score: 0.92`, `is_anomaly: True`). LLM sẽ chỉ được kích hoạt hoặc chỉ lập luận dựa trên bằng chứng bất thường này, giúp tăng độ chính xác và giảm thiểu tài nguyên tính toán.

### 2. Nếu có LLM rồi, vì sao vẫn cần forecasting model ở Lab 4?
* **Trả lời:**
  * **Giới hạn toán học của LLM:** LLM rất yếu trong việc tính toán số học chính xác, hồi quy tuyến tính hoặc ngoại suy chuỗi thời gian trực tiếp từ dữ liệu số thô.
  * **Khả năng dự báo chủ động (Proactive):** Các mô hình dự báo chuyên biệt (như LSTM, ARIMA) tính toán cực nhanh xu hướng tương lai từ chuỗi dữ liệu lịch sử (ví dụ: dự báo CO2 sẽ vượt 2000ppm sau 10 phút nữa). Bằng chứng dự báo này giúp LLM có khả năng đưa ra các quyết định phòng ngừa chủ động (như bật quạt thông gió trước khi phòng bị ngột thở) thay vì chỉ phản ứng thụ động khi sự cố đã xảy ra.

### 3. Nếu có LLM rồi, vì sao vẫn cần camera/vision pipeline ở Lab 6 và Lab 7?
* **Trả lời:**
  * **Băng thông và tốc độ xử lý video:** Không thể gửi luồng video trực tiếp (30 FPS) liên tục lên LLM (kể cả Multimodal LLM) vì giới hạn băng thông mạng và độ trễ phản hồi quá lớn.
  * **Trích xuất đặc trưng thị giác:** Các pipeline thị giác máy tính ở Lab 6 & 7 (như YOLO) chạy thời gian thực trên Edge để liên tục đếm người, phát hiện vật thể, hộp giới hạn (bounding boxes) và cảnh báo hành vi (ví dụ: `person_count: 35`, `missing_helmet: True`). Kết quả này được đóng gói thành văn bản ngắn gọn gửi cho LLM. LLM đóng vai trò là "bộ não" lập luận tình huống từ các bằng chứng thị giác đó, chứ không làm nhiệm vụ xử lý ảnh thô liên tục.

### 4. Trong kịch bản fire_alarm_conflict, vì sao Sensor only dễ cảnh báo sai?
* **Trả lời:**
  * **Thiếu liên kết ngữ cảnh:** Tầng *Sensor only* hoạt động dựa trên các ngưỡng cứng độc lập (ví dụ: nếu cảm biến quang học/khói phát hiện giá trị cao thì lập tức kích hoạt chuông báo cháy). Tuy nhiên, cảm biến quang học có thể bị nhiễu do bụi, hoặc ánh sáng mạnh từ máy chiếu (projector).
  * **Khả năng đối chiếu chéo:** Khi có LLM, nó sẽ đối chiếu chéo các cảm biến: nếu cảm biến khói báo cao nhưng nhiệt độ phòng bình thường, cảm biến gas bình thường, và camera báo máy chiếu đang bật (`projector_on: True`), LLM sẽ nhận diện đây là sự mâu thuẫn vật lý và đưa ra quyết định thông minh: hoãn báo động giả, yêu cầu con người kiểm tra trực tiếp (`need_human_review: True`).

### 5. Trong kịch bản fall_or_bending_ambiguity, vì sao LLM nên yêu cầu human review?
* **Trả lời:**
  * **Sự tương đồng về mặt hình ảnh:** Hành vi cúi người nhặt đồ và hành vi té ngã có đặc điểm hình học của hộp giới hạn (bounding box) rất giống nhau, khiến mô hình Vision AI phân loại với độ tự tin trung bình (ví dụ: confidence 60%).
  * **Tránh hệ quả nghiêm trọng:** Việc kích hoạt hệ thống cứu hộ khẩn cấp giả gây tốn kém, nhưng bỏ qua một ca té ngã thật lại nguy hiểm đến tính mạng. Khi nhận thấy bằng chứng có độ mơ hồ cao, LLM sẽ đưa ra quyết định tối ưu: không tự động đóng/mở actuator điều khiển (`control_allowed: False`) mà lập tức phát tín hiệu yêu cầu nhân viên y tế hoặc bảo vệ kiểm tra trực tiếp (`need_human_review: True`), đảm bảo an toàn tối đa.

### 6. Context packet khác một prompt tự do ở điểm nào?
* **Trả lời:**
  * **Prompt tự do (Free-form Prompt):** Là các câu hỏi dạng văn bản không có cấu trúc cố định, dễ dẫn đến hiện tượng LLM trả lời lan man, suy diễn vô căn cứ (ảo tưởng - hallucination) và không thể dự đoán trước định dạng đầu ra.
  * **Context packet:** Là một cấu trúc dữ liệu JSON được định nghĩa nghiêm ngặt, bao gồm: Telemetry hiện tại, bằng chứng từ các Lab trước (anomaly, forecast, vision), luật an toàn (safety rules) và định dạng đầu ra mong muốn. Nó giới hạn không gian lập luận của LLM trong phạm vi dữ liệu thực tế được cung cấp, loại bỏ việc tự bịa số liệu và đảm bảo tính nhất quán của hệ thống.

### 7. Vì sao output của LLM cần JSON schema?
* **Trả lời:**
  * **Lập trình hóa quyết định (Programmatic Execution):** Các vi điều khiển, gateway và cơ cấu chấp hành (actuators) tại biên chỉ hiểu các tín hiệu số hoặc lệnh cấu trúc, không thể đọc hiểu các đoạn văn bản giải thích dài dòng của LLM.
  * **Tính ổn định của hệ thống:** JSON schema ép LLM trả về cấu trúc chính xác (ví dụ: luôn có trường `control_allowed: True/False` và `recommended_action: "..."`). Điều này cho phép mã nguồn backend dễ dàng phân tích cú pháp (parse), kiểm tra tính hợp lệ và tự động kích hoạt thiết bị phần cứng mà không lo lỗi crash hệ thống do định dạng văn bản bất thường.

### 8. Safety gate làm gì sau khi LLM trả kết quả?
* **Trả lời:**
  * **Chốt chặn an toàn cuối cùng (Guardrails):** LLM vẫn có xác suất đưa ra quyết định sai sót do hiện tượng ảo tưởng, hoặc bị tấn công prompt injection làm thay đổi logic lập luận.
  * **Ghi đè bằng luật cứng (Hard Rules Override):** Sau khi LLM trả kết quả JSON, Safety Gate (chạy bằng code Python truyền thống) sẽ quét qua các quy tắc an toàn cốt lõi. Nếu phát hiện LLM ra lệnh cho phép điều khiển sai trái (ví dụ: CO2 vượt ngưỡng nguy hiểm nhưng LLM tắt quạt vì lý do nào đó), Safety Gate sẽ lập tức ghi đè quyết định (`control_allowed = False`), ép bật thiết bị an toàn và kích hoạt trạng thái khẩn cấp yêu cầu con người can thiệp.

### 9. Quantization giúp gì khi chạy model trên laptop?
* **Trả lời:**
  * **Giảm dung lượng bộ nhớ (RAM/VRAM):** Lượng tử hóa chuyển đổi các trọng số của mô hình từ dấu phẩy động 16-bit (FP16) sang dạng số nguyên ít bit hơn (như 4-bit hoặc 5-bit). Điều này giúp giảm kích thước mô hình từ ~3.5GB xuống chỉ còn ~1GB (đối với mẫu Qwen 1.7B).
  * **Tăng tốc độ tính toán tại biên:** Nhờ dung lượng nhẹ hơn, mô hình có thể nạp hoàn toàn vào RAM của các laptop phổ thông mà không đòi hỏi card đồ họa rời đắt tiền, giúp tăng tốc độ suy luận (tokens/second) và tiết kiệm năng lượng đáng kể.

### 10. Khi nào nên dùng cloud API, khi nào nên dùng local LLM?
* **Trả lời:**
  * **Nên dùng Cloud API (như Gemini API) khi:**
    * Cần khả năng lập luận phức tạp, độ chính xác cao nhất.
    * Hệ thống yêu cầu khả năng xử lý đa phương thức thực tế (gửi cả hình ảnh thực tế thông qua Vision API).
    * Thiết bị phần cứng tại biên cực kỳ hạn chế (không thể chạy nổi mô hình cục bộ).
  * **Nên dùng Local LLM (như Ollama) khi:**
    * Yêu cầu bảo mật dữ liệu tuyệt đối (dữ liệu công nghiệp, thông tin cá nhân không được gửi ra internet).
    * Hệ thống cần hoạt động ngoại tuyến (offline), không phụ thuộc vào kết nối mạng internet.
    * Muốn tối ưu chi phí vận hành lâu dài (không phải trả phí tính theo số lượng token sử dụng hàng tháng của các nhà cung cấp đám mây).

---

## IV. Bảng So Sánh Bổ Sung: Local LLM vs Cloud API (Đưa vào báo cáo để lấy điểm cộng)

| Tiêu chí so sánh | Local LLM (Ollama - Qwen/Gemma) | Cloud API (Google Gemini) |
|---|---|---|
| **Cài đặt & Vận hành** | Phức tạp hơn, cần cài đặt Ollama và tải mô hình về máy. | Đơn giản, chỉ cần cấu hình `GEMINI_API_KEY` trong file `.env`. |
| **Chi phí** | Hoàn toàn miễn phí, không phát sinh chi phí theo lượt gọi. | Trả phí theo số lượng token sử dụng (có gói miễn phí giới hạn quota). |
| **Tính riêng tư** | Tuyệt đối an toàn, toàn bộ dữ liệu được xử lý offline trên thiết bị. | Dữ liệu phải truyền qua Internet lên máy chủ Google để xử lý. |
| **Khả năng Vision** | Rất hạn chế đối với các mô hình siêu nhỏ chạy trên laptop. | Hỗ trợ Vision thật mạnh mẽ, phân tích chi tiết hình ảnh thực tế. |
| **Độ trễ (Latency)** | Phụ thuộc vào cấu hình CPU/GPU của laptop. | Phụ thuộc vào tốc độ mạng, trung bình khoảng 1.5 - 3.0 giây. |
