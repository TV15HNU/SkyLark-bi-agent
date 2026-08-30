/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        background: "#0d1117",
        panel: "#12161c",
        card: "#161b22",
        "card-hover": "#1c2128",
        border: "#21262d",
        "border-muted": "#30363d",
        accent: {
          sky: "#38bdf8",
          "sky-dark": "#0284c7",
          amber: "#f59e0b",
          emerald: "#10b981",
          rose: "#f43f5e",
        },
        text: {
          primary: "#e6edf3",
          secondary: "#8b949e",
          muted: "#6e7681",
        }
      },
      fontFamily: {
        sans: ["Space Grotesk", "IBM Plex Sans", "-apple-system", "sans-serif"],
        mono: ["JetBrains Mono", "IBM Plex Mono", "monospace"],
      }
    },
  },
  plugins: [],
}
