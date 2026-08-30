/** @type {import('tailwindcss').Config} */
export default {
  darkMode: 'class',
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#12261F",
        forest: {
          DEFAULT: "#1F4D3D",
          light: "#2C6B54",
          dark: "#12261F",
        },
        marigold: {
          DEFAULT: "#F2A93B",
          light: "#F7C46E",
          dark: "#D98E1F",
        },
        clay: "#A65B3F",
        rain: "#3B6E8C",
        paper: "#F7F3EA",
        wheat: "#EFE3C3",
      },
      fontFamily: {
        display: ["'Space Grotesk'", "sans-serif"],
        body: ["'Inter'", "sans-serif"],
        mono: ["'IBM Plex Mono'", "monospace"],
      },
      boxShadow: {
        card: "0 2px 14px rgba(18, 38, 31, 0.08)",
      },
    },
  },
  plugins: [],
}
