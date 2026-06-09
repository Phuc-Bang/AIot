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
  });

  function updateThemeIcons(theme) {
    if (theme === 'dark') {
      sunIcon.style.display = 'block';
      moonIcon.style.display = 'none';
    } else {
      sunIcon.style.display = 'none';
      moonIcon.style.display = 'block';
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

  // Simple Search Index Logic
  const searchInput = document.getElementById('searchInput');
  const searchResults = document.getElementById('searchResults');
  
  // Fetch site pages data dynamically for search
  const isSubPage = window.location.pathname.includes('/pages/');
  const searchIndexPath = isSubPage ? '../search_index.json' : 'search_index.json';
  
  let searchIndex = [];
  fetch(searchIndexPath)
    .then(res => res.json())
    .then(data => { searchIndex = data; })
    .catch(err => console.error('Failed to load search index:', err));

  if (searchInput) {
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