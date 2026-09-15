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
        // Design-system extension (redesign pass): a warm earth-neutral
        // scale for premium editorial surfaces that shouldn't read as
        // "green dashboard" -- used for hero backgrounds, section dividers
        // and quiet secondary surfaces. Additive only; nothing above this
        // point changed, so every existing className keeps working.
        sand: {
          50: "#FBF8F2",
          100: "#F5EFE2",
          200: "#EBE1CC",
          300: "#DCCBA8",
        },
        charcoal: {
          DEFAULT: "#23281F",
          light: "#3A4234",
        },
      },
      fontFamily: {
        display: ["'Space Grotesk'", "sans-serif"],
        body: ["'Inter'", "sans-serif"],
        mono: ["'IBM Plex Mono'", "monospace"],
      },
      boxShadow: {
        card: "0 10px 30px rgba(16, 62, 50, 0.08)",
        soft: "0 8px 24px rgba(11, 26, 22, 0.05)",
        // Elevation scale extension -- "lifted" for hero/flagship panels,
        // "premium" for the rare, single most important element on a page.
        lifted: "0 20px 45px rgba(13, 45, 39, 0.14)",
        premium: "0 30px 70px -12px rgba(13, 45, 39, 0.28)",
      },
      borderRadius: {
        xl: '1rem',
        '2xl': '1.5rem',
        '3xl': '2rem',
        '4xl': '2.5rem',
      },
    },
  },
  plugins: [],
}
