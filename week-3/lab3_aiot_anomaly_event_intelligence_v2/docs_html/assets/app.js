(function () {
  const doc = document.documentElement;
  const storedTheme = localStorage.getItem("lab3-docs-theme");
  const prefersDark = window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches;
  doc.dataset.theme = storedTheme || (prefersDark ? "dark" : "light");

  function updateThemeButton() {
    const button = document.querySelector("[data-theme-toggle]");
    if (!button) return;
    button.textContent = doc.dataset.theme === "dark" ? "Light mode" : "Dark mode";
  }

  function highlightCurrentNav() {
    const current = window.location.pathname.split("/").pop() || "index.html";
    document.querySelectorAll(".nav-link").forEach((link) => {
      const target = link.getAttribute("href");
      if (target === current) {
        link.classList.add("active");
        link.setAttribute("aria-current", "page");
      }
    });
  }

  function setupThemeToggle() {
    const button = document.querySelector("[data-theme-toggle]");
    if (!button) return;
    button.addEventListener("click", () => {
      doc.dataset.theme = doc.dataset.theme === "dark" ? "light" : "dark";
      localStorage.setItem("lab3-docs-theme", doc.dataset.theme);
      updateThemeButton();
    });
    updateThemeButton();
  }

  function setupMobileNav() {
    const button = document.querySelector("[data-nav-toggle]");
    if (!button) return;
    button.addEventListener("click", () => {
      document.body.classList.toggle("nav-open");
    });

    document.querySelectorAll(".nav-link").forEach((link) => {
      link.addEventListener("click", () => document.body.classList.remove("nav-open"));
    });
  }

  function setupCopyButtons() {
    document.querySelectorAll("pre").forEach((pre) => {
      if (pre.classList.contains("no-copy")) return;
      const code = pre.querySelector("code");
      if (!code) return;

      const button = document.createElement("button");
      button.className = "copy-btn";
      button.type = "button";
      button.textContent = "Copy";
      button.addEventListener("click", async () => {
        try {
          if (navigator.clipboard && window.isSecureContext) {
            await navigator.clipboard.writeText(code.innerText);
          } else {
            const textarea = document.createElement("textarea");
            textarea.value = code.innerText;
            textarea.setAttribute("readonly", "");
            textarea.style.position = "fixed";
            textarea.style.opacity = "0";
            document.body.appendChild(textarea);
            textarea.select();
            document.execCommand("copy");
            textarea.remove();
          }
          button.textContent = "Copied";
          window.setTimeout(() => (button.textContent = "Copy"), 1400);
        } catch (error) {
          button.textContent = "Failed";
          window.setTimeout(() => (button.textContent = "Copy"), 1400);
        }
      });
      pre.appendChild(button);
    });
  }

  document.addEventListener("DOMContentLoaded", () => {
    highlightCurrentNav();
    setupThemeToggle();
    setupMobileNav();
    setupCopyButtons();
  });
})();
