# Metadata và Event trong Lab 6

## 1. Metadata là gì?

Metadata là dữ liệu mô tả ảnh.

Nó trả lời các câu hỏi:

- Ảnh này có ID gì?
- Ảnh đến từ thiết bị nào?
- Ảnh được tạo lúc nào?
- Ảnh đến từ upload, camera hay motion capture?
- File ảnh gốc nằm ở đâu?
- File ảnh xử lý nằm ở đâu?
- Ảnh rộng/cao bao nhiêu?
- Độ sáng trung bình là bao nhiêu?
- Xử lý mất bao lâu?

Trong Lab 6, metadata được ghi vào bảng `images` của cơ sở dữ liệu:

```text
outputs/lab6.db
```

Schema hiện tại:

| Cột | Ý nghĩa |
|---|---|
| `image_id` | ID ảnh |
| `device_id` | Thiết bị/client tạo ảnh |
| `timestamp` | Thời điểm ghi ảnh |
| `source_type` | Nguồn ảnh |
| `image_path` | Đường dẫn ảnh gốc |
| `processed_path` | Đường dẫn ảnh xử lý |
| `width` | Chiều rộng ảnh gốc |
| `height` | Chiều cao ảnh gốc |
| `brightness` | Độ sáng trung bình |
| `processing_status` | Trạng thái xử lý |
| `processing_time_ms` | Thời gian xử lý |
| `note` | Ghi chú thêm |

## 2. Event là gì?

Event là sự kiện vận hành sinh ra từ dữ liệu hoặc hành động của hệ thống.

Nó trả lời các câu hỏi:

- Có chuyện gì vừa xảy ra?
- Mức độ nghiêm trọng là gì?
- Điểm số hoặc chỉ số liên quan là bao nhiêu?
- Vì sao event này được tạo?
- Người dùng hoặc hệ thống nên làm gì tiếp theo?

Trong Lab 6, event được ghi vào bảng `events` của cơ sở dữ liệu:

```text
outputs/lab6.db
```

Schema hiện tại:

| Cột | Ý nghĩa |
|---|---|
| `event_id` | ID event |
| `image_id` | ID ảnh hoặc video liên quan |
| `timestamp` | Thời điểm event |
| `event_type` | Loại event |
| `score` | Điểm số liên quan |
| `severity` | Mức độ |
| `explanation` | Giải thích |
| `action_hint` | Gợi ý hành động |

## 3. Metadata khác event như thế nào?

Metadata là mô tả dữ liệu. Event là diễn giải vận hành.

Ví dụ một ảnh có brightness bằng `0.0`:

- Metadata ghi rằng ảnh có brightness `0.0`, kích thước `640x480`, source là `camera`.
- Event diễn giải rằng đây là `LOW_LIGHT`, severity `WARNING`, và gợi ý cải thiện ánh sáng.

Bảng so sánh:

| Tiêu chí | Metadata | Event |
|---|---|---|
| Mục đích | Mô tả ảnh | Ghi nhận điều xảy ra |
| Gắn với | Một ảnh cụ thể | Ảnh, video hoặc trạng thái vận hành |
| Tính chất | Khách quan, đo đạc | Có diễn giải, có mức độ |
| Ví dụ | width, height, brightness | LOW_LIGHT, MOTION_DETECTED |
| Dùng cho | Tra cứu, phân tích dữ liệu | Dashboard, cảnh báo, automation |

## 4. Một ảnh có thể có nhiều event

Trong Lab 6, một ảnh motion capture thường có thể sinh hai event:

1. Event xử lý ảnh từ `log_image_pipeline()`, ví dụ `IMAGE_PROCESSED`.
2. Event chuyển động từ `motion_capture()`, ví dụ `MOTION_DETECTED`.

Điều này giống hệ thống IoT thật: một bản ghi sensor có thể dẫn đến nhiều event nghiệp vụ.

Ví dụ:

```text
image_id = img_97a015dbd0
metadata: ảnh từ motion_capture, brightness 133.93
event 1: IMAGE_PROCESSED
event 2: MOTION_DETECTED, score 16473.0
```

## 5. Event severity hiện tại

Lab 6 đang dùng hai mức:

| Severity | Ý nghĩa |
|---|---|
| `NORMAL` | Trạng thái bình thường |
| `WARNING` | Có vấn đề cần chú ý |

Các rule hiện tại:

- `brightness < 70` sinh `LOW_LIGHT` với severity `WARNING`.
- Ảnh xử lý bình thường sinh `IMAGE_PROCESSED` với severity `NORMAL`.
- Ghi video sinh `VIDEO_RECORDED` với severity `NORMAL`.
- Motion score vượt `min_area` sinh `MOTION_DETECTED` với severity `WARNING`.
- Motion score không vượt ngưỡng sinh `NO_SIGNIFICANT_MOTION` với severity `NORMAL`.

## 6. Ý nghĩa trong sản phẩm AIoT

Trong sản phẩm thật, metadata và event thường được tách rõ:

- Metadata giúp lưu lịch sử dữ liệu cảm biến.
- Event giúp hệ thống phản ứng.

Ví dụ ứng dụng camera nhà thông minh:

- Metadata: camera cửa trước, ảnh 1280x720, brightness 35, timestamp.
- Event: `LOW_LIGHT`, cần bật đèn.
- Event khác: `PERSON_DETECTED`, gửi thông báo đến điện thoại.

Lab 6 mới dừng ở xử lý ảnh cơ bản, nhưng cấu trúc metadata/event đã là nền tảng tốt để mở rộng sang object detection, cảnh báo và dashboard sản phẩm.
