# HƯỚNG DẪN XUẤT BẢN TÀI LIỆU KỸ THUẬT SANG ĐỊNH DẠNG HTML (PORTABLE DOCUMENTATION PORTAL)

Dự án **Lab 4: Energy Forecasting** tích hợp sẵn một công cụ chuyển đổi tự động hệ thống tài liệu kỹ thuật từ định dạng Markdown `.md` thô sang định dạng **Trang Web HTML phản hồi cao (Responsive HTML Documentation Portal)** nằm tại thư mục `html_docs/`.

Portal này được thiết kế với giao diện cao cấp kiểu **GitBook / ReadTheDocs**, hỗ trợ đầy đủ tiếng Việt có dấu, đồ thị nhúng động, bảng dữ liệu, khối mã nguồn (code blocks) và các hộp cảnh báo an toàn vật lý cực kỳ trực quan.

---

## 🚀 Tính năng vượt trội của Bản xuất bản HTML

1.  **Thanh điều hướng bên trái (Sticky Sidebar)**: Giúp người học nhanh chóng nhảy giữa các học phần từ 00 đến 11, Handbook và Trang chủ mà không cần quay lại.
2.  **Tương thích Di động (Responsive Layout)**: Tự động tối ưu giao diện khi đọc trên Laptop, Máy tính bảng (Tablet) hoặc Điện thoại (Mobile).
3.  **Hộp cảnh báo kiểu GitHub (Custom Alert Boxes)**: Các thẻ `[!NOTE]`, `[!TIP]`, `[!WARNING]`, `[!IMPORTANT]`, và `[!CAUTION]` được biên dịch thành các hộp màu nổi bật đi kèm icon sinh động.
4.  **Sơ đồ động Mermaid (Dynamic Mermaid JS)**: Tích hợp thư viện Mermaid JS từ CDN công khai. Toàn bộ sơ đồ dạng luồng hoặc kiến trúc sẽ được render trực tiếp dạng ảnh vector **SVG sắc nét**, có thể thu phóng trên trình duyệt.
5.  **Bản đồ liên kết tự động (Hrefs Link Porting)**: Toàn bộ các liên kết trỏ tới tệp `.md` (bao gồm cả các liên kết tuyệt đối lẫn tương đối) được tự động chuyển thành định dạng `.html` tương ứng cục bộ, bảo đảm Portal có thể chạy **hoàn toàn ngoại tuyến (offline)** bằng cách click đúp trực tiếp vào file.

---

## 🛠️ Hướng dẫn cài đặt và Chạy chuyển đổi

Để xuất bản hoặc cập nhật lại hệ thống HTML, bạn chỉ cần thực hiện 2 bước đơn giản trên Terminal/PowerShell:

### Bước 1: Cài đặt thư viện Python Markdown
```bash
pip install markdown
```

### Bước 2: Chạy script chuyển đổi tự động
```bash
python tools/md_to_html.py
```

*Lưu ý*: Script chuyển đổi có tích hợp cơ chế tự động cài đặt `markdown` thông qua `pip` nếu phát hiện máy chủ thiếu thư viện này, bảo đảm quy trình diễn ra trơn tru nhất.

---

## 📂 Cấu trúc thư mục đầu ra sau khi chạy

Sau khi chạy thành công, thư mục `html_docs/` sẽ được tự động khởi tạo với cấu trúc sau:

```text
lab4_aiot_forecasting/
├── tools/
│   └── md_to_html.py            # Script chuyển đổi (Python)
├── docs/
│   └── README_HTML_EXPORT.md    # Tài liệu hướng dẫn này
└── html_docs/                   # THƯ MỤC CỔNG THÔNG TIN HTML (Đầu ra)
    ├── index.html               # Trang chủ Portal (Landing Page tổng hợp)
    ├── 00_project_overview.html # Chi tiết học phần 00
    ├── 01_architecture.html     # Chi tiết học phần 01
    ├── ...                      # Các học phần từ 02 đến 11
    ├── HANDBOOK.html            # Sách hướng dẫn kỹ thuật tổng hợp
    └── README.html              # Trang chủ mục lục bổ trợ
```

---

## 🖥️ Hướng dẫn sử dụng học tập

*   **Đọc Offline**: Hãy mở thư mục `html_docs/` và click đúp vào file **`index.html`** để mở Cổng thông tin trên bất kỳ trình duyệt nào (Chrome, Edge, Firefox, Safari).
*   **Chia sẻ tiện lợi**: Bạn có thể nén toàn bộ thư mục `html_docs/` gửi cho bạn bè hoặc upload trực tiếp lên các dịch vụ hosting tĩnh (như GitHub Pages, Vercel, Netlify) để chia sẻ tài liệu trực tuyến miễn phí.
