# -*- coding: utf-8 -*-
"""
Lab 4 AIoT Forecasting - Markdown to HTML Converter
Converts all Vietnamese technical documentation (.md) inside docs/ into a beautiful,
responsive HTML portal located in html_docs/ for students and engineers to study.
"""

import os
import re
import sys
from pathlib import Path

# Programmatic check and import of python-markdown
try:
    import markdown
except ImportError:
    print("Thư viện 'markdown' chưa được cài đặt. Tiến hành cài đặt tự động...")
    import subprocess
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "markdown"])
        import markdown
    except Exception as e:
        print(f"Lỗi: Không thể tự động cài đặt thư viện 'markdown'.")
        print("Vui lòng chạy lệnh sau trên terminal: pip install markdown")
        sys.exit(1)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DOCS_DIR = PROJECT_ROOT / "docs"
HTML_OUT_DIR = PROJECT_ROOT / "html_docs"

# Ordered list of documentation pages to keep the learning roadmap order in the sidebar
DOCS_ORDER = [
    "00_project_overview.md",
    "01_architecture.md",
    "02_data_flow.md",
    "03_runtime_and_dependencies.md",
    "04_dataset_and_schema.md",
    "05_feature_engineering.md",
    "06_model_training_and_metrics.md",
    "07_decision_layer.md",
    "08_api_forecast_workflow.md",
    "09_code_review.md",
    "10_safety_fail_safe.md",
    "11_development_roadmap.md",
    "HANDBOOK.md",
    "README.md"
]

PAGE_TITLES = {
    "00_project_overview.md": "00. Tổng quan dự án",
    "01_architecture.md": "01. Kiến trúc hệ thống AIoT",
    "02_data_flow.md": "02. Luồng dữ liệu tuần tự",
    "03_runtime_and_dependencies.md": "03. Luồng thực thi & Phụ thuộc",
    "04_dataset_and_schema.md": "04. Tập dữ liệu & Điền khuyết",
    "05_feature_engineering.md": "05. Kỹ nghệ đặc trưng thời gian",
    "06_model_training_and_metrics.md": "06. Mô hình hóa & Đo lường sai số",
    "07_decision_layer.md": "07. Tầng ra quyết định & Cảnh báo",
    "08_api_forecast_workflow.md": "08. Triển khai API FastAPI",
    "09_code_review.md": "09. Đánh giá chất lượng mã nguồn",
    "10_safety_fail_safe.md": "10. An toàn & Cơ chế Fail-safe",
    "11_development_roadmap.md": "11. Lộ trình phát triển & Học tập",
    "HANDBOOK.md": "📖 Sách hướng dẫn kỹ thuật (Handbook)",
    "README.md": "🏡 Trang chủ / Tài liệu Index"
}

