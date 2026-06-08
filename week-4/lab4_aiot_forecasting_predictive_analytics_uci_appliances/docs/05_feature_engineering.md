# KỸ NGHỆ ĐẶC TRƯNG CHUỖI THỜI GIAN (FEATURE ENGINEERING CHO AIoT)

Trong các bài toán học máy thông thường, các bản ghi dữ liệu được coi là độc lập và có cùng phân phối (I.I.D). Tuy nhiên, dữ liệu IoT bản chất là **Chuỗi thời gian (Time-series)**. Các giá trị đo đạc có sự liên kết chặt chẽ và phụ thuộc nặng nề vào quá khứ. 

Tài liệu này giải thích chi tiết cơ chế hoạt động, công thức toán học, ví dụ trực quan bằng bảng nhỏ và ý nghĩa vận hành của các loại đặc trưng chuỗi thời gian trong **Lab 4**, giúp sinh viên thấu hiểu sâu sắc cách "chuẩn bị tri thức" cho mô hình trước khi dự báo.

---

## 1. Tại sao Telemetry IoT thô là KHÔNG ĐỦ để Dự báo?

Nếu ta chỉ đưa các giá trị cảm biến tại thời điểm hiện tại $t$ vào mô hình (ví dụ: nhiệt độ bếp đang là 25°C, công suất điện đang là 80 Wh), mô hình sẽ hoàn toàn **"mù lòa"** trước xu hướng vận hành.

### Lý do 1: Thiếu ngữ cảnh Lịch sử (Temporal Context)
Một giá trị thô $80$ Wh ở hiện tại không cho mô hình biết hệ thống đang ở trạng thái nào:
*   *Kịch bản A*: 10 phút trước là $20$ Wh $\rightarrow$ Phụ tải đang **tăng vọt** dữ dội (kích hoạt thiết bị công suất cao).
*   *Kịch bản B*: 10 phút trước là $300$ Wh $\rightarrow$ Phụ tải đang **lao dốc** mạnh (vừa tắt thiết bị lớn).
Nếu chỉ nhìn con số $80$ Wh hiện tại, mô hình sẽ đưa ra cùng một dự báo cho cả hai kịch bản trái ngược này, dẫn đến sai số rất lớn.

### Lý do 2: Thiếu thông tin động học & tuần hoàn
Nhiệt độ phòng tăng 1°C có thể là do thời tiết bên ngoài ấm lên (từ từ), hoặc do bếp từ vừa được bật (đột ngột). Sự thiếu hụt gia tốc (sai phân) và mốc thời gian tuần hoàn (giờ cao điểm/thấp điểm) khiến các thuật toán học máy không thể phân biệt được hành vi sinh hoạt của con người.

---

## 2. Đặc trưng Độ trễ (Lag Features)

### Định nghĩa & Cơ chế
Đặc trưng độ trễ (Lag) lấy giá trị của biến mục tiêu trong quá khứ làm đặc trưng đầu vào cho thời điểm hiện tại.
$$\text{Lag}_k(y_t) = y_{t-k}$$

### Ví dụ trực quan bằng Bảng nhỏ ($k=1$ và $k=2$):

| Thời gian ($t$) | Appliances thô ($y_t$) | appliances_lag_1 ($y_{t-1}$) | appliances_lag_2 ($y_{t-2}$) | Ghi chú |
| :--- | :--- | :--- | :--- | :--- |
| 12:00:00 | **50 Wh** | NaN | NaN | Chưa đủ lịch sử quá khứ. |
| 12:10:00 | **60 Wh** | **50 Wh** | NaN | `lag_1` lấy giá trị lúc 12:00. |
| 12:20:00 | **90 Wh** | **60 Wh** | **50 Wh** | `lag_1` lấy 12:10, `lag_2` lấy 12:00. |
| 12:30:00 | **80 Wh** | **90 Wh** | **60 Wh** | Đẩy dịch chuyển tuần tự xuôi dòng. |

### Ý nghĩa trong AIoT
Công suất tiêu thụ điện có tính **quán tính hành vi**. Nếu điều hòa đang bật ở thời điểm $t-1$ (10 phút trước) và $t-2$ (20 phút trước), khả năng rất cao là nó vẫn đang tiếp tục hoạt động ở thời điểm hiện tại $t$.

---

## 3. Đặc trưng Cửa sổ trượt (Rolling Features)

### Định nghĩa & Cơ chế
Tính toán một chỉ số thống kê (trung bình hoặc độ lệch chuẩn) trên một cửa sổ thời gian trượt về quá khứ có độ rộng cố định $W$.
$$\text{Rolling Mean}_W(y_t) = \frac{1}{W} \sum_{i=0}^{W-1} y_{t-i}$$

### Ví dụ trực quan bằng Bảng nhỏ (Rolling Mean với cửa sổ $W=3$):

