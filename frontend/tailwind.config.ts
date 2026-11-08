import type { Config } from "tailwindcss";

// Palette drawn from the tricolour: deep navy (trust, primary), saffron (energy, highlights), India green (success).
const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        navy: { 50: "#eef3fb", 100: "#d9e3f5", 200: "#b3c7eb", 300: "#86a3da", 600: "#1f3f8f", 700: "#183274", 800: "#122659", 900: "#0b1a40" },
        saffron: { 50: "#fff6ec", 100: "#ffe8cc", 200: "#ffd199", 400: "#ffa94d", 500: "#f58a1f", 600: "#d96f0a", 700: "#a85205" },
        indgreen: { 50: "#ecf8ee", 100: "#d3f0d8", 500: "#2e9e44", 600: "#138808", 700: "#0f6b07", 800: "#0c5406" },
        // legacy alias used by older components
        brand: { 50: "#eef3fb", 600: "#1f3f8f", 700: "#183274", 900: "#0b1a40" },
      },
      fontFamily: {
        head: ["var(--font-head)", "var(--font-deva)", "var(--font-beng)", "system-ui", "sans-serif"],
        body: ["var(--font-body)", "var(--font-deva)", "var(--font-beng)", "system-ui", "sans-serif"],
      },
      boxShadow: {
        card: "0 1px 2px rgba(11,26,64,.06), 0 6px 20px -8px rgba(11,26,64,.18)",
        lift: "0 2px 4px rgba(11,26,64,.08), 0 18px 36px -12px rgba(11,26,64,.30)",
      },
      keyframes: {
        fadeUp: { from: { opacity: "0", transform: "translateY(14px)" }, to: { opacity: "1", transform: "none" } },
        floaty: { "0%,100%": { transform: "translateY(0)" }, "50%": { transform: "translateY(-10px)" } },
        spinSlow: { to: { transform: "rotate(360deg)" } },
      },
      animation: {
        "fade-up": "fadeUp .55s cubic-bezier(.2,.7,.2,1) both",
        floaty: "floaty 7s ease-in-out infinite",
        "spin-slow": "spinSlow 60s linear infinite",
      },
    },
  },
  plugins: [],
};
export default config;
