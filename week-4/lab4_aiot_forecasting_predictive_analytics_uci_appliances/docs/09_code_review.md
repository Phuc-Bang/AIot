# BÁO CÁO ĐÁNH GIÁ MÃ NGUỒN CẤP ĐỘ SENIOR (ENGINEERING CODE REVIEW)

Khi xây dựng một hệ thống học máy phục vụ thực tế (Production ML), chất lượng của mã nguồn đóng vai trò sống còn đối với sự ổn định, tính an toàn và khả năng bảo trì của hệ thống. Một mã nguồn chắp vá, thiếu phân tách trách nhiệm rõ ràng sẽ nhanh chóng sụp đổ khi lượng người dùng tăng cao hoặc khi phân phối dữ liệu đầu vào biến động.

Tài liệu này thực hiện đánh giá mã nguồn (Code Review) toàn diện dự án **Lab 4** dưới lăng kính của một Kỹ sư phần mềm & Kiến trúc sư MLOps cấp cao, chỉ rõ các ưu/khuyết điểm, nhận diện các mẫu chống đối (anti-patterns), logic dễ vỡ và vạch ra chiến lược tái cấu trúc (refactoring) chuẩn doanh nghiệp.

---

## 1. Đánh giá 10 Chiều Kỹ thuật Phần mềm (Software Engineering Dimensions)

---

### 1. Tổ chức mã nguồn (Code Organization)
*   **Đánh giá**: Khá rõ ràng đối với quy mô một bài thực hành (POC). Các file mã nguồn được đặt gọn trong thư mục `src/`, dữ liệu trong `data/`, mô hình trong `models/` và kết quả trong `outputs/`.
*   **Điểm yếu**: Chưa phân tách rõ ràng giữa mã nguồn chạy offline (huấn luyện, vẽ biểu đồ) và mã nguồn chạy online (FastAPI). Việc đặt chung toàn bộ trong một thư mục dễ gây nhầm lẫn về môi trường chạy và thư viện phụ thuộc (dependencies).

---

### 2. Tính mô-đun hóa (Modularity)
*   **Đánh giá**: Tốt. File `utils.py` đóng vai trò là lõi chia sẻ (Shared Library) chứa toàn bộ logic tiền xử lý và đặc trưng chuỗi thời gian, giúp cả `train_forecast.py` và `app.py` tái sử dụng, tránh lỗi lệch dữ liệu đầu vào.
*   **Điểm yếu**: File `utils.py` đang gánh vác quá nhiều trách nhiệm (God Object). Nó vừa chứa cấu hình biến toàn cục, logic tiền xử lý, tính toán đặc trưng lượng giác, logic phân cấp rủi ro an toàn và các hàm ghi lưu file JSON.

---

### 3. Cách đặt tên (Naming Conventions)
*   **Đánh giá**: Rất trực quan và tường minh. Các biến mục tiêu (`Appliances`), cột ngày (`date`), chân trời dự báo (`HORIZON_STEPS`), và các đặc trưng động (`appliances_lag_1`, `appliances_rolling_mean_6`) được đặt tên theo chuẩn snake_case và mang rõ ý nghĩa vật lý gốc.
*   **Điểm yếu**: Một số biến toàn cục trong `utils.py` (như `UCI_COLUMNS`, `FEATURE_COLUMNS`) được viết hoa cố định, nhưng thực tế các đặc trưng đầu vào có thể thay đổi động tùy theo phiên bản mô hình được nạp từ file `.joblib`.

---

### 4. Phân tách các Trách nhiệm (Separation of Concerns - SoC)
*   **Đánh giá**: Ở mức trung bình. 
*   **Điểm yếu nghiêm trọng**: Có sự đan xen quá sâu giữa **Logic toán học học máy** và **Logic nghiệp vụ web**. Cụ thể, file `app.py` (vốn chỉ nên chịu trách nhiệm tiếp nhận yêu cầu mạng và validate HTTP) lại trực tiếp thực hiện logic điền khuyết thiếu đặc trưng, ánh xạ rủi ro thống kê và thực hiện ghi đè file log đĩa cứng. Điều này vi phạm nghiêm trọng nguyên lý SoC.

---

### 5. Rủi ro rò rỉ dữ liệu (Data Leakage Risks)
*   **Đánh giá**: Tuyệt vời. Dự án áp dụng chặt chẽ phép cắt dòng thời gian tuyến tính (`time_split` chia 75% đầu làm train, 25% sau làm test) và cấm sử dụng xáo trộn shuffle dữ liệu, triệt tiêu hoàn toàn nguy cơ rò rỉ thông tin tương lai về quá khứ.
*   **Điểm cần lưu ý**: Cần bảo đảm ở môi trường chạy trực tuyến, Client tuyệt đối không gửi nhầm mốc thời gian tương lai lọt vào mảng lịch sử telemetry đầu vào.

---

### 6. Khả năng mở rộng quy mô (Scalability)
*   **Đánh giá**: Kém.
*   **Nguyên nhân**:
    1.  *Ghi log đồng thời*: Việc mở rộng file `forecast_log.csv` cục bộ trực tiếp trên ổ đĩa thông qua Pandas là phép toán đơn luồng (Single-thread blocking IO). Khi có hàng nghìn request gọi API đồng thời, hệ thống sẽ bị thắt nút cổ chai tại ổ đĩa (IO Bottleneck) và crash server do xung đột khóa file.
    2.  *Tính toán đặc trưng lặp*: Server API phải tính toán lại toàn bộ Lag/Rolling bằng Pandas trong RAM cho từng request đơn lẻ, gây tiêu tốn CPU nghiêm trọng.

---

### 7. Khả năng bảo trì (Maintainability)
*   **Đánh giá**: Dễ bảo trì đối với mã nguồn hiện tại nhờ cấu trúc gọn nhẹ và comment code rất chi tiết.
*   **Khuyết điểm**: Thiếu hoàn toàn các bài **Unit Tests** cho các hàm lõi trong `utils.py` (ví dụ không có test kiểm thử xem hàm Sin/Cos có trả về đúng tọa độ lượng giác hay không, điền khuyết thiếu hoạt động đúng không). Khi thay đổi code trong `utils.py`, không có gì bảo đảm hệ thống không bị lỗi hồi quy (regression bugs).

---

### 8. Tính sẵn sàng triển khai (Deployment Readiness)
*   **Đánh giá**: Ở mức cơ bản (POC).
*   **Điểm yếu**:
    *   Thiếu file cấu hình môi trường bảo mật (như `.env` hoặc cấu hình Consul). Các đường dẫn tệp tin và cổng kết nối đang được viết cứng (hard-coded) trực tiếp trong file.
    *   Thiếu file cấu hình Docker (`Dockerfile`) để đóng gói đồng bộ dịch vụ.

---

### 9. Chất lượng Thiết kế API (API Design Quality)
*   **Đánh giá**: Rất tốt. Cấu trúc bản tin phản hồi JSON của endpoint `/forecast` được phân cấp rất mạch lạc: `model_output` chứa kết quả thô, `decision` chứa thông tin hành động nghiệp vụ an toàn và `api_check` phục vụ giám sát độ trễ mạng. Endpoint `/health` hỗ trợ tốt cho Kubernetes health probes.
*   **Điểm yếu**: Payload đầu vào bắt buộc gửi mảng lịch sử 24 điểm đo gây lãng phí băng thông mạng di động. Thiết kế REST HTTP truyền thống có độ trễ lớn hơn so với giao thức gọn nhẹ **gRPC** hoặc **WebSockets** trong truyền dữ liệu IoT.

---