| Thời gian ($t$) | Appliances thô ($y_t$) | appliances_rolling_mean_3 | Phép toán tính trung vị |
| :--- | :--- | :--- | :--- |
| 12:00:00 | **50 Wh** | NaN | Chưa đủ 3 phần tử. |
| 12:10:00 | **60 Wh** | NaN | Chưa đủ 3 phần tử. |
| 12:20:00 | **100 Wh** | **70.0 Wh** | $(50 + 60 + 100) / 3 = 70.0$ |
| 12:30:00 | **90 Wh** | **83.3 Wh** | $(60 + 100 + 90) / 3 = 83.3$ |

### Ý nghĩa trong AIoT
*   **Rolling Mean**: Lọc bỏ các đỉnh nhọn bất thường mang tính tức thời (nhiễu gai), giúp mô hình nắm bắt xu hướng nền của phụ tải trong 1 tiếng hoặc 4 tiếng gần nhất.
*   **Rolling Std**: Đo lường sự biến động. STD cao cho thấy các thiết bị công suất lớn đang liên tục được bật/tắt (hệ thống không ổn định).

---

## 4. Đặc trưng Sai phân (Delta Features)

### Định nghĩa & Cơ chế
Đo lường mức độ thay đổi phụ tải điện năng so với thời điểm quá khứ cách đó $k$ bước:
$$\Delta_k(y_t) = y_t - y_{t-k}$$

### Ví dụ trực quan bằng Bảng nhỏ ($\Delta_1$ và $\Delta_2$):

| Thời gian ($t$) | Appliances thô ($y_t$) | appliances_delta_1 | appliances_delta_2 | Phép toán |
| :--- | :--- | :--- | :--- | :--- |
| 12:00:00 | **50 Wh** | NaN | NaN | Không có quá khứ đối chiếu. |
| 12:10:00 | **60 Wh** | **+10 Wh** | NaN | $60 - 50 = +10$ Wh |
| 12:20:00 | **100 Wh** | **+40 Wh** | **+50 Wh** | $\Delta_1=100-60$; $\Delta_2=100-50$ |
| 12:30:00 | **70 Wh** | **-30 Wh** | **+10 Wh** | Phụ tải giảm mạnh $70 - 100 = -30$ Wh |

### Ý nghĩa trong AIoT
Cung cấp **gia tốc (hướng và cường độ thay đổi)**. Gia trị $\Delta_1$ dương rất lớn cho biết một thiết bị công suất cao vừa mới được bật lên, giúp mô hình dự báo xu hướng tiếp tục tăng hoặc bão hòa tiếp theo.

---

## 5. Đặc trưng Thời gian Tuần hoàn (Cyclic Time Features)

### Hạn chế của số thường
Nếu biểu diễn giờ từ $0$ đến $23$, mốc **23:50** ($23.83$) và **00:10** ($0.17$) về mặt số học cách nhau rất xa ($|23.83 - 0.17| = 23.66$), nhưng thực tế vật lý sinh hoạt chỉ cách nhau đúng **20 phút**.

### Giải pháp Lượng giác (Sin/Cos Projection)
Chiếu giờ lên vòng tròn lượng giác có chu kỳ 24 giờ:
$$\theta = \frac{2\pi \cdot \text{Hour}}{24.0}, \quad x = \sin(\theta), \quad y = \cos(\theta)$$

### Ví dụ trực quan bằng Bảng nhỏ:

| Thời gian thực | Giờ số thực (Hour) | Góc $\theta$ (Radian) | hour_sin ($x$) | hour_cos ($y$) | Khoảng cách hình học |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **23:50:00** | $23.83$ | $6.24$ Rad | **-0.043** | **+0.999** | **Cực kỳ gần nhau** trên vòng tròn lượng giác (Cos tiệm cận 1, Sin tiệm cận 0). |
| **00:00:00** | $0.00$ | $0.00$ Rad | **0.000** | **+1.000** |
| **00:10:00** | $0.17$ | $0.04$ Rad | **+0.043** | **+0.999** |

---

## 6. Cách Tạo nhãn `target_future` bằng Kỹ thuật Shifting

Để biến bài toán chuỗi thời gian thành bài toán Học có giám sát, ta dịch nhãn ngược lại tương lai $h$ bước (Horizon Steps = 1):
$$\text{target\_future}_t = y_{t+h}$$

### Ví dụ trực quan bằng Bảng nhỏ ($h=1$):

| Thời gian ($t$) | Đặc trưng hiện tại $X_t$ (Lag_1) | Appliances thực tế ($y_t$) | target_future ($y_{t+1}$) | Cặp dữ liệu huấn luyện học máy |
| :--- | :--- | :--- | :--- | :--- |
| 12:00:00 | NaN | **50 Wh** | **60 Wh** | (Không dùng vì đặc trưng bị NaN) |
| 12:10:00 | 50 Wh | **60 Wh** | **100 Wh** | Đầu vào: $[60, 50] \rightarrow$ Nhãn: **100** |
| 12:20:00 | 60 Wh | **100 Wh** | **90 Wh** | Đầu vào: $[100, 60] \rightarrow$ Nhãn: **90** |
| 12:30:00 | 100 Wh | **90 Wh** | *NaN* (chưa xảy ra) | (Dòng này bị loại bỏ khỏi tập Train) |

