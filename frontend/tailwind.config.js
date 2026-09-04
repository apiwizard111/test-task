/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#0b0d11",
        panel: "#12151c",
        raised: "#181c25",
        line: "#242a36",
        mute: "#8b93a7",
        lime: "#c8f542",
        mist: "#e8ecf4",
        danger: "#ff6b6b",
      },
      fontFamily: {
        sans: ['"IBM Plex Sans"', "ui-sans-serif", "system-ui", "sans-serif"],
        mono: ['"IBM Plex Mono"', "ui-monospace", "SFMono-Regular", "monospace"],
      },
      boxShadow: {
        glow: "0 0 0 1px rgba(200,245,66,0.18), 0 18px 50px rgba(0,0,0,0.35)",
      },
    },
  },
  plugins: [],
};