### 10. Chất lượng Kỹ nghệ Đặc trưng (Feature Engineering Quality)
*   **Đánh giá**: Đạt điểm tối đa về mặt khoa học dữ liệu chuỗi thời gian. Sự kết hợp giữa Lag, Rolling (Mean & Std), Delta (đo gia tốc) và Cyclic Time (Sin/Cos) thể hiện tư duy học máy chuỗi thời gian xuất sắc và bắt bài được toàn bộ các quán tính vật lý của phụ tải điện.

---

## 2. Nhận diện các Mẫu chống đối (Anti-Patterns) & Logic dễ gãy

1.  **Anti-Pattern: Concurrent CSV Logging (Ghi file CSV đồng thời)**:
    *   *Mã lỗi*: `forecast_log.to_csv(OUTPUT_DIR / "forecast_log.csv", mode='a', index=False)` trong luồng API trực tuyến.
    *   *Rủi ro*: Đây là mẫu chống đối kinh điển. File CSV không thể chịu tải đồng thời. Hệ thống chắc chắn crash khi chạy đa luồng trên Kubernetes.
2.  **Logic dễ vỡ: Hard-coded training medians**:
    *   *Mã lỗi*: Nạp tĩnh `raw_medians` từ tệp bundle `.joblib` để điền khuyết thiếu vĩnh viễn.
    *   *Rủi ro*: Nếu cảm biến hỏng kéo dài nhiều ngày, việc điền mãi một giá trị trung vị tĩnh của quá khứ sẽ làm mô hình liên tục dự báo ra một hằng số phẳng lì, làm mất hoàn toàn độ nhạy của hệ thống cảnh báo.
3.  **Thiếu xác thực logic vật lý (Missing Semantic Validation)**:
    *   *Rủi ro*: Pydantic chỉ kiểm tra kiểu dữ liệu (`float`, `int`). Nếu Gateway bị nhiễu gửi lên giá trị `T1: -100.0` (Nhiệt độ phòng bếp âm 100 độ C), API vẫn chấp nhận và đưa vào mô hình suy diễn, dẫn đến kết quả dự báo công suất bị bóp méo nghiêm trọng.
4.  **Thiếu hệ thống Giám sát & Cảnh báo (Missing Monitoring)**:
    *   *Rủi ro*: Hệ thống hoàn toàn "mù" trước hiện tượng trôi lệch dữ liệu (Data Drift) và sụt giảm độ chính xác. Không có cơ chế tự động gửi cảnh báo (Slack, Email) khi mô hình dự báo liên tục lệch quá $50\%$ so với thực tế đo đạc.

---

## 3. Chiến lược Tái cấu trúc chuẩn Doanh nghiệp (Refactoring Strategy)

Để chuyển đổi toàn diện dự án lên quy mô lớn, chúng ta áp dụng 3 bước cải tiến kiến trúc:

### Bước 1: Tái cấu trúc Thư mục dự án (Folder Restructuring)

Chúng ta chuyển đổi từ thư mục bài lab phẳng dẹt sang cấu trúc thư mục phân tầng chuẩn doanh nghiệp (Enterprise Layout):

