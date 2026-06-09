# 03. Cấu Trúc Thư Mục Dự Án (Folder Structure)

Một dự án AIoT chuẩn doanh nghiệp cần có cấu trúc thư mục rõ ràng, phân định rạch ròi giữa mã nguồn ứng dụng (app), dữ liệu tĩnh (assets/sample_images), các kịch bản chạy thử (scripts), tệp tin kiểm thử (tests) và tệp tin đóng gói (Docker configurations).

---

## 1. Sơ Đồ Cây Thư Mục Chi Tiết

Dưới đây là sơ đồ chi tiết của dự án Week 5 sau khi đã được tối ưu hóa cấu trúc (tách biệt Frontend):

```text
lab5_dockerized_multimodel_aiot_inference_service_v4/
├── Dockerfile                        # Công thức build Docker Image
├── docker-compose.yml                # Cấu hình khởi chạy docker-compose
├── requirements.txt                  # Danh sách thư viện Python cần thiết
├── .dockerignore                     # Danh sách file bỏ qua khi đóng gói image
├── .gitignore                        # Danh sách file bỏ qua khi dùng Git
├── README.md                         # Hướng dẫn tổng quan dự án
├── RUN_GUIDE.md                      # Hướng dẫn chi tiết các bước chạy và quan sát
├── RUN_TEST_LOG.txt                  # Nhật ký lưu trữ lịch sử test
│
├── app/                              # Mã nguồn chính của FastAPI
│   ├── __init__.py                   # Đánh dấu thư mục là một Python package
│   ├── main.py                       # Tệp chạy chính khởi tạo FastAPI và các route
│   ├── schemas.py                    # Định nghĩa cấu trúc dữ liệu đầu vào (Pydantic models)
│   ├── sensor_inference.py           # Thuật toán phân tích cảm biến (z-score, Moving Avg)
│   ├── vision_inference.py           # Trực quan hóa và suy luận mô hình ảnh ONNX
│   ├── logging_utils.py              # Các hàm phụ trợ ghi log ra file CSV
│   └── templates/                    # Thư mục chứa giao diện tĩnh (Frontend)
│       └── classify-image-demo.html  # Trang HTML/CSS/JS cao cấp (được tách ra từ main.py)
│
├── models/                           # Thư mục chứa các tệp trọng số AI
│   └── vision/                       # Nơi lưu trữ mô hình ảnh
│       ├── squeezenet1.1-7.onnx      # File mô hình ONNX SqueezeNet (4.73 MB)
│       └── imagenet_classes.txt      # File ánh xạ nhãn lớp (1000 classes của ImageNet)
│
├── sample_images/                    # Ảnh mẫu để kiểm thử tính năng upload phân loại
│   └── classroom_object.jpg          # Ảnh mẫu chụp lớp học
│
├── sample_requests/                  # Payload JSON mẫu để test API cảm biến
│   ├── detect_anomaly_request.json   # Payload mẫu test phát hiện dị thường
│   └── forecast_request.json         # Payload mẫu test dự báo chỉ số
│
├── outputs/                          # Thư mục lưu nhật ký hoạt động (Ghi log)
│   ├── .gitkeep                      # Đảm bảo Git theo dõi thư mục rỗng này
│   ├── service_log.csv               # Log ghi nhận lịch sử gọi API cảm biến
│   └── vision_inference_log.csv      # Log ghi nhận lịch sử upload phân loại ảnh
│
├── scripts/                          # Kịch bản tự động hỗ trợ vận hành
│   ├── download_vision_model.py      # Tải tự động file model ONNX từ Internet
│   └── smoke_test_local.py           # Chạy test nhanh các luồng API local
│
└── tests/                            # Thư mục kiểm thử tự động
    └── test_api_local.py             # Các unit test viết bằng pytest
```

---

## 2. Ý Nghĩa Của Việc Phân Chia Cấu Trúc Mã Nguồn

### A. Tách biệt Frontend và Backend (`app/templates/`)
* **Trước đây**: File HTML giao diện được viết dưới dạng một chuỗi văn bản (String) khổng lồ nằm trực tiếp trong file mã nguồn Python `app/main.py`. Điều này làm code Python cực kỳ dài, khó đọc, không thể sử dụng tính năng tự động gợi ý code (IntelliSense) của các IDE khi chỉnh sửa HTML/CSS/JS.
* **Giải pháp tối ưu**: Tách toàn bộ mã giao diện ra tệp [classify-image-demo.html](file:///e:/AIoT/Home-Work/week-5/lab5_dockerized_multimodel_aiot_inference_service_v4/app/templates/classify-image-demo.html). File `main.py` chỉ làm nhiệm vụ đọc tệp tin này từ đĩa và trả về qua giao thức HTTP. Giao diện được thiết kế theo chuẩn `taste-skill` giúp tăng tính thẩm mỹ vượt trội.

### B. Module Hóa Công Việc (Modularization)
* **`app/schemas.py`**: Định nghĩa khuôn mẫu dữ liệu (Data contract). Nếu Client gửi sai định dạng (ví dụ thiếu trường dữ liệu hoặc sai kiểu dữ liệu), FastAPI sẽ tự động chặn và trả lỗi về ngay tại cổng kiểm soát đầu tiên, giúp bảo vệ các hàm tính toán xử lý ở phía sau.
* **`app/sensor_inference.py`** & **`app/vision_inference.py`**: Tách biệt hoàn toàn phần xử lý toán học/mô hình AI ra khỏi phần điều phối mạng. Nhờ vậy, khi bạn muốn thay thế mô hình phân loại ảnh mới mạnh hơn, bạn chỉ việc sửa logic trong file `vision_inference.py` mà không cần đụng vào file định cấu hình API `main.py`.