CSS_STYLE = """
:root {
    --primary: #4f46e5;
    --primary-light: #e0e7ff;
    --primary-hover: #4338ca;
    --text-dark: #0f172a;
    --text-muted: #64748b;
    --bg-slate: #f8fafc;
    --bg-sidebar: #0f172a;
    --border-slate: #e2e8f0;
    --code-bg: #1e293b;
    --inline-code-bg: #f1f5f9;
    --inline-code-color: #e11d48;
}

* {
    box-sizing: border-box;
    margin: 0;
    padding: 0;
}

body {
    font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
    color: var(--text-dark);
    background-color: var(--bg-slate);
    line-height: 1.6;
    display: flex;
    min-height: 100vh;
}

/* Sidebar Navigation */
.sidebar {
    width: 320px;
    background-color: var(--bg-sidebar);
    color: #f8fafc;
    display: flex;
    flex-direction: column;
    position: fixed;
    top: 0;
    bottom: 0;
    left: 0;
    z-index: 100;
    box-shadow: 4px 0 10px rgba(0,0,0,0.1);
}

.sidebar-header {
    padding: 24px;
    border-bottom: 1px solid rgba(255,255,255,0.1);
}

.sidebar-header h1 {
    font-size: 20px;
    font-weight: 700;
    color: #ffffff;
    display: flex;
    align-items: center;
    gap: 8px;
}

.sidebar-header .badge {
    background-color: var(--primary);
    color: white;
    font-size: 11px;
    padding: 2px 8px;
    border-radius: 9999px;
    font-weight: 600;
    margin-top: 4px;
    display: inline-block;
}

.sidebar-nav {
    flex: 1;
    overflow-y: auto;
    padding: 16px 0;
}

.sidebar-nav-item {
    display: block;
    padding: 12px 24px;
    color: #cbd5e1;
    text-decoration: none;
    font-size: 14px;
    transition: all 0.2s ease;
    border-left: 4px solid transparent;
}

.sidebar-nav-item:hover {
    background-color: rgba(255,255,255,0.05);
    color: #ffffff;
    padding-left: 28px;
}

.sidebar-nav-item.active {
    background-color: rgba(79, 70, 229, 0.15);
    color: #ffffff;
    border-left-color: var(--primary);
    font-weight: 600;
}

.sidebar-footer {
    padding: 16px 24px;
    border-top: 1px solid rgba(255,255,255,0.1);
    font-size: 11px;
    color: #94a3b8;
    text-align: center;
}

/* Main Content Area */
.main-wrapper {
    margin-left: 320px;
    flex: 1;
    display: flex;
    flex-direction: column;
    min-height: 100vh;
}

.top-bar {
    background-color: #ffffff;
    border-bottom: 1px solid var(--border-slate);
    padding: 16px 40px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    position: sticky;
    top: 0;
    z-index: 90;
}

.top-bar-title {
    font-size: 14px;
    color: var(--text-muted);
    font-weight: 500;
}

.top-bar-links a {
    color: var(--primary);
    text-decoration: none;
    font-size: 14px;
    font-weight: 500;
    transition: color 0.2s;
}

.top-bar-links a:hover {
    color: var(--primary-hover);
    text-decoration: underline;
}

.content-container {
    flex: 1;
    padding: 48px 64px 80px 64px;
    max-width: 1012px;
    width: 100%;
    margin: 0 auto;
    background-color: #ffffff;
    box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05);
    border-radius: 8px;
    margin-top: 24px;
    margin-bottom: 24px;
}

/* Markdown Styling */
.markdown-body h1 {
    font-size: 32px;
    font-weight: 800;
    margin-bottom: 24px;
    padding-bottom: 12px;
    border-bottom: 2px solid var(--border-slate);
    color: #0f172a;
}

.markdown-body h2 {
    font-size: 22px;
    font-weight: 700;
    margin-top: 36px;
    margin-bottom: 16px;
    padding-bottom: 6px;
    border-bottom: 1px solid var(--border-slate);
    color: #1e293b;
}

.markdown-body h3 {
    font-size: 18px;
    font-weight: 600;
    margin-top: 28px;
    margin-bottom: 12px;
    color: #334155;
}

.markdown-body h4 {
    font-size: 16px;
    font-weight: 600;
    margin-top: 20px;
    margin-bottom: 8px;
    color: #475569;
}

.markdown-body p {
    margin-bottom: 16px;
    color: #334155;
    text-align: justify;
}

.markdown-body ul, .markdown-body ol {
    margin-bottom: 16px;
    padding-left: 24px;
}

.markdown-body li {
    margin-bottom: 8px;
    color: #334155;
}

.markdown-body a {
    color: var(--primary);
    text-decoration: none;
    transition: color 0.15s;
    font-weight: 500;
}

.markdown-body a:hover {
    color: var(--primary-hover);
    text-decoration: underline;
}

/* Blockquotes */
.markdown-body blockquote {
    padding: 12px 24px;
    border-left: 4px solid var(--border-slate);
    background-color: var(--bg-slate);
    margin-bottom: 20px;
    font-style: italic;
    color: var(--text-muted);
}

/* Code block styling */
.markdown-body pre {
    background-color: var(--code-bg);
    padding: 16px;
    border-radius: 8px;
    overflow-x: auto;
    margin-bottom: 20px;
}

.markdown-body pre code {
    background-color: transparent;
    color: #f8fafc;
    padding: 0;
    border-radius: 0;
    font-size: 13.5px;
    font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace;
}

.markdown-body code {
    background-color: var(--inline-code-bg);
    color: var(--inline-code-color);
    padding: 2px 6px;
    border-radius: 4px;
    font-size: 85%;
    font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace;
}

/* Table styling */
.markdown-body table {
    width: 100%;
    border-collapse: collapse;
    margin-bottom: 24px;
    font-size: 14.5px;
}

.markdown-body th, .markdown-body td {
    padding: 12px 16px;
    border: 1px solid var(--border-slate);
}

.markdown-body th {
    background-color: var(--bg-slate);
    font-weight: 600;
    text-align: left;
    color: #1e293b;
}

.markdown-body tr:nth-child(even) {
    background-color: #fafbfd;
}

/* Custom Alert Boxes (GitHub Alerts mapping) */
.alert {
    padding: 16px 20px;
    margin-bottom: 24px;
    border-radius: 8px;
    border-left-width: 4px;
    border-left-style: solid;
}

.alert-title {
    font-weight: 700;
    margin-bottom: 8px;
    font-size: 14.5px;
    display: flex;
    align-items: center;
    gap: 8px;
}

.alert-content p {
    margin-bottom: 0 !important;
    font-size: 14px;
    text-align: justify;
}

.alert-note {
    background-color: #eff6ff;
    border-left-color: #3b82f6;
    color: #1e40af;
}
.alert-note .alert-title { color: #1d4ed8; }

.alert-tip {
    background-color: #f0fdf4;
    border-left-color: #22c55e;
    color: #166534;
}
.alert-tip .alert-title { color: #15803d; }

.alert-important {
    background-color: #faf5ff;
    border-left-color: #a855f7;
    color: #6b21a8;
}
.alert-important .alert-title { color: #7e22ce; }

.alert-warning {
    background-color: #fffbeb;
    border-left-color: #f59e0b;
    color: #92400e;
}
.alert-warning .alert-title { color: #b45309; }

.alert-caution {
    background-color: #fef2f2;
    border-left-color: #ef4444;
    color: #991b1b;
}
.alert-caution .alert-title { color: #b91c1c; }

/* Mermaid Styling */
.mermaid {
    background-color: white !important;
    border: 1px solid var(--border-slate);
    border-radius: 8px;
    padding: 24px;
    display: flex;
    justify-content: center;
    margin-bottom: 24px;
    overflow-x: auto;
}

.footer {
    background-color: #ffffff;
    border-top: 1px solid var(--border-slate);
    padding: 24px;
    text-align: center;
    font-size: 13px;
    color: var(--text-muted);
    margin-top: auto;
}

/* Landing Page Grid */
.landing-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
    gap: 20px;
    margin-top: 24px;
}

.landing-card {
    background-color: #ffffff;
    border: 1px solid var(--border-slate);
    border-radius: 8px;
    padding: 20px;
    text-decoration: none;
    color: var(--text-dark);
    transition: all 0.2s ease;
    display: flex;
    flex-direction: column;
    gap: 8px;
}

.landing-card:hover {
    transform: translateY(-4px);
    box-shadow: 0 10px 15px -3px rgba(0,0,0,0.05);
    border-color: var(--primary);
}

.landing-card h3 {
    font-size: 16px;
    font-weight: 700;
    color: var(--primary);
}

.landing-card p {
    font-size: 13.5px;
    color: var(--text-muted);
    margin-bottom: 0;
    text-align: left;
}

@media (max-width: 1024px) {
    .sidebar {
        display: none; /* simple hides sidebar for tablet/mobile to keep script clean */
    }
    .main-wrapper {
        margin-left: 0;
    }
    .content-container {
        padding: 24px;
        margin-top: 0;
        margin-bottom: 0;
        border-radius: 0;
    }
}
"""

