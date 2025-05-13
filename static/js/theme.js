// Wait for the DOM to load
document.addEventListener("DOMContentLoaded", () => {
  // Get the theme toggle button and its icon
  const themeToggle = document.getElementById("theme-toggle");
  const themeToggleIcon = themeToggle.querySelector("i"); // Access the <i> tag
  // Get the root HTML element to apply theme classes
  const html = document.documentElement;

  // Function to update the theme icon based on the current theme
  const updateIcon = (theme) => {
    if (theme === "dark") {
      themeToggleIcon.classList.remove("fa-sun");
      themeToggleIcon.classList.add("fa-moon");
    } else {
      themeToggleIcon.classList.remove("fa-moon");
      themeToggleIcon.classList.add("fa-sun");
    }
  };

  // Check for a saved theme in local storage, default to light if none found
  let currentTheme = localStorage.getItem("theme");
  if (!currentTheme) {
    // If no saved theme, check user's OS preference (optional)
    // Otherwise, default to light theme
    if (
      window.matchMedia &&
      window.matchMedia("(prefers-color-scheme: dark)").matches
    ) {
      currentTheme = "dark";
    } else {
      currentTheme = "light";
    }
  }

  // Apply the determined theme class to the HTML element
  html.classList.add(currentTheme);
  // Set the initial icon based on the applied theme
  updateIcon(currentTheme);

  // Add event listener to the theme toggle button
  themeToggle.addEventListener("click", () => {
    // Toggle theme: if currently dark, switch to light; otherwise, switch to dark
    if (html.classList.contains("dark")) {
      // Switch to light theme
      html.classList.remove("dark");
      html.classList.add("light"); // Ensure 'light' class is present
      // Save the light theme preference to local storage
      localStorage.setItem("theme", "light");
      // Update the icon to reflect the light theme
      updateIcon("light");
    } else {
      // Switch to dark theme
      html.classList.remove("light"); // Ensure 'light' class is removed
      html.classList.add("dark");
      // Save the dark theme preference to local storage
      localStorage.setItem("theme", "dark");
      // Update the icon to reflect the dark theme
      updateIcon("dark");
    }
  });

  // Listen for changes in the user's OS theme preference (optional)
  // This allows the theme to sync with OS settings if no manual theme is set
  window
    .matchMedia("(prefers-color-scheme: dark)")
    .addEventListener("change", (event) => {
      const newColorScheme = event.matches ? "dark" : "light";
      // Only update the theme if the user hasn't manually set a theme
      // This prevents OS changes from overriding a user's explicit choice
      if (localStorage.getItem("theme") === null) {
        html.classList.remove("dark", "light"); // Remove existing theme classes
        html.classList.add(newColorScheme); // Apply the new OS theme class
        updateIcon(newColorScheme); // Update the icon
      }
    });
});
