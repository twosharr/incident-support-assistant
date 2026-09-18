/** @type {import("tailwindcss").Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        teams: {
          purple: "#6264A7",
          "purple-dark": "#464775",
          bg: "#1F1F1F",
          sidebar: "#292929",
          surface: "#2D2D2D",
          border: "#3D3D3D",
          text: "#E8E8E8",
          "text-muted": "#A0A0A0",
        },
      },
    },
  },
  plugins: [],
};