def generate_sidebar(active_page: str) -> str:
    nav_html = []
    # Index/Readme link
    active_class = "active" if active_page == "README.md" else ""
    nav_html.append(f'        <a href="index.html" class="sidebar-nav-item {active_class}">🏡 Trang chủ / Tổng mục lục</a>')
    
    # Process regular pages
    for filename in DOCS_ORDER:
        if filename == "README.md":
            continue
        title = PAGE_TITLES.get(filename, filename)
        active_class = "active" if active_page == filename else ""
        html_file = filename.replace(".md", ".html")
        nav_html.append(f'        <a href="{html_file}" class="sidebar-nav-item {active_class}">{title}</a>')
        
    return "\n".join(nav_html)

def fix_links(html_content: str) -> str:
    # 1. Replace absolute file:///.../docs/XYZ.md with XYZ.html
    html_content = re.sub(
        r'href="file:///[^"]+/docs/([^"]+)\.md(#\S+)??"',
        r'href="\1.html\2"',
        html_content
    )
    
    # 2. Replace relative docs/XYZ.md or simply XYZ.md with XYZ.html
    # Matches href="00_project_overview.md"
    html_content = re.sub(
        r'href="([^"]+)\.md(#\S+)??"',
        r'href="\1.html\2"',
        html_content
    )
    
    # Also clean up index.html references specifically if it replaces README
    html_content = html_content.replace('href="README.html"', 'href="index.html"')
    
    return html_content

