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