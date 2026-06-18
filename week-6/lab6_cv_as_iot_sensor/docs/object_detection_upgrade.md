# OpenCV Built-In Person Motion Upgrade

## Mục tiêu

Bản nâng cấp này mở rộng Lab 6 từ motion detection cơ bản sang phát hiện người đang chuyển động.

Không dùng model ngoài hoặc framework nhận diện vật thể bên ngoài. Backend chỉ dùng OpenCV built-in:

- `MOG2`, `KNN`, hoặc frame diff để tạo motion mask.
- `HOGDescriptor_getDefaultPeopleDetector()` để phát hiện bbox người.

## Luồng xử lý

```text
camera frame
→ motion mask
→ morphology open/close
→ motion score
→ HOG person bbox
→ motion pixels inside bbox
→ PERSON_MOTION_CONFIRMED hoặc NO_PERSON_MOTION
```

Ảnh raw và ảnh processed chỉ được lưu khi hệ thống xác nhận `PERSON_MOTION_CONFIRMED`.

## Reason code

- `NO_GLOBAL_MOTION`: motion score dưới ngưỡng.
- `NO_PERSON_DETECTED`: HOG không tìm thấy người.
- `PERSON_NO_MOTION_OVERLAP`: có bbox người nhưng motion trong bbox chưa đủ.
- `LOW_QUALITY_DARK`, `LOW_QUALITY_OVEREXPOSED`, `LOW_QUALITY_BLURRY`: chất lượng frame không đủ tin cậy.
- `PERSON_MOTION_CONFIRMED`: có người đang chuyển động và ảnh đã được lưu.

## Hạn chế

HOG có thể bỏ sót người bị che khuất, đang ngồi, quá gần camera, ánh sáng kém, ảnh mờ hoặc góc nhìn lạ.
