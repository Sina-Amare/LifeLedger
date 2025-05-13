// Wait for DOM to load
document.addEventListener("DOMContentLoaded", () => {
  const themeToggle = document.getElementById("theme-toggle");
  const themeToggleIcon = themeToggle.querySelector("i"); // To access the <i> tag
  const html = document.documentElement;

  // Function to update icon based on theme
  const updateIcon = (theme) => {
    if (theme === "dark") {
      themeToggleIcon.classList.remove("fa-sun");
      themeToggleIcon.classList.add("fa-moon");
    } else {
      themeToggleIcon.classList.remove("fa-moon");
      themeToggleIcon.classList.add("fa-sun");
    }
  };

  // Check for saved theme or default to light
  let currentTheme = localStorage.getItem("theme");
  if (!currentTheme) {
    // If no saved theme, use user's OS preference (optional)
    // Otherwise, default to light
    if (
      window.matchMedia &&
      window.matchMedia("(prefers-color-scheme: dark)").matches
    ) {
      currentTheme = "dark";
    } else {
      currentTheme = "light";
    }
  }

  html.classList.add(currentTheme);
  updateIcon(currentTheme); // Set the initial icon

  themeToggle.addEventListener("click", () => {
    if (html.classList.contains("dark")) {
      html.classList.remove("dark");
      html.classList.add("light"); // Ensure 'light' class is present
      localStorage.setItem("theme", "light");
      updateIcon("light");
    } else {
      html.classList.remove("light"); // Ensure 'light' class is removed
      html.classList.add("dark");
      localStorage.setItem("theme", "dark");
      updateIcon("dark");
    }
  });

  // Listen for changes in OS theme preference (optional)
  window
    .matchMedia("(prefers-color-scheme: dark)")
    .addEventListener("change", (event) => {
      const newColorScheme = event.matches ? "dark" : "light";
      // Only update if the user hasn't manually set a theme
      if (localStorage.getItem("theme") === null) {
        html.classList.remove("dark", "light");
        html.classList.add(newColorScheme);
        updateIcon(newColorScheme);
      }
    });
});
