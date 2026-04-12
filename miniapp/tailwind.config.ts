import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{js,ts,jsx,tsx}", "./components/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#102542",
        paper: "#fffaf2",
        low: "#2a9d8f",
        medium: "#f4a261",
        high: "#d1495b"
      }
    }
  },
  plugins: []
};

export default config;