def format_alerts(html_content: str) -> str:
    alert_types = {
        'NOTE': {'class': 'alert-note', 'title': 'Lưu ý', 'icon': '📝'},
        'TIP': {'class': 'alert-tip', 'title': 'Gợi ý / Mẹo', 'icon': '💡'},
        'IMPORTANT': {'class': 'alert-important', 'title': 'Quan trọng', 'icon': '🚨'},
        'WARNING': {'class': 'alert-warning', 'title': 'Cảnh báo', 'icon': '⚠️'},
        'CAUTION': {'class': 'alert-caution', 'title': 'Cẩn trọng', 'icon': '🛑'}
    }
    
    for alert, info in alert_types.items():
        # Match blockquotes containing [!ALERT] followed by a line break and content
        pattern = rf'<blockquote>\s*<p>\s*\[!{alert}\]\s*<br\s*/?>\s*(.*?)</p>\s*</blockquote>'
        replacement = f'''<div class="alert {info['class']}">
            <div class="alert-title">{info['icon']} {info['title']}</div>
            <div class="alert-content"><p>\\1</p></div>
        </div>'''
        html_content = re.sub(pattern, replacement, html_content, flags=re.DOTALL | re.IGNORECASE)
        
        # Also match single-paragraph blockquotes without a <br>
        pattern_single = rf'<blockquote>\s*<p>\s*\[!{alert}\]\s*(.*?)</p>\s*</blockquote>'
        html_content = re.sub(pattern_single, replacement, html_content, flags=re.DOTALL | re.IGNORECASE)
        
    return html_content

def format_mermaid(html_content: str) -> str:
    def decode_entities(match):
        code = match.group(1)
        code = code.replace('&lt;', '<').replace('&gt;', '>').replace('&amp;', '&').replace('&quot;', '"')
        return f'<pre class="mermaid">{code}</pre>'
        
    pattern = r'<pre>\s*<code class="language-mermaid">(.*?)</code>\s*</pre>'
    html_content = re.sub(pattern, decode_entities, html_content, flags=re.DOTALL)
    return html_content

def build_full_html(page_title: str, body_content: str, active_page: str) -> str:
    sidebar_html = generate_sidebar(active_page)
    
    return f"""<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{page_title} - Lab 4 AIoT Energy Forecasting</title>
    <style>
        {CSS_STYLE}
    </style>
    <!-- Mermaid.js for drawing diagrams directly in the browser -->
    <script type="module">
        import mermaid from 'https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.esm.min.mjs';
        mermaid.initialize({{
            startOnLoad: true,
            theme: 'default',
            securityLevel: 'loose',
            flowchart: {{ useMaxWidth: true, htmlLabels: true }}
        }});
    </script>
    <!-- MathJax for rendering LaTeX math formulas -->
    <script src="https://polyfill.io/v3/polyfill.min.js?features=es6"></script>
    <script id="MathJax-script" async src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-mml-chtml.js"></script>
    <script>
    window.MathJax = {{
      tex: {{
        inlineMath: [['\\\\(', '\\\\)']],
        displayMath: [['\\\\[', '\\\\]'], ['$$', '$$']],
        processEscapes: true,
        processEnvironments: true
      }}
    }};
    </script>
</head>
<body>

    <!-- Left Sidebar Navigation -->
    <div class="sidebar">
        <div class="sidebar-header">
            <h1>🔋 Lab 4 AIoT</h1>
            <div class="badge">Energy Forecasting</div>
        </div>
        <div class="sidebar-nav">
            {sidebar_html}
        </div>
        <div class="sidebar-footer">
            Designed by DeepMind Team & Antigravity AI
        </div>
    </div>

    <!-- Main Content Area -->
    <div class="main-wrapper">
        <div class="top-bar">
            <div class="top-bar-title">Tài liệu Kỹ thuật Hệ thống Dự báo Phụ tải Điện năng BEMS</div>
            <div class="top-bar-links">
                <a href="index.html">🏡 Quay lại Trang chủ</a>
            </div>
        </div>

        <div style="padding: 0 40px; flex: 1;">
            <div class="content-container markdown-body">
                {body_content}
            </div>
        </div>

        <div class="footer">
            © 2026 - Lab 4 AIoT Forecasting & Predictive Analytics - Tài liệu Đào tạo Chuyên sâu
        </div>
    </div>

</body>
</html>
"""

