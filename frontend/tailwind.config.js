/** @type {import('tailwindcss').Config} */
export default {
  darkMode: "class",
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        risk: {
          low: "#16a34a",
          medium: "#d97706",
          high: "#dc2626",
          critical: "#991b1b",
        },
        primary: {
          50: "#f4f7f0",
          100: "#e7eee1",
          200: "#d1dfcc",
          300: "#bfdc75",
          400: "#b5d94e",
          500: "#75a94f",
          600: "#1f5544",
          700: "#194638",
          800: "#143a30",
          900: "#102f27",
        },
      },
      fontFamily: {
        sans: ["'Plus Jakarta Sans'", "ui-sans-serif", "system-ui", "-apple-system", "sans-serif"],
        display: ["'Poppins'", "'Plus Jakarta Sans'", "ui-sans-serif", "sans-serif"],
      },
      boxShadow: {
        card: "0 2px 10px 0 rgba(31, 85, 68, 0.06)",
        soft: "0 8px 24px -6px rgba(31, 85, 68, 0.18)",
      },
      borderRadius: {
        "2xl": "1rem",
        "3xl": "1.5rem",
      },
    },
  },
  plugins: [],
};
