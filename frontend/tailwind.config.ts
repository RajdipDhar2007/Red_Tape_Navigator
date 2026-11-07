import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        brand: { 50: "#eef6ff", 600: "#1d4ed8", 700: "#1e40af", 900: "#0f2a63" },
      },
    },
  },
  plugins: [],
};
export default config;