def generate_landing_page(pages_info: list) -> str:
    # Generates the landing page (index.html) with a beautiful grid of all pages
    cards_html = []
    
    for filename, title, summary in pages_info:
        if filename == "README.md":
            continue
        html_file = filename.replace(".md", ".html")
        cards_html.append(f"""
        <a href="{html_file}" class="landing-card">
            <h3>{title}</h3>
            <p>{summary}</p>
        </a>
        """)
        
    grid_content = "\n".join(cards_html)
    
    landing_body = f"""
    <h1>🔋 HỆ THỐNG TÀI LIỆU KỸ THUẬT: LAB 4 FORECASTING</h1>
    <p style="font-size: 16px; margin-bottom: 24px;">Chào mừng các bạn đến với cổng thông tin tài liệu kỹ thuật toàn diện của dự án <strong>Lab 4: Dự báo và Phân tích Dự đoán Điện năng tiêu thụ (UCI Appliances Dataset)</strong>. Hệ thống tài liệu này được chuyển đổi tự động từ Markdown sang HTML di động, giúp tối ưu hóa việc nghiên cứu và học tập trực quan.</p>
    
    <h2>🗺️ Sơ đồ Lộ trình Học tập (14 Học phần)</h2>
    <div class="landing-grid">
        {grid_content}
    </div>
    
    <h2 style="margin-top: 40px;">🧪 Hướng dẫn chạy thử nghiệm nhanh</h2>
    <p>Để khởi chạy dự án và kiểm thử dịch vụ API dự báo phụ tải Wh của ngôi nhà:</p>
    <pre><code># 1. Tải và cài đặt các thư viện phụ thuộc
pip install -r requirements.txt

# 2. Tải tập dữ liệu thô UCI Appliances về máy
python src/download_data.py

# 3. Huấn luyện 5 mô hình và đóng gói model bundle tốt nhất
python src/train_forecast.py

# 4. Khởi chạy FastAPI Server serving cục bộ
uvicorn src.app:app --reload

# 5. Kiểm thử gọi API thời gian thực
python src/test_api_local.py</code></pre>
    """
    
    return landing_body

