# AI Agent Design Skill: Premium AIoT Dashboard Architect (Vanilla HTML/CSS/JS Edition)

Tài liệu này chứa các quy tắc thiết kế giao diện (UI/UX) cao cấp, được trích xuất và tối ưu hóa từ kho lưu trữ `taste-skill` để áp dụng riêng cho các dự án web sử dụng **Vanilla HTML, CSS và JavaScript** (như trang demo phân loại ảnh và bảng điều khiển cảm biến của **Week 5**).

---

## 1. Nguyên Tắc Cốt Lõi (Core Directives)

* **Vibe: Ethereal Dark Glassmorphism**: Giao diện mang phong cách bảng điều khiển công nghệ cao, sử dụng nền tối sâu (deep OLED black), các thẻ kính mờ (glassmorphism cards) có viền hairline sáng sắc nét, cùng các dải màu gradient radial phát sáng huyền ảo phía sau.
* **Typography**: Cấm sử dụng các font mặc định nhàm chán (Arial, Times New Roman). Sử dụng các font chữ hiện đại từ Google Fonts như **`Plus Jakarta Sans`** hoặc **`Outfit`** để tạo cảm giác công nghệ, đắt tiền.
* **Micro-interactions**: Tất cả các tương tác (hover, click, thay đổi trạng thái) phải mượt mà, sử dụng các hàm nội suy động lực học vật lý (`cubic-bezier`), không dùng các transition mặc định.

---

## 2. Bảng Màu Thiết Kế (Harmonic Color Palette)

```css
:root {
  --bg-base: #050608;          /* OLED Black */
  --bg-card: rgba(13, 17, 24, 0.7); /* Thẻ kính mờ */
  --border-light: rgba(255, 255, 255, 0.08); /* Viền hairline siêu mỏng */
  --border-glow: rgba(56, 189, 248, 0.2);  /* Viền phát sáng xanh cyan */
  
  /* Màu nhấn (Accent colors) */
  --cyan: #38bdf8;
  --blue: #2563eb;
  --indigo: #6366f1;
  
  /* Màu trạng thái */
  --status-normal: #10b981;     /* Xanh lá (Normal) */
  --status-warning: #f59e0b;    /* Vàng (Warning) */
  --status-danger: #ef4444;     /* Đỏ (High/Danger) */
  
  /* Text */
  --text-primary: #f3f4f6;
  --text-secondary: #9ca3af;
  --text-muted: #6b7280;
}
```

---

## 3. Kiến Trúc Hộp Kính Hai Lớp (Double-Bezel Card Design)

Để giao diện không bị phẳng và rẻ tiền, tất cả các thẻ thông tin (`card`) và khu vực hiển thị ảnh phải được bao bọc trong cấu trúc khung kép (Double-Bezel):

```html
<!-- Cấu trúc HTML -->
<div class="card-wrapper">
  <div class="card-inner">
    <h3>Tiêu đề thẻ</h3>
    <p>Nội dung hiển thị...</p>
  </div>
</div>
```

```css
/* Cấu trúc CSS */
.card-wrapper {
  background: rgba(255, 255, 255, 0.02);
  border: 1px solid var(--border-light);
  padding: 6px;
  border-radius: 24px; /* Bo góc lớn ở lớp ngoài */
  box-shadow: 0 20px 40px rgba(0, 0, 0, 0.3);
}

.card-inner {
  background: var(--bg-card);
  border: 1px solid var(--border-light);
  border-radius: 18px; /* Bo góc nhỏ hơn theo tỷ lệ đồng tâm */
  padding: 20px;
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
}
```

---

## 4. Hiệu Ứng Nút Nhấn & Island Button Architecture

Nút nhấn phải trông giống như một khối phần cứng có độ nảy khi click:

```css
button {
  background: linear-gradient(135deg, var(--blue), var(--indigo));
  color: var(--text-primary);
  border: 1px solid rgba(255, 255, 255, 0.1);
  padding: 12px 24px;
  border-radius: 9999px; /* Dạng viên thuốc */
  font-weight: 600;
  letter-spacing: 0.03em;
  cursor: pointer;
  transition: all 0.5s cubic-bezier(0.16, 1, 0.3, 1);
  box-shadow: 0 4px 12px rgba(37, 99, 235, 0.2);
}

button:hover {
  transform: translateY(-2px) scale(1.02);
  box-shadow: 0 8px 20px rgba(99, 102, 241, 0.4);
}

button:active {
  transform: translateY(1px) scale(0.98);
}
```

---

## 5. Chuyển Động Của Trạng Thái (Motion & Fluidity)

Khi gọi API suy luận AI, các trạng thái cập nhật kết quả không được xuất hiện đột ngột mà phải chuyển động mượt mà:

```css
/* Animation xuất hiện nhẹ nhàng */
@keyframes fadeInUp {
  from {
    opacity: 0;
    transform: translateY(20px);
    filter: blur(4px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
    filter: blur(0);
  }
}

.result-active {
  animation: fadeInUp 0.8s cubic-bezier(0.16, 1, 0.3, 1) forwards;
}
```

---

## 6. Danh Sách Kiểm Tra Trước Khi Xuất Bản UI (Pre-flight Checklist)

* [ ] Background có sử dụng màu tối OLED kết hợp gradient radial mờ ảo không?
* [ ] Đã nhúng font chữ cao cấp từ Google Fonts chưa? (Ưu tiên `Plus Jakarta Sans`).
* [ ] Các khối hiển thị ảnh và kết quả đã được bao bọc bởi cấu trúc Double-Bezel chưa?
* [ ] Các nút nhấn chính có bo góc dạng tròn viên thuốc mượt mà không?
* [ ] Bảng kết quả Top-K có các đường hairline mỏng tinh tế thay vì viền dày không?
* [ ] Tất cả hiệu ứng chuyển động có dùng `cubic-bezier(0.16, 1, 0.3, 1)` (mô phỏng lò xo vật lý) không?