---

## 7. Làm thế nào để Tránh lỗi Rò rỉ Dữ liệu tương lai (Data Leakage)?

Rò rỉ dữ liệu tương lai xảy ra khi mô hình vô tình biết trước thông tin của tương lai $t+1$ khi đang thực hiện tính toán đặc trưng tại thời điểm $t$.

### 3 Nguyên tắc Vàng phòng chống Data Leakage trong Lab 4:
1.  **Duy nhất dịch nhãn ngược**: Chỉ duy nhất cột nhãn `target_future` được phép sử dụng shift âm (`.shift(-1)`).
2.  **Đặc trưng tuyệt đối không hướng tương lai**: Tất cả các đặc trưng Lag, Rolling, Delta bắt buộc phải dùng shift dương hoặc trượt về quá khứ để bảo đảm mối quan hệ nhân quả vật lý:
    $$\text{Đặc trưng}_t = f(\text{Dữ\_liệu}_{\le t})$$
3.  **Chia dữ liệu theo mốc thời gian (Time-series Split)**: Cắt bảng dữ liệu theo chiều dọc tuyến tính thời gian. Tuyệt đối không dùng `train_test_split(..., shuffle=True)` làm trộn lẫn xáo trộn các dòng dữ liệu.

---

## 8. Các Đặc trưng Quan trọng nhất để Dự báo Điện năng Tiêu thụ

Trong quá trình phân tích huấn luyện offline, các đặc trưng được mô hình đánh giá quan trọng nhất (Feature Importances) đối với bài toán phụ tải điện bao gồm:

1.  **`appliances_lag_1` và `appliances_lag_2` (Độ trễ gần nhất)**: Chiếm trọng số quan trọng nhất (> 60% mức độ đóng góp). Phản ánh trạng thái liền kề của thiết bị (Đang bật thì khả năng bật tiếp là cực cao).
2.  **`appliances_rolling_mean_3` và `rolling_mean_6` (Trend ngắn hạn)**: Giúp mô hình nhận biết xu thế nền đang tăng hay giảm của cả ngôi nhà.
3.  **`hour_sin` và `hour_cos` (Chu kỳ ngày/đêm)**: Xác định rõ ràng các khung giờ sinh hoạt cao điểm (18:00 - 21:00) và thấp điểm (đêm muộn).
4.  **`T_out` và `RH_out` (Thông số thời tiết ngoài trời)**: Tác động gián tiếp nhưng rất mạnh mẽ đến hoạt động của các thiết bị sưởi ấm hoặc làm mát (HVAC).

---

## 9. Phương pháp Mở rộng Đặc trưng cho Hệ thống AIoT Thực tế (Production)

Để nâng cấp độ chính xác của mô hình lên cấp độ thương mại, ta cần bổ sung thêm 4 nhóm đặc trưng nâng cao:

### 1. Đặc trưng Tương tác nhiệt (Interaction Features)
*   *Mô tả*: Sự chênh lệch giữa nhiệt độ trong nhà và ngoài trời ảnh hưởng trực tiếp đến công suất làm lạnh của điều hòa.
*   *Đặc trưng mới*: `temp_diff = T_indoor - T_out` hoặc `T_out * RH_out` (chỉ số cảm giác nhiệt thực tế).

### 2. Đặc trưng Cửa sổ trượt của Thời tiết (Weather Rolling Features)
*   *Mô tả*: Ngôi nhà không phản ứng tức thời với thời tiết ngoài trời mà có quán tính hấp thụ nhiệt chậm (khoảng 1 - 2 tiếng).
*   *Đặc trưng mới*: `T_out_rolling_mean_6` (Trung bình nhiệt độ ngoài trời trong 1 tiếng trước).

### 3. Đặc trưng Lịch và Ngày lễ đặc biệt (Calendar Events Features)
*   *Mô tả*: Hành vi sử dụng điện ngày Tết, ngày nghỉ lễ quốc khánh, hoặc ngày nắng nóng kỷ lục hoàn toàn khác ngày thường.
*   *Đặc trưng mới*: `is_holiday` (nhị phân), `is_summer_peak` (khung giờ mùa hè cao điểm).

### 4. Đặc trưng Trạng thái hoạt động thiết bị (Device Actuator State)
*   *Mô tả*: Nếu hệ thống có kết nối thông tin phản hồi từ Smart Plug.
*   *Đặc trưng mới*: `hvac_state_lag_1` (`0` - đang tắt, `1` - đang bật), phản ánh trực tiếp sự thay đổi tải mà không cần đoán gián tiếp qua dòng điện.
