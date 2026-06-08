# HƯỚNG DẪN VẬN HÀNH & BIÊN SOẠN TÀI LIỆU VỚI MKDOCS MATERIAL

Hệ thống tài liệu chuyên sâu của **Lab 4: Energy Forecasting** đã được tích hợp đầy đủ công cụ **MkDocs** đi kèm với giao diện **MkDocs Material Theme** - tiêu chuẩn vàng công nghiệp cho các trang tài liệu kỹ thuật của các tập đoàn công nghệ lớn hiện nay.

Bộ tài liệu được trình bày dạng trang web có thanh tìm kiếm thông minh thời gian thực (instant search), hỗ trợ thay đổi giao diện sáng/tối (Dark/Light mode) tự động, bản địa hóa tiếng Việt 100%, tích hợp sao chép mã nguồn nhanh và hiển thị biểu đồ Mermaid động.

---

## 🌟 Các tính năng nổi bật của MkDocs Material trong Dự án

1.  **Instant Search (Tìm kiếm tức thời)**: Hộp tìm kiếm thông minh tự động gợi ý từ khóa, bôi đậm kết quả phù hợp ngay khi người dùng gõ phím.
2.  **Dark/Light Mode Switcher**: Tích hợp nút chuyển đổi giao diện sáng/tối ở góc trên bên phải, giúp người học đọc tài liệu dễ chịu vào ban đêm.
3.  **Tự động tạo Mục lục (Table of Contents)**: Mỗi trang tài liệu đều hiển thị một mục lục phụ ở bên phải màn hình, tự động cuộn (spy scroll) theo vị trí đọc hiện tại.
4.  **Tối ưu hóa Code Blocks**: Hỗ trợ bôi màu cú pháp mã nguồn (Pygments highlighting) và tích hợp sẵn nút sao chép nhanh (copy-to-clipboard) ở góc mỗi khối code.
5.  **Dịch thuật Tiếng Việt**: Toàn bộ giao diện tìm kiếm, chỉ số định hướng và các nhãn liên kết được cấu hình bản địa hóa tiếng Việt hoàn toàn.
6.  **Biên dịch sơ đồ Mermaid**: Các sơ đồ lưu trình và kiến trúc hệ thống dạng mã nguồn Mermaid được tự động vẽ thành sơ đồ vector SVG tương tác mượt mà.

---

## 🛠️ Hướng dẫn cài đặt và Khởi chạy

Để xem trước (preview) hoặc đóng gói (build) trang tài liệu trên máy tính của bạn, hãy thực hiện các bước sau trên terminal của workspace:

### Bước 1: Cài đặt MkDocs và Material Theme
Chạy lệnh sau để tải các gói thư viện cần thiết:
```bash
pip install mkdocs mkdocs-material
```

### Bước 2: Chạy máy chủ xem trước cục bộ (Live Preview)
Để khởi chạy máy chủ phát triển thời gian thực, phục vụ việc đọc tài liệu hoặc chỉnh sửa trực quan:
```bash
mkdocs serve
```
*Kết quả đầu ra*: Máy chủ sẽ khởi chạy tại đường dẫn cục bộ **`http://127.0.0.1:8000/`**.
*Tính năng Hot Reload*: Bất kỳ thay đổi nào của bạn trên các file `.md` trong thư mục `docs/` sẽ được tự động biên dịch và làm mới trên trình duyệt ngay lập tức mà không cần khởi động lại lệnh.

### Bước 3: Đóng gói trang tài liệu tĩnh (Production Build)
Khi muốn phân phối tài liệu dưới dạng trang web tĩnh hoàn chỉnh để upload lên các dịch vụ hosting (như GitHub Pages, Vercel, Netlify):
```bash
mkdocs build
```
*Kết quả đầu ra*: Một thư mục mới có tên là **`site/`** sẽ được tạo ra tại thư mục gốc của dự án. Thư mục này chứa toàn bộ mã nguồn HTML, CSS, JS tĩnh đã được tối ưu hóa dung lượng (minified), sẵn sàng để triển khai trực tuyến.

---

## 📂 Sắp xếp Cấu trúc Tệp tin

*   **`mkdocs.yml`**: Tệp tin cấu hình chính nằm ở thư mục gốc của dự án. Định nghĩa tiêu đề trang, cách cấu hình Material Theme, kích hoạt các markdown extensions tiện ích và định tuyến cây điều hướng (navigation).
*   **`docs/`**: Thư mục chứa toàn bộ các file `.md` tài liệu gốc. MkDocs sẽ tự động quét thư mục này và chuyển hóa thành các trang HTML tương ứng.
*   **`site/`**: Thư mục đầu ra chứa trang web tĩnh sau khi chạy lệnh `mkdocs build`.

---

## 📝 Quy tắc mở rộng định dạng Admonition (Alerts) trong MkDocs

Ngoài cấu trúc trích dẫn khối thô kiểu GitHub, MkDocs Material hỗ trợ các khối cảnh báo **Admonition** cực kỳ bắt mắt với cú pháp mở rộng:

```markdown
!!! note "Tiêu đề tùy chọn"
    Nội dung ghi chú ở đây. Lưu ý phải lùi vào 4 dấu cách.

!!! tip "Gợi ý hữu ích"
    Nội dung gợi ý hoặc mẹo phát triển.

!!! warning "Cảnh báo quá tải"
    Cảnh báo về rủi ro dòng điện hoặc sập mạng.
```

Hãy sử dụng các cú pháp admonition này khi viết thêm tài liệu mới để trang web hiển thị các hộp thoại thông tin một cách chuẩn hóa và chuyên nghiệp nhất!
