#!/usr/bin/env python3
import os
import re
import html
import json
from pathlib import Path
import markdown

SOURCE_DIR = Path(__file__).parent.parent / "docs"
TARGET_DIR = Path(__file__).parent.parent / "docs-site"
PAGES_DIR = TARGET_DIR / "pages"

# Grouping and sorting configurations for the sidebar
CORE_DOCS = [
    ("01_project_overview.md", "01. Tổng quan dự án"),
    ("02_architecture.md", "02. Kiến trúc hệ thống"),
    ("03_folder_structure.md", "03. Cấu trúc thư mục"),
    ("04_api_reference.md", "04. Tài liệu API"),
    ("05_model_pipeline.md", "05. Quy trình suy luận"),
    ("06_docker_deployment.md", "06. Triển khai Docker"),
    ("07_data_flow.md", "07. Luồng dữ liệu"),
]

GUIDE_DOCS = [
    ("lab5_study_guide.md", "Cẩm nang nghiên cứu Lab 5"),
    ("HUONG_DAN_CHAY_VA_QUAN_SAT.md", "Hướng dẫn chạy & Quan sát"),
    ("DUONG_DI_MODEL_TRONG_THUC_TE.md", "Đường đi của model"),
    ("model_formats_for_students.md", "Định dạng model AI"),
    ("docker_environment_comparison.md", "So sánh môi trường Docker"),
    ("docker_desktop_gui_beginner.md", "Docker Desktop cho người mới"),
    ("docker_ubuntu_engine_beginner.md", "Docker Engine trên Ubuntu"),
    ("submission_checklist_v4.md", "Checklist nộp bài"),
    ("taste_skill.md", "Quy chuẩn thiết kế Taste Skill"),
]

def make_sidebar(current_filename: str, depth=0) -> str:
    prefix = "" if depth == 0 else "../"
    html_lines = []
    
    html_lines.append('<div class="sidebar-section">')
    html_lines.append('  <h4 class="sidebar-title">Core Documentation</h4>')
    html_lines.append('  <ul class="sidebar-list">')
    for file, title in CORE_DOCS:
        link = f"{prefix}pages/{file.replace('.md', '.html')}"
        if file == "01_project_overview.md" and current_filename == "index.html":
            link = f"pages/{file.replace('.md', '.html')}"
        elif current_filename == file:
            link = "#"
        active = 'active' if current_filename == file or (file == "01_project_overview.md" and current_filename == "index.html") else ''
        html_lines.append(f'    <li><a href="{link}" class="sidebar-link {active}">{title}</a></li>')
    html_lines.append('  </ul>')
    html_lines.append('</div>')

    html_lines.append('<div class="sidebar-section">')
    html_lines.append('  <h4 class="sidebar-title">References & Guides</h4>')
    html_lines.append('  <ul class="sidebar-list">')
    for file, title in GUIDE_DOCS:
        link = f"{prefix}pages/{file.replace('.md', '.html')}"
        if current_filename == file:
            link = "#"
        active = 'active' if current_filename == file else ''
        html_lines.append(f'    <li><a href="{link}" class="sidebar-link {active}">{title}</a></li>')
    html_lines.append('  </ul>')
    html_lines.append('</div>')

    return "\n".join(html_lines)

def convert_mermaid(html_content: str) -> str:
    # Convert <pre><code class="language-mermaid">...</code></pre> to <pre class="mermaid">...</pre> for Mermaid.js
    pattern = re.compile(r'<pre><code class="language-mermaid">(.*?)</code></pre>', re.DOTALL)
    def replace_mermaid(match):
        code_content = match.group(1)
        decoded = html.unescape(code_content)
        return f'<pre class="mermaid">{decoded}</pre>'
    
    html_content = pattern.sub(replace_mermaid, html_content)
    
    pattern2 = re.compile(r'<pre><code class="mermaid">(.*?)</code></pre>', re.DOTALL)
    html_content = pattern2.sub(replace_mermaid, html_content)
    return html_content

