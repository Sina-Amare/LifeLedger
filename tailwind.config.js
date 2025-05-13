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
        "light-bg": "#f5f7fa",
        "dark-bg": "#1e1e2f",
        "accent-blue": "#38bdf8",
        "accent-purple": "#7c3aed",
        "accent-pink": "#ec4899",
        "accent-green": "#22c55e",
        "muted-gray": "#6b7280",
        "primary-text": "#111827",
        "dark-text": "#e5e7eb",
      },
      backgroundImage: {
        "gradient-hero": "linear-gradient(120deg, #38bdf8 0%, #7c3aed 100%)",
        "pattern-dots":
          "radial-gradient(circle at 1px 1px, #d1d5db 1px, transparent 0)",
      },
      fontFamily: {
        sans: ["Inter", "ui-sans-serif", "system-ui"],
      },
    },
  },
  plugins: [],
  darkMode: "class",
};