```text
lab4_aiot_forecasting_predictive_analytics_uci_appliances/
├─ config/                                  # Chứa các file cấu hình môi trường (.env, settings.yaml)
├─ data/                                    # Fallback offline data
├─ deploy/                                  # Dockerfile, docker-compose, Kubernetes manifests
├─ docs/                                    # Hệ thống tài liệu kỹ thuật
├─ models/                                  # Joblib model bundle registry
├─ src/                                     # Toàn bộ mã nguồn chia phân cấp rõ ràng
│  ├─ core/                                 # Lõi toán học độc lập
│  │  ├─ __init__.py
│  │  ├─ features.py                        # Tách riêng logic tính Lag, Rolling, Sin/Cos
│  │  └─ preprocessing.py                 # Tách logic làm sạch, điền khuyết raw_medians
│  ├─ training/                             # Pipeline huấn luyện offline
│  │  ├─ __init__.py
│  │  └─ pipeline.py                        # Grid search, cross validation, MLflow tracking
│  ├─ api/                                   # Lớp phục vụ API thời gian thực
│  │  ├─ endpoints/                         # REST controllers (/health, /forecast)
│  │  ├─ schemas/                           # Pydantic models với semantic validation
│  │  ├─ services/                          # Business logic: gọi model serving, mapping rủi ro
│  │  ├─ middleware/                        # Rate limiting, Prometheus metrics collector
│  │  └─ app.py                             # Khởi tạo FastAPI Server chính
│  ├─ edge/                                 # Nhúng ESP32 C++ Code
│  │  └─ safety_gateway/
│  └─ utils/                                # Tiện ích ghi log đĩa, định dạng ngày tháng dùng chung
├─ tests/                                   # Thư mục kiểm thử Unit test & Integration test
│  ├─ unit/                                 # Test các hàm toán học trong core/features.py
│  └─ integration/                          # Test endpoint API giả lập
├─ requirements.txt
└─ requirements-dev.txt                     # Thư viện kiểm thử (pytest, httpx) và MLOps (mlflow)
```

---

### Bước 2: Tách biệt Logic & Nâng cấp Kỹ thuật (Refactoring Steps)

1.  **Tách `utils.py` thành các Module chuyên biệt**:
    *   Tách toàn bộ logic tạo đặc trưng sang `src/core/features.py`. File này hoàn toàn thuần khiết (Pure functions), chỉ nhận vào dữ liệu số và trả về đặc trưng, không chứa đường dẫn tệp hay logic nghiệp vụ API, giúp viết Unit Test bằng **PyTest** cực kỳ dễ dàng.
2.  **Nâng cấp xác thực dữ liệu đầu vào (Semantic Validation)**:
    *   Sử dụng Pydantic `Field(..., ge=10.0, le=45.0)` cho các cột nhiệt độ phòng để từ chối ngay lập tức các giá trị nhiễu ảo từ biên gửi lên.
3.  **Tách logic ghi log ra khỏi luồng API đồng bộ**:
    *   Thay thế việc ghi đè file CSV bằng cơ chế đẩy log sự kiện sang một hàng đợi chạy nền không chặn (Asynchronous background task) sử dụng tính năng `BackgroundTasks` của FastAPI, ghi trực tiếp vào Database thông qua Connection Pool để tối ưu hóa hiệu năng chịu tải.

---

### Bước 3: Đề xuất Cải tiến hướng Sản xuất (Production Improvements)

1.  **Thay thế cơ chế điền khuyết thiếu tĩnh bằng Imputation động**:
    *   Tích hợp giải thuật điền khuyết thiếu chuỗi thời gian thông minh dựa trên giá trị liền kề gần nhất (**Forward Fill**) kết hợp với giá trị trung vị của khung giờ tương ứng trong tuần để đảm bảo dữ liệu điền khuyết phản ánh đúng ngữ cảnh sinh hoạt.
2.  **Tích hợp Rate Limiting & API Security**:
    *   Sử dụng API Key xác thực (ngăn chặn các Gateway lạ gửi dữ liệu rác tấn công server) và cài đặt **Rate Limiting** (giới hạn mỗi IP Gateway chỉ được phép gửi tối đa 1 request mỗi 10 phút) để bảo vệ API trước nguy cơ bị quá tải DDoS.
3.  **Tự động tái huấn luyện khi có cảnh báo Drift**:
    *   Cấu hình một tiến trình nền sử dụng **Evidently AI** để tính toán khoảng cách Wasserstein giữa phân phối dữ liệu đầu vào thực tế của tuần này so với tập huấn luyện lịch sử. Nếu chỉ số trôi lệch vượt quá ngưỡng an toàn, kích hoạt lệnh webhook gọi Airflow tự động chạy pipeline huấn luyện lại mô hình và xuất bản phiên bản model mới lên registry.
