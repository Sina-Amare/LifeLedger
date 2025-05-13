document.addEventListener("DOMContentLoaded", () => {
  const themeToggle = document.getElementById("theme-toggle");
  const html = document.documentElement;
  const savedTheme = localStorage.getItem("theme") || "light";
  html.classList.add(savedTheme);
  themeToggle.innerHTML = savedTheme === "dark" ? "🌙" : "☀️";

  themeToggle.addEventListener("click", () => {
    const isDark = html.classList.contains("dark");
    html.classList.toggle("dark", !isDark);
    localStorage.setItem("theme", isDark ? "light" : "dark");
    themeToggle.innerHTML = isDark ? "☀️" : "🌙";
  });
});
