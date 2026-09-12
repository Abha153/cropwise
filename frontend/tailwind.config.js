/** @type {import('tailwindcss').Config} */
export default {
  darkMode: 'class',
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#17372D",
        forest: {
          DEFAULT: "#103E32",
          light: "#2A6756",
          dark: "#0D2D27",
        },
        marigold: {
          DEFAULT: "#E5B96A",
          light: "#F2D08B",
          dark: "#C58B34",
        },
        clay: "#B76C4B",
        rain: "#3E6F7F",
        paper: "#FFFFFF",
        wheat: "#EDF6F0",
        mist: "#F4F7F4",
      },
      fontFamily: {
        display: ["'Space Grotesk'", "sans-serif"],
        body: ["'Inter'", "sans-serif"],
        mono: ["'IBM Plex Mono'", "monospace"],
      },
      boxShadow: {
        card: "0 10px 30px rgba(16, 62, 50, 0.08)",
        soft: "0 8px 24px rgba(11, 26, 22, 0.05)",
      },
      borderRadius: {
        xl: '1rem',
        '2xl': '1.5rem',
        '3xl': '2rem',
      },
    },
  },
  plugins: [],
}
