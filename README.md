# 🚀 AIoT (Artificial Intelligence of Things) - Course Portfolio

Chào mừng bạn đến với kho lưu trữ bài tập và dự án thực hành môn học **AIoT (Trí tuệ nhân tạo kết hợp Vạn vật kết nối)**. Đây là nơi tổng hợp toàn bộ quá trình nghiên cứu, phát triển và đóng gói các mô hình AI phục vụ cho các ứng dụng IoT thực tế từ cơ bản đến nâng cao của **Phúc Băng**.

---

## 📌 Tổng Quan Lộ Trình Học Tập & Thực Hành

Dưới đây là tóm tắt các dự án và bài tập đã hoàn thành qua từng tuần học:

| Tuần | Chủ Đề Chính | Mô Tả Dự Án / Bài Tập | Công Nghệ & Thuật Toán |
|:---:|---|---|---|
| **[week-1](file:///e:/AIoT/Home-Work/week-1)** | **Smart Classroom AIoT** | Thiết lập và mô phỏng hệ thống phòng học thông minh kết nối IoT cơ bản. | IoT Simulation, Data Logging |
| **[week-2](file:///e:/AIoT/Home-Work/week-2)** | **Data Exploration & Baseline ML** | Khảo sát các tập dữ liệu IoT công cộng, trực quan hóa dữ liệu trên Jupyter Notebook và xây dựng baseline model. | Python, Jupyter Notebook, Pandas |
| **[week-3](file:///e:/AIoT/Home-Work/week-3)** | **Anomaly Detection & Event Intelligence** | Xây dựng hệ thống phát hiện dị thường trong chuỗi dữ liệu telemetry cảm biến (nhiệt độ, độ ẩm) và đưa ra cảnh báo tự động. | Z-Score Anomaly Rule, Rule-based Engine |
| **[week-4](file:///e:/AIoT/Home-Work/week-4)** | **Forecasting & Predictive Analytics** | Dự báo mức tiêu thụ năng lượng của thiết bị (Appliances Energy) và nồng độ khí CO2. | Random Forest, Gradient Boosting, LSTM |
| **[week-5](file:///e:/AIoT/Home-Work/week-5)** | **Dockerized Multi-Model Inference Service** | Đóng gói một API dịch vụ AIoT đa mô hình (xử lý song song dữ liệu số cảm biến và upload hình ảnh) sử dụng Docker. | FastAPI, ONNX Runtime, SqueezeNet, Docker Compose |

---

## 🛠️ Công Nghệ & Thư Viện Sử Dụng

Dự án áp dụng nhiều công nghệ hiện đại trong cả hai lĩnh vực **AI/ML** và **IoT/DevOps**:

* **Backend & API**: `FastAPI` (hiệu năng cao, tự động sinh Swagger docs), `Uvicorn`
* **Deep Learning & Inference**: `ONNX Runtime` (chạy suy luận mô hình siêu nhẹ), `PyTorch` (huấn luyện LSTM), `scikit-learn`, `joblib`
* **Xử lý ảnh**: `Pillow` (PIL), `NumPy`
* **DevOps & Containerization**: `Docker`, `Docker Compose`
* **Phân tích dữ liệu**: `Jupyter Notebook`, `Matplotlib`, `Seaborn`

---

## 📁 Cấu Trúc Kho Lưu Trữ

```text
Home-Work/
├── .gitignore                   # Cấu hình bỏ qua các file rác (.venv, cache, logs) chung
├── README.md                    # Tài liệu hướng dẫn chung (File này)
├── week-1/                      # Dự án Smart Classroom cơ bản
├── week-2/                      # Khảo sát dữ liệu IoT & baseline model
├── week-3/                      # Phát hiện dị thường dữ liệu cảm biến
│   ├── docs/                    # Tài liệu hướng dẫn & đề bài tuần 3
│   └── lab3_aiot_anomaly_event_intelligence_v2/   # Mã nguồn dự án Anomaly Detection
├── week-4/                      # Dự báo chuỗi thời gian (Forecasting)
│   ├── docs/                    # Đề bài & tài liệu tuần 4
│   ├── lab4_aiot_model_training_v4/               # Mã nguồn huấn luyện model ML & LSTM
│   └── lab4_aiot_forecasting_predictive_analytics_uci_appliances/
└── week-5/                      # Đóng gói Docker & API đa mô hình
    ├── docs/                    # Tài liệu tuần 5
    └── lab5_dockerized_multimodel_aiot_inference_service_v4/ # Dịch vụ API Docker hoàn chỉnh
```

---

## 🚀 Hướng Dẫn Chạy Thử Dự Án (Ví dụ với Tuần 5)

Để chạy thử nghiệm dịch vụ API phân tích cảm biến và phân loại ảnh trong tuần 5, bạn có thể thực hiện theo 2 cách:

### Cách 1: Chạy trực tiếp trên máy Local (Python)
1. **Kích hoạt môi trường ảo & cài đặt thư viện**:
   ```bash
   cd week-5/lab5_dockerized_multimodel_aiot_inference_service_v4
   python -m venv .venv
   # Windows:
   .venv\Scripts\activate
   # Linux/macOS:
   source .venv/bin/activate
   pip install -r requirements.txt
   pip install httpx pytest
   ```
2. **Tải trọng số mô hình ảnh**:
   ```bash
   python scripts/download_vision_model.py
   ```
3. **Chạy server**:
   ```bash
   uvicorn app.main:app --reload --port 8001
   ```
   *Truy cập Swagger docs tại: `http://127.0.0.1:8001/docs`*

### Cách 2: Chạy thông qua Docker Compose
Bạn chỉ cần cài đặt Docker/Docker Desktop và chạy lệnh duy nhất:
```bash
cd week-5/lab5_dockerized_multimodel_aiot_inference_service_v4
docker compose up --build -d
```
*Hệ thống sẽ được khởi chạy trên cổng **`8001`** (để tránh xung đột cổng `8000` của các dự án khác trên máy).*
* **API Health Check**: `http://127.0.0.1:8001/health`
* **Giao diện phân loại ảnh**: `http://127.0.0.1:8001/classify-image-demo`

---

## 📝 Nhật Ký Phát Triển & Bản Quyền

* Dự án được thiết kế và thực hiện hoàn toàn bởi **Phúc Băng**.
* Vui lòng tôn trọng bản quyền học thuật và cấu trúc thư mục học tập.