def main():
    print("=== BẮT ĐẦU CHUYỂN ĐỔI TÀI LIỆU SANG HTML ===")
    
    if not DOCS_DIR.exists():
        print(f"Lỗi: Không tìm thấy thư mục tài liệu '{DOCS_DIR}'")
        sys.exit(1)
        
    HTML_OUT_DIR.mkdir(exist_ok=True)
    
    # Initialize markdown converter with extensions
    # 'extra' includes tables and fenced code blocks
    # 'toc' yields TOC hooks if needed
    md_converter = markdown.Markdown(extensions=['extra', 'toc', 'tables', 'fenced_code'])
    
    pages_summary = {
        "00_project_overview.md": "Giới thiệu bài toán dự báo, bối cảnh smart home, và đối sánh bản chất với Lab 3 Anomaly Detection.",
        "01_architecture.md": "Kiến trúc 8 lớp của hệ thống AIoT, nơi AI sinh sống, ánh xạ BEMS tòa nhà và tích hợp ESP32/MQTT.",
        "02_data_flow.md": "Chi tiết luồng đi của dữ liệu thô qua 15 bước biến đổi thành kết quả API dự đoán Wh.",
        "03_runtime_and_dependencies.md": "Đồ thị dependency của hệ thống, luồng thực thi trong RAM và cẩm nang debug lỗi KeyError/NaN.",
        "04_dataset_and_schema.md": "Giải nghĩa 29 cảm biến trong dataset UCI và cơ chế phòng vệ điền khuyết thiếu 2 lớp an toàn.",
        "05_feature_engineering.md": "Cơ chế toán học đằng sau đặc trưng chuỗi thời gian: Lag, Rolling, Delta, Cyclic Sin/Cos và chống rò rỉ.",
        "06_model_training_and_metrics.md": "Tầm quan trọng của Baselines và ý nghĩa lưới điện vật lý của các sai số hồi quy MAE, RMSE, MAPE, Bias.",
        "07_decision_layer.md": "Tầng ra quyết định ánh xạ rủi ro Wh sang phân vị xác suất thống kê (70%/90%/97%) và log forecast.",
        "08_api_forecast_workflow.md": "Triển khai FastAPI online serving, Sequence Diagram, JSON payloads mẫu và tích hợp Dashboard.",
        "09_code_review.md": "Đánh giá chất lượng code theo chuẩn Senior (modularity, SoC) và sơ đồ tái cấu trúc mô-đun hóa.",
        "10_safety_fail_safe.md": "8 rủi ro hệ thống vật lý và giải pháp Edge Safety Gateway nhúng ESP32 bằng C++ Safe Interlock.",
        "11_development_roadmap.md": "Đường dẫn học tập phễu 4 giai đoạn cho học viên và lộ trình 3 cấp độ MLOps cho doanh nghiệp.",
        "HANDBOOK.md": "Cuốn sách hướng dẫn kỹ thuật (Handbook) tổng hợp đầy đủ từ thuật ngữ chuyên ngành đến FAQ & troubleshooting."
    }
    
    landing_pages_info = []
    
    for filename in DOCS_ORDER:
        filepath = DOCS_DIR / filename
        if not filepath.exists():
            print(f"Cảnh báo: Không tìm thấy file '{filename}' trong thư mục docs/. Bỏ qua...")
            continue
            
        print(f"Đang xử lý: {filename}...")
        
        # Read markdown content
        with open(filepath, "r", encoding="utf-8") as f:
            md_content = f.read()
            
        # Convert to HTML
        md_converter.reset()
        html_body = md_converter.convert(md_content)
        
        # Apply custom HTML styling & postprocessing
        html_body = fix_links(html_body)
        html_body = format_alerts(html_body)
        html_body = format_mermaid(html_body)
        
        # Get readable title
        page_title = PAGE_TITLES.get(filename, filename)
        
        # Render within HTML template
        full_html = build_full_html(page_title, html_body, filename)
        
        # Write to html_docs
        out_filename = filename.replace(".md", ".html")
        # If it's README.md, write to README.html too
        out_path = HTML_OUT_DIR / out_filename
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(full_html)
            
        if filename != "README.md":
            summary = pages_summary.get(filename, "Tài liệu đào tạo kỹ thuật chi tiết của dự án Lab 4.")
            landing_pages_info.append((filename, page_title, summary))
            
    # Generate the beautiful Landing Page (index.html)
    print("Đang tạo trang chủ: index.html...")
    landing_body_content = generate_landing_page(landing_pages_info)
    # Highlight README link in the sidebar since index.html serves as the portal
    full_landing_html = build_full_html("Trang chủ", landing_body_content, "README.md")
    
    with open(HTML_OUT_DIR / "index.html", "w", encoding="utf-8") as f:
        f.write(full_landing_html)
        
    print(f"=== CHUYỂN ĐỔI THÀNH CÔNG! ===")
    print(f"Tất cả file HTML đã được lưu trữ tại: {HTML_OUT_DIR.resolve()}")
    print("Vui lòng mở file 'html_docs/index.html' trên trình duyệt để thưởng thức.")

if __name__ == "__main__":
    main()