def rewrite_html_links(html_content: str, current_filename: str, depth: int) -> str:
    # Regex to match href="..."
    href_pattern = re.compile(r'href="([^"]+)"')
    
    def replace_href(match):
        url = match.group(1)
        
        # If it's a file:/// link pointing to our project docs or code
        project_folder_match = re.search(r'lab5_dockerized_multimodel_aiot_inference_service_v4/(.*)', url)
        if project_folder_match:
            subpath = project_folder_match.group(1)
            # E.g., docs/model_formats_for_students.md or app/templates/classify-image-demo.html
            if subpath.startswith("docs/"):
                doc_name = subpath.replace("docs/", "")
                doc_html = doc_name.replace(".md", ".html")
                if depth == 0:
                    return f'href="pages/{doc_html}"'
                else:
                    return f'href="{doc_html}"'
            else:
                root_relative_prefix = "../" if depth == 0 else "../../"
                return f'href="{root_relative_prefix}{subpath}"'
        
        # If it's a relative link ending with .md (e.g. model_formats_for_students.md or ./model_formats_for_students.md)
        if url.endswith(".md") and not url.startswith("http") and not url.startswith("file:"):
            clean_url = url.lstrip("./")
            doc_name = os.path.basename(clean_url)
            doc_html = doc_name.replace(".md", ".html")
            if depth == 0:
                return f'href="pages/{doc_html}"'
            else:
                return f'href="{doc_html}"'
                
        return match.group(0)
    
    return href_pattern.sub(replace_href, html_content)

def build_template(title: str, content: str, sidebar_html: str, depth=0) -> str:
    prefix = "" if depth == 0 else "../"
    
    return f"""<!DOCTYPE html>
<html lang="vi" data-theme="dark">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{title} - AIoT Documentation</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700&display=swap" rel="stylesheet">
  <link rel="stylesheet" href="{prefix}css/style.css">
  <!-- Highlight.js Theme -->
  <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.8.0/styles/github-dark.min.css" id="hljs-theme">
  <script src="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.8.0/highlight.min.js"></script>
</head>
<body>
  <div class="app-layout">
    <!-- Top Header -->
    <header class="top-nav">
      <div class="top-nav-left">
        <button class="mobile-menu-toggle" id="menuToggle">
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 12h18M3 6h18M3 18h18"/></svg>
        </button>
        <span class="logo">⚡ AIoT Docs</span>
      </div>
      <div class="top-nav-right">
        <div class="search-container">
          <input type="text" id="searchInput" placeholder="Tìm kiếm tài liệu... (/)">
          <div class="search-results" id="searchResults"></div>
        </div>
        <button class="theme-toggle" id="themeToggle" title="Đổi giao diện">
          <svg class="sun-icon" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="5"/><path d="M12 1v2M12 21v2M4.22 4.22l1.42 1.42M18.36 18.36l1.42 1.42M1 12h2M21 12h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42"/></svg>
          <svg class="moon-icon" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="display:none;"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/></svg>
        </button>
      </div>
    </header>

    <div class="main-layout">
      <!-- Sidebar Navigation -->
      <aside class="sidebar" id="sidebar">
        {sidebar_html}
      </aside>
      <div class="sidebar-overlay" id="sidebarOverlay"></div>

      <!-- Main Content Area -->
      <main class="content-area">
        <div class="content-container">
          <article class="markdown-body">
            {content}
          </article>
        </div>
      </main>

      <!-- Right Table of Contents Panel -->
      <aside class="toc-panel" id="tocPanel"></aside>
    </div>
  </div>

  <script src="{prefix}js/search_index.js"></script>
  <script src="{prefix}js/main.js"></script>
  <!-- Mermaid.js for Diagrams -->
  <script type="module">
    import mermaid from 'https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.esm.min.mjs';
    mermaid.initialize({{ 
      startOnLoad: true, 
      theme: document.documentElement.getAttribute('data-theme') === 'dark' ? 'dark' : 'default',
      securityLevel: 'loose'
    }});
  </script>
</body>
</html>
"""

