# BỘ TÀI LIỆU KỸ THUẬT: FORECASTING & PREDICTIVE ANALYTICS CHO HỆ THỐNG AIoT (SMART HOME ENERGY)

Chào mừng các bạn sinh viên và kỹ sư AIoT đến với bộ tài liệu kỹ thuật chuyên sâu của **Lab 4: Dự báo và Phân tích Dự đoán Điện năng tiêu thụ (UCI Appliances Dataset)**. 

Hệ thống tài liệu này được biên soạn bởi Đội ngũ Kiến trúc sư ML & AIoT cấp cao, nhằm cung cấp cái nhìn toàn diện, sâu sắc và mang tính thực tiễn cao nhất về cách xây dựng, vận hành và sản xuất hóa (productionize) một hệ thống dự báo chuỗi thời gian (time-series forecasting) trong thế giới IoT thực tế.

---

## 🗺️ Bản đồ Chỉ đường Hệ thống Tài liệu (15 Cấu phần Kỹ thuật)

Để tiếp thu kiến thức một cách khoa học và có hệ thống, khuyến lượng người học đi theo lộ trình cấu trúc tuyến tính dưới đây:

### Phần I: Tổng quan & Kiến trúc Hệ thống
1.  **[00_project_overview.md](file:///e:/AIoT/Day-4/lab4_aiot_forecasting_predictive_analytics_uci_appliances_code/lab4_aiot_forecasting_predictive_analytics_uci_appliances/docs/00_project_overview.md)**
    *   *Nội dung*: Giới thiệu mục tiêu học tập, bối cảnh thực tế bài toán phụ tải điện Wh và **bảng đối chuẩn chi tiết** phân biệt bản chất giữa *Lab 3 (Anomaly Detection)* và *Lab 4 (Forecasting)*.
2.  **[01_architecture.md](file:///e:/AIoT/Day-4/lab4_aiot_forecasting_predictive_analytics_uci_appliances_code/lab4_aiot_forecasting_predictive_analytics_uci_appliances/docs/01_architecture.md)**
    *   *Nội dung*: Sơ đồ Mermaid biểu diễn kiến trúc AIoT 8 lớp. Nơi AI hoạt động, ánh xạ BEMS tòa nhà thực tế và thiết kế mở rộng ESP32 nhúng qua MQTT.
3.  **[02_data_flow.md](file:///e:/AIoT/Day-4/lab4_aiot_forecasting_predictive_analytics_uci_appliances_code/lab4_aiot_forecasting_predictive_analytics_uci_appliances/docs/02_data_flow.md)**
    *   *Nội dung*: Sơ đồ luồng biến đổi tuần tự **15 bước của dòng dữ liệu** từ CSV thô đến phản hồi API. Đi kèm bảng dữ liệu trung gian và cẩm nang debug lỗi KeyError/NaN.
4.  **[03_runtime_and_dependencies.md](file:///e:/AIoT/Day-4/lab4_aiot_forecasting_predictive_analytics_uci_appliances_code/lab4_aiot_forecasting_predictive_analytics_uci_appliances/docs/03_runtime_and_dependencies.md)**
    *   *Nội dung*: Đồ thị phụ thuộc file (Dependency Graph), sơ đồ thực thi RAM tuần tự, phân loại an toàn chỉnh sửa file và 4 vị trí đặt debug (breakpoints) thực tế.

### Phần II: Dữ liệu & Kỹ nghệ Đặc trưng chuỗi thời gian
5.  **[04_dataset_and_schema.md](file:///e:/AIoT/Day-4/lab4_aiot_forecasting_predictive_analytics_uci_appliances_code/lab4_aiot_forecasting_predictive_analytics_uci_appliances/docs/04_dataset_and_schema.md)**
    *   *Nội dung*: Phân tích cấu trúc schema 29 cột đo đạc UCI. Đặc biệt đi sâu vào chiến lược xử lý dữ liệu khuyết thiếu thời gian thực qua 2 lớp phòng vệ điền khuyết bằng bộ trung vị thô (`raw_medians`).
6.  **[05_feature_engineering.md](file:///e:/AIoT/Day-4/lab4_aiot_forecasting_predictive_analytics_uci_appliances_code/lab4_aiot_forecasting_predictive_analytics_uci_appliances/docs/05_feature_engineering.md)**
    *   *Nội dung*: Chi tiết toán học và ví dụ bảng nhỏ (mini tables) Lag (quán tính), Rolling (mịn nhiễu), Delta (gia tốc), Sin/Cos thời gian tuần hoàn (Cyclic Time), kỹ thuật dịch nhãn tương lai và phòng chống rò rỉ dữ liệu (Data Leakage).

### Phần III: Mô hình hóa, API & Đánh giá sai số
7.  **[06_model_training_and_metrics.md](file:///e:/AIoT/Day-4/lab4_aiot_forecasting_predictive_analytics_uci_appliances_code/lab4_aiot_forecasting_predictive_analytics_uci_appliances/docs/06_model_training_and_metrics.md)**
    *   *Nội dung*: Cơ chế hoạt động của 5 mô hình (Baselines vs LR/RF/GB), tầm quan trọng của Time-series Split, và công thức/ý nghĩa vật lý lưới điện của **MAE, RMSE, MAPE, và Forecast Bias** (lệch thấp vs lệch cao).
8.  **[07_decision_layer.md](file:///e:/AIoT/Day-4/lab4_aiot_forecasting_predictive_analytics_uci_appliances_code/lab4_aiot_forecasting_predictive_analytics_uci_appliances/docs/07_decision_layer.md)**
    *   *Nội dung*: Tầng ra quyết định ánh xạ rủi ro theo phân vị xác suất thống kê ($70\%, 90\%, 97\%$), chỉ thị khuyến nghị hành động tương ứng và cấu trúc log đối soát `forecast_log.csv`.
9.  **[08_api_forecast_workflow.md](file:///e:/AIoT/Day-4/lab4_aiot_forecasting_predictive_analytics_uci_appliances_code/lab4_aiot_forecasting_predictive_analytics_uci_appliances/docs/08_api_forecast_workflow.md)**
    *   *Nội dung*: Luồng FastAPI cold start, sơ đồ chuỗi (Sequence Diagram), ví dụ JSON Request/Response mẫu và các giao thức kết nối bên thứ ba (Dashboard/MQTT).

### Phần IV: Đánh giá mã nguồn & An toàn vận hành
10. **[09_code_review.md](file:///e:/AIoT/Day-4/lab4_aiot_forecasting_predictive_analytics_uci_appliances_code/lab4_aiot_forecasting_predictive_analytics_uci_appliances/docs/09_code_review.md)**
    *   *Nội dung*: Báo cáo đánh giá mã nguồn cấp độ Senior phân tích 10 chiều kỹ thuật phần mềm (modularity, SoC, scalability). Nhận diện các anti-patterns nguy hiểm (ghi CSV đồng thời) và đề xuất sơ đồ tái cấu trúc (refactoring) module.
11. **[10_safety_fail_safe.md](file:///e:/AIoT/Day-4/lab4_aiot_forecasting_predictive_analytics_uci_appliances_code/lab4_aiot_forecasting_predictive_analytics_uci_appliances/docs/10_safety_fail_safe.md)**
    *   *Nội dung*: Phân tích 8 nhóm rủi ro an toàn lưới điện vật lý. Thiết kế kiến trúc fail-safe 3 lớp, **mã nguồn nhúng ESP32 Safe Interlock C++** quy tắc khóa cứng, logic ping timeout dự phòng cục bộ, Hồi quy phân vị và ngắt cứng ngắt nguồn khẩn cấp.

### Phần V: Lộ trình phát triển & Sách hướng dẫn
12. **[11_development_roadmap.md](file:///e:/AIoT/Day-4/lab4_aiot_forecasting_predictive_analytics_uci_appliances_code/lab4_aiot_forecasting_predictive_analytics_uci_appliances/docs/11_development_roadmap.md)**
    *   *Nội dung*: Lộ trình 3 cấp độ nâng cấp hệ thống (Học tập, Kỹ thuật, Công nghiệp) và Phễu đường dẫn học tập 4 giai đoạn rèn luyện 7 khía cạnh năng lực cho học viên.
13. **[HANDBOOK.md](file:///e:/AIoT/Day-4/lab4_aiot_forecasting_predictive_analytics_uci_appliances_code/lab4_aiot_forecasting_predictive_analytics_uci_appliances/docs/HANDBOOK.md)**
    *   *Nội dung*: **Cuốn Sách hướng dẫn Kỹ thuật chuyên sâu (Technical Handbook) tổng hợp**. Tích hợp từ điển thuật ngữ chuyên ngành (glossary), tóm tắt 8 lớp, kỹ nghệ đặc trưng lượng giác, luồng API mẫu, cẩm nang debug lỗi KeyError/NaN, FAQ và MLOps roadmap.

---

## 🎯 Ý nghĩa Thực tế của Lab 4 trong Đô thị Thông minh (AIoT Context)

Dự báo năng lượng không chỉ dừng lại ở việc hiển thị một con số trên màn hình Dashboard đẹp mắt. Trong hệ sinh thái **Lưới điện thông minh (Smart Grid)** và **Tòa nhà thông minh (Smart Building)**, dự báo phụ tải (Load Forecasting) chính là "bộ não" kích hoạt các chiến lược tối ưu hóa:

1.  **Chuyển dịch phụ tải (Load Shifting)**: Dự báo trước đỉnh phụ tải tiêu thụ điện của ngôi nhà vào giờ cao điểm, từ đó hệ thống điều khiển thông minh tự động dịch chuyển thời gian hoạt động của các thiết bị tiêu thụ nhiều điện (ví dụ: máy sấy quần áo, trạm sạc xe điện) sang khung giờ thấp điểm có giá điện rẻ hơn.
2.  **Quản lý nguồn năng lượng phân tán (DERs - Distributed Energy Resources)**: Kết hợp dự báo phụ tải với dự báo sản lượng điện mặt trời áp mái. Nếu dự báo hộ gia đình sẽ tiêu thụ lượng điện lớn trong 1 giờ tới, hệ thống có thể chủ động sạc đầy pin lưu trữ năng lượng (ESS) từ trước hoặc giữ năng lượng lại thay vì bán rẻ lên lưới điện quốc gia.
3.  **Vận hành an toàn phòng chống quá tải**: Đưa ra khuyến cáo ngắt các thiết bị không thiết yếu trước khi hiện tượng sụt áp hoặc nhảy aptomat tổng xảy ra, bảo vệ an toàn cháy nổ cho toàn hệ thống điện gia đình.

Hãy bắt đầu hành trình nghiên cứu bằng việc mở tài liệu đầu tiên: **[00_project_overview.md](file:///e:/AIoT/Day-4/lab4_aiot_forecasting_predictive_analytics_uci_appliances_code/lab4_aiot_forecasting_predictive_analytics_uci_appliances/docs/00_project_overview.md)**.
