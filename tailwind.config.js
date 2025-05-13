/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./templates/**/*.html",
    "./accounts/templates/**/*.html",
    "./journal/templates/**/*.html",
  ],
  theme: {
    extend: {
      colors: {
        // New Palette
        "primary-light": "#3B82F6", // Main blue for light mode (e.g., buttons)
        "primary-dark": "#60A5FA", // Main blue for dark mode or hover
        "secondary-light": "#10B981", // Green or teal for light mode
        "secondary-dark": "#34D399", // Green or teal for dark mode or hover
        "accent-light": "#F59E0B", // Orange or gold for emphasis
        "accent-dark": "#FBBF24", // Orange or gold for dark mode or hover

        "background-light": "#F9FAFB", // Very light background for light mode
        "text-light": "#1F2937", // Dark text for light mode

        "background-dark": "#111827", // Very dark background for dark mode
        "text-dark": "#E5E7EB", // Light text for dark mode

        "card-light": "#FFFFFF", // Card color in light mode
        "card-dark": "#1F2937", // Card color in dark mode

        "border-light": "#D1D5DB", // Border color in light mode
        "border-dark": "#374151", // Border color in dark mode

        // Previous colors that might still be used or for gradients
        "light-blue-start": "#3a8dff",
        "light-blue-end": "#4fa8ff",
        "blue-purple": "#9b5de5", // We might replace this with new colors
        "pink-purple": "#ec4899", // We might replace this with new colors
        "button-blue": "#3B82F6", // Aligned with primary-light
        "button-red": "#ef4444",
        "welcome-bg": "#F9FAFB", // Aligned with background-light
        "dark-purple": "#111827", // Aligned with background-dark
      },
      backgroundImage: {
        // New gradient for Hero Section
        "gradient-hero-light": "linear-gradient(135deg, #60A5FA, #34D399)", // Blue to green/teal
        "gradient-hero-dark": "linear-gradient(135deg, #3B82F6, #10B981)", // Darker version of the gradient
      },
      fontFamily: {
        sans: ["Inter", "sans-serif"], // Inter font you were using is good
      },
      boxShadow: {
        "custom-light":
          "0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05)",
        "custom-dark":
          "0 10px 15px -3px rgba(0, 0, 0, 0.3), 0 4px 6px -2px rgba(0, 0, 0, 0.15)",
      },
    },
  },
  plugins: [],
  darkMode: "class", // Enables class-based dark mode (e.g., <html class="dark">)
};