def main():
    TARGET_DIR.mkdir(parents=True, exist_ok=True)
    PAGES_DIR.mkdir(parents=True, exist_ok=True)
    (TARGET_DIR / "css").mkdir(parents=True, exist_ok=True)
    (TARGET_DIR / "js").mkdir(parents=True, exist_ok=True)
    
    print("Generating assets...")
    
    # 1. Write CSS file
    css_content = """
:root[data-theme="dark"] {
  --bg-base: #0b0f19;
  --bg-sidebar: #0f172a;
  --bg-nav: rgba(15, 23, 42, 0.8);
  --border-color: rgba(255, 255, 255, 0.08);
  --text-primary: #f3f4f6;
  --text-secondary: #9ca3af;
  --text-muted: #4b5563;
  --accent-color: #38bdf8;
  --accent-hover: #0ea5e9;
  --card-bg: rgba(30, 41, 59, 0.5);
  --code-bg: #020617;
  --pre-bg: #030712;
  --table-header-bg: rgba(15, 23, 42, 0.6);
  --highlight-bg: rgba(56, 189, 248, 0.1);
  --scrollbar-thumb: #1e293b;
}

:root[data-theme="light"] {
  --bg-base: #f8fafc;
  --bg-sidebar: #ffffff;
  --bg-nav: rgba(255, 255, 255, 0.8);
  --border-color: rgba(0, 0, 0, 0.08);
  --text-primary: #0f172a;
  --text-secondary: #334155;
  --text-muted: #64748b;
  --accent-color: #0284c7;
  --accent-hover: #0369a1;
  --card-bg: #f1f5f9;
  --code-bg: #e2e8f0;
  --pre-bg: #f8fafc;
  --table-header-bg: #e2e8f0;
  --highlight-bg: rgba(2, 132, 199, 0.1);
  --scrollbar-thumb: #cbd5e1;
}

* {
  box-sizing: border-box;
  margin: 0;
  padding: 0;
}

body {
  font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  background-color: var(--bg-base);
  color: var(--text-primary);
  min-height: 100vh;
  line-height: 1.6;
  transition: background-color 0.3s, color 0.3s;
}

/* Scrollbars */
::-webkit-scrollbar {
  width: 8px;
  height: 8px;
}
::-webkit-scrollbar-track {
  background: transparent;
}
::-webkit-scrollbar-thumb {
  background: var(--scrollbar-thumb);
  border-radius: 4px;
}

/* App Layout */
.app-layout {
  display: flex;
  flex-direction: column;
  height: 100vh;
  overflow: hidden;
}

/* Top Navigation */
.top-nav {
  height: 64px;
  background-color: var(--bg-nav);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  border-bottom: 1px solid var(--border-color);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
  position: relative;
  z-index: 100;
}

.top-nav-left {
  display: flex;
  align-items: center;
  gap: 16px;
}

.logo {
  font-size: 1.25rem;
  font-weight: 700;
  letter-spacing: -0.02em;
  color: var(--text-primary);
}

.mobile-menu-toggle {
  background: none;
  border: none;
  color: var(--text-primary);
  cursor: pointer;
  display: none;
}

.top-nav-right {
  display: flex;
  align-items: center;
  gap: 20px;
}

/* Search Box */
.search-container {
  position: relative;
  width: 260px;
}

.search-container input {
  width: 100%;
  padding: 8px 16px;
  border-radius: 9999px;
  background: var(--card-bg);
  border: 1px solid var(--border-color);
  color: var(--text-primary);
  font-size: 0.875rem;
  outline: none;
  transition: border-color 0.2s, box-shadow 0.2s;
}

.search-container input:focus {
  border-color: var(--accent-color);
  box-shadow: 0 0 0 3px var(--highlight-bg);
}

.search-results {
  position: absolute;
  top: 42px;
  right: 0;
  width: 320px;
  background: var(--bg-sidebar);
  border: 1px solid var(--border-color);
  border-radius: 12px;
  box-shadow: 0 10px 25px rgba(0, 0, 0, 0.2);
  max-height: 300px;
  overflow-y: auto;
  display: none;
  z-index: 200;
}

.search-result-item {
  padding: 10px 16px;
  cursor: pointer;
  border-bottom: 1px solid var(--border-color);
  transition: background 0.2s;
  display: block;
  text-decoration: none;
}

.search-result-item:hover {
  background: var(--card-bg);
}

.search-result-title {
  font-size: 0.9rem;
  font-weight: 600;
  color: var(--accent-color);
}

.search-result-snippet {
  font-size: 0.75rem;
  color: var(--text-secondary);
  margin-top: 4px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

/* Theme Toggle */
.theme-toggle {
  background: none;
  border: none;
  color: var(--text-primary);
  cursor: pointer;
  padding: 6px;
  border-radius: 8px;
  transition: background 0.2s;
}

.theme-toggle:hover {
  background: var(--card-bg);
}

/* Main Layout */
.main-layout {
  display: flex;
  flex: 1;
  overflow: hidden;
  position: relative;
}

/* Sidebar */
.sidebar {
  width: 280px;
  background-color: var(--bg-sidebar);
  border-right: 1px solid var(--border-color);
  padding: 24px 16px;
  overflow-y: auto;
  flex-shrink: 0;
  transition: transform 0.3s ease;
}

.sidebar-section {
  margin-bottom: 24px;
}

.sidebar-title {
  font-size: 0.75rem;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: var(--text-muted);
  margin-bottom: 12px;
  padding-left: 12px;
  font-weight: 700;
}

.sidebar-list {
  list-style: none;
}

.sidebar-link {
  display: block;
  padding: 8px 12px;
  border-radius: 8px;
  color: var(--text-secondary);
  text-decoration: none;
  font-size: 0.9rem;
  font-weight: 500;
  transition: all 0.2s;
}

.sidebar-link:hover {
  color: var(--text-primary);
  background-color: var(--card-bg);
}

.sidebar-link.active {
  color: var(--accent-color);
  background-color: var(--highlight-bg);
  font-weight: 600;
}

/* Content Area */
.content-area {
  flex: 1;
  overflow-y: auto;
  padding: 40px 48px;
  display: flex;
  justify-content: center;
}

.content-container {
  max-width: 860px;
  width: 100%;
}

/* Right Table of Contents Panel */
.toc-panel {
  width: 240px;
  flex-shrink: 0;
  padding: 40px 24px 40px 16px;
  overflow-y: auto;
  border-left: 1px solid var(--border-color);
}

.toc-title {
  font-size: 0.75rem;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: var(--text-muted);
  font-weight: 700;
  margin-bottom: 12px;
}

.toc-list {
  list-style: none;
  padding-left: 0;
}

.toc-item {
  margin-bottom: 8px;
  line-height: 1.4;
}

.toc-h2 {
  padding-left: 0;
  font-size: 0.85rem;
}

.toc-h3 {
  padding-left: 12px;
  font-size: 0.8rem;
}

.toc-link {
  color: var(--text-secondary);
  text-decoration: none;
  transition: color 0.2s;
  display: inline-block;
}

.toc-link:hover {
  color: var(--accent-color);
}

/* Markdown Styling (Modern documentation-style typography) */
.markdown-body {
  max-width: 100%;
}

.markdown-body h1 {
  font-size: 2.25rem;
  font-weight: 700;
  margin-bottom: 24px;
  letter-spacing: -0.03em;
  border-bottom: 1px solid var(--border-color);
  padding-bottom: 12px;
}

.markdown-body h2 {
  font-size: 1.5rem;
  font-weight: 600;
  margin-top: 36px;
  margin-bottom: 16px;
  letter-spacing: -0.02em;
  border-bottom: 1px solid var(--border-color);
  padding-bottom: 8px;
}

.markdown-body h3 {
  font-size: 1.25rem;
  font-weight: 600;
  margin-top: 24px;
  margin-bottom: 12px;
}

.markdown-body p {
  margin-bottom: 16px;
  color: var(--text-secondary);
  font-size: 1rem;
}

.markdown-body ul, .markdown-body ol {
  margin-bottom: 16px;
  padding-left: 24px;
  color: var(--text-secondary);
}

.markdown-body li {
  margin-bottom: 8px;
}

.markdown-body a {
  color: var(--accent-color);
  text-decoration: none;
}

.markdown-body a:hover {
  text-decoration: underline;
}

.markdown-body table {
  width: 100%;
  border-collapse: collapse;
  margin-bottom: 24px;
  font-size: 0.9rem;
}

.markdown-body th, .markdown-body td {
  border: 1px solid var(--border-color);
  padding: 10px 14px;
  text-align: left;
}

.markdown-body th {
  background-color: var(--table-header-bg);
  font-weight: 600;
}

.markdown-body tr:hover td {
  background-color: var(--table-header-bg);
}

/* Code wrapper and copy button */
.code-wrapper {
  position: relative;
  margin-bottom: 20px;
}

.code-wrapper pre {
  margin-bottom: 0 !important;
}

.copy-button {
  position: absolute;
  top: 10px;
  right: 10px;
  background: rgba(15, 23, 42, 0.6);
  border: 1px solid var(--border-color);
  border-radius: 6px;
  color: var(--text-secondary);
  padding: 4px 8px;
  font-size: 0.75rem;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 4px;
  opacity: 0;
  transition: opacity 0.2s, background 0.2s, color 0.2s;
  font-family: inherit;
  z-index: 10;
}

.code-wrapper:hover .copy-button {
  opacity: 1;
}

.copy-button:hover {
  background: rgba(15, 23, 42, 0.9);
  color: var(--text-primary);
}

.copy-button.copied {
  border-color: #22c55e;
  color: #22c55e;
  background: rgba(34, 197, 94, 0.1);
}

/* Code block styling */
.markdown-body pre {
  background-color: var(--pre-bg);
  border: 1px solid var(--border-color);
  border-radius: 12px;
  padding: 16px;
  overflow-x: auto;
}

.markdown-body code {
  font-family: Menlo, Monaco, Consolas, "Courier New", monospace;
  font-size: 0.85rem;
  background-color: var(--code-bg);
  padding: 3px 6px;
  border-radius: 6px;
}

.markdown-body pre code {
  background-color: transparent;
  padding: 0;
  border-radius: 0;
  font-size: 0.85rem;
}

/* Alert styles (GitHub-style) */
.markdown-body blockquote {
  padding: 16px;
  border-left: 4px solid var(--border-color);
  background: var(--card-bg);
  border-radius: 0 12px 12px 0;
  margin-bottom: 20px;
}

.markdown-body blockquote p {
  margin-bottom: 0;
}

/* Custom Mermaid containers */
.mermaid {
  background: var(--pre-bg) !important;
  border: 1px solid var(--border-color);
  border-radius: 12px;
  padding: 20px;
  margin-bottom: 24px;
  display: flex;
  justify-content: center;
}

/* Responsive CSS */
@media (max-width: 1200px) {
  .toc-panel {
    display: none;
  }
}

@media (max-width: 860px) {
  .mobile-menu-toggle {
    display: block;
  }
  
  .sidebar {
    position: absolute;
    top: 0;
    bottom: 0;
    left: 0;
    transform: translateX(-100%);
    z-index: 150;
  }
  
  .sidebar.open {
    transform: translateX(0);
  }
  
  .sidebar-overlay {
    position: absolute;
    top: 0;
    bottom: 0;
    left: 0;
    right: 0;
    background: rgba(0, 0, 0, 0.4);
    backdrop-filter: blur(4px);
    z-index: 140;
    display: none;
  }
  
  .sidebar-overlay.open {
    display: block;
  }
  
  .content-area {
    padding: 24px 16px;
  }
  
  .search-container {
    width: 160px;
  }
}
"""
    (TARGET_DIR / "css" / "style.css").write_text(css_content.strip(), encoding="utf-8")
    
    # 2. Write Javascript file
    js_content = """
document.addEventListener('DOMContentLoaded', () => {
  const themeToggle = document.getElementById('themeToggle');
  const sunIcon = themeToggle.querySelector('.sun-icon');
  const moonIcon = themeToggle.querySelector('.moon-icon');
  
  // Theme Toggle Logic
  const savedTheme = localStorage.getItem('theme') || 'dark';
  document.documentElement.setAttribute('data-theme', savedTheme);
  updateThemeIcons(savedTheme);

  themeToggle.addEventListener('click', () => {
    const currentTheme = document.documentElement.getAttribute('data-theme');
    const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
    document.documentElement.setAttribute('data-theme', newTheme);
    localStorage.setItem('theme', newTheme);
    updateThemeIcons(newTheme);
    
    // Reload only if there are mermaid diagrams on the page to redraw them natively
    if (document.querySelector('.mermaid')) {
      location.reload();
    }
  });

  function updateThemeIcons(theme) {
    const hljsTheme = document.getElementById('hljs-theme');
    if (theme === 'dark') {
      sunIcon.style.display = 'block';
      moonIcon.style.display = 'none';
      if (hljsTheme) hljsTheme.href = 'https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.8.0/styles/github-dark.min.css';
    } else {
      sunIcon.style.display = 'none';
      moonIcon.style.display = 'block';
      if (hljsTheme) hljsTheme.href = 'https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.8.0/styles/github.min.css';
    }
  }

  // Mobile Menu Toggle Logic
  const menuToggle = document.getElementById('menuToggle');
  const sidebar = document.getElementById('sidebar');
  const sidebarOverlay = document.getElementById('sidebarOverlay');

  if (menuToggle) {
    menuToggle.addEventListener('click', () => {
      sidebar.classList.toggle('open');
      sidebarOverlay.classList.toggle('open');
    });
  }

  if (sidebarOverlay) {
    sidebarOverlay.addEventListener('click', () => {
      sidebar.classList.remove('open');
      sidebarOverlay.classList.remove('open');
    });
  }

  // Generate Table of Contents (TOC) dynamically
  const article = document.querySelector('.markdown-body');
  const tocPanel = document.getElementById('tocPanel');
  
  if (article && tocPanel) {
    const headings = article.querySelectorAll('h2, h3');
    if (headings.length > 0) {
      const tocTitle = document.createElement('div');
      tocTitle.className = 'toc-title';
      tocTitle.textContent = 'Mục lục';
      tocPanel.appendChild(tocTitle);
      
      const tocList = document.createElement('ul');
      tocList.className = 'toc-list';
      
      headings.forEach((heading, idx) => {
        // Ensure heading has an ID
        if (!heading.id) {
          heading.id = 'heading-' + idx;
        }
        
        const li = document.createElement('li');
        li.className = 'toc-item ' + (heading.tagName === 'H3' ? 'toc-h3' : 'toc-h2');
        
        const a = document.createElement('a');
        a.href = '#' + heading.id;
        a.className = 'toc-link';
        a.textContent = heading.textContent;
        
        li.appendChild(a);
        tocList.appendChild(li);
      });
      
      tocPanel.appendChild(tocList);
    } else {
      tocPanel.style.display = 'none';
    }
  }

  // Add Copy to Clipboard Buttons to Code Blocks
  const codeBlocks = document.querySelectorAll('pre');
  codeBlocks.forEach((block) => {
    // If it's a mermaid block, skip copy button
    if (block.classList.contains('mermaid')) return;
    
    // Create wrapper
    const wrapper = document.createElement('div');
    wrapper.className = 'code-wrapper';
    block.parentNode.insertBefore(wrapper, block);
    wrapper.appendChild(block);
    
    // Create copy button
    const copyBtn = document.createElement('button');
    copyBtn.className = 'copy-button';
    copyBtn.innerHTML = `
      <svg class="copy-icon" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>
      <span class="copy-text">Copy</span>
    `;
    wrapper.appendChild(copyBtn);
    
    copyBtn.addEventListener('click', () => {
      const codeText = block.innerText;
      navigator.clipboard.writeText(codeText).then(() => {
        copyBtn.querySelector('.copy-text').textContent = 'Copied!';
        copyBtn.classList.add('copied');
        setTimeout(() => {
          copyBtn.querySelector('.copy-text').textContent = 'Copy';
          copyBtn.classList.remove('copied');
        }, 2000);
      });
    });
  });

  // Run Highlight.js
  if (typeof hljs !== 'undefined') {
    hljs.highlightAll();
  }

  // Local Search Index Logic (uses window.searchIndex loaded from js/search_index.js)
  const searchInput = document.getElementById('searchInput');
  const searchResults = document.getElementById('searchResults');
  
  const searchIndex = window.searchIndex || [];
  const isSubPage = window.location.pathname.includes('/pages/');

  if (searchInput) {
    // Shortcut '/' to focus search
    document.addEventListener('keydown', (e) => {
      if (e.key === '/' && document.activeElement !== searchInput) {
        e.preventDefault();
        searchInput.focus();
      }
    });

    searchInput.addEventListener('input', (e) => {
      const query = e.target.value.toLowerCase().trim();
      if (!query) {
        searchResults.style.display = 'none';
        return;
      }

      const matches = searchIndex.filter(item => 
        item.title.toLowerCase().includes(query) || 
        item.content.toLowerCase().includes(query)
      ).slice(0, 5);

      if (matches.length === 0) {
        searchResults.innerHTML = '<div style="padding:10px 16px;font-size:0.8rem;color:var(--text-muted);">Không tìm thấy kết quả.</div>';
      } else {
        searchResults.innerHTML = matches.map(item => {
          const relativeLink = isSubPage ? '../' + item.link : item.link;
          return `
            <a href="${relativeLink}" class="search-result-item">
              <div class="search-result-title">${item.title}</div>
              <div class="search-result-snippet">${item.snippet}...</div>
            </a>
          `;
        }).join('');
      }
      searchResults.style.display = 'block';
    });

    // Close search results clicking outside
    document.addEventListener('click', (e) => {
      if (!searchInput.contains(e.target) && !searchResults.contains(e.target)) {
        searchResults.style.display = 'none';
      }
    });
  }
});
"""
    (TARGET_DIR / "js" / "main.js").write_text(js_content.strip(), encoding="utf-8")

    # 3. Read and parse markdown files
    md_files = list(SOURCE_DIR.glob("*.md"))
    print(f"Found {len(md_files)} markdown files in {SOURCE_DIR}")
    
    # Store for search indexing
    search_data = []
    
    md_parser = markdown.Markdown(extensions=['tables', 'fenced_code', 'toc'])
    
    for md_path in md_files:
        filename = md_path.name
        content = md_path.read_text(encoding="utf-8")
        
        # Parse title from headers
        title_match = re.search(r'^#\s+(.*?)$', content, re.MULTILINE)
        title = title_match.group(1).strip() if title_match else filename.replace('.md', '').replace('_', ' ')
        
        # Clean markdown syntax for clean text indexing (search snippets)
        clean_text = re.sub(r'[#*`\[\]()-]', ' ', content)
        clean_text = re.sub(r'\s+', ' ', clean_text).strip()
        snippet = clean_text[:120]
        
        # Convert Markdown to HTML
        raw_html = md_parser.convert(content)
        # Apply Mermaid formatting conversion (decodes HTML entities)
        styled_html = convert_mermaid(raw_html)
        
        # Translate links inside the HTML content
        styled_html = rewrite_html_links(styled_html, filename, depth=1)
        
        sidebar_html = make_sidebar(filename, depth=1)
        html_page = build_template(title, styled_html, sidebar_html, depth=1)
        
        html_filename = filename.replace('.md', '.html')
        (PAGES_DIR / html_filename).write_text(html_page, encoding="utf-8")
        print(f"Compiled: {filename} -> pages/{html_filename}")
        
        # Append page data to search index
        search_data.append({
            "title": title,
            "link": f"pages/{html_filename}",
            "content": clean_text,
            "snippet": snippet
        })
        
        # If the file is 01_project_overview.md, create a replica as index.html at root
        if filename == "01_project_overview.md":
            sidebar_root = make_sidebar("index.html", depth=0)
            styled_html_root = convert_mermaid(raw_html)
            # Translate links for root file (depth=0)
            styled_html_root = rewrite_html_links(styled_html_root, "index.html", depth=0)
            
            index_page = build_template(title, styled_html_root, sidebar_root, depth=0)
            (TARGET_DIR / "index.html").write_text(index_page, encoding="utf-8")
            print("Generated: index.html (homepage)")

    # 4. Save search index json & javascript (for file:/// protocol CORS bypass)
    import json
    search_index_path = TARGET_DIR / "search_index.json"
    search_index_path.write_text(json.dumps(search_data, ensure_ascii=False, indent=2), encoding="utf-8")
    
    search_index_js_path = TARGET_DIR / "js" / "search_index.js"
    js_search_data = "window.searchIndex = " + json.dumps(search_data, ensure_ascii=False, indent=2) + ";"
    search_index_js_path.write_text(js_search_data, encoding="utf-8")
    
    print(f"Generated search index at: {search_index_path}")
    print(f"Generated search index JS at: {search_index_js_path}")
    print("Documentation build completed successfully!")

if __name__ == "__main__":
    main()
