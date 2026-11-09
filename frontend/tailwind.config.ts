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
        pop: { "0%": { opacity: "0", transform: "scale(.85)" }, "60%": { transform: "scale(1.05)" }, "100%": { opacity: "1", transform: "none" } },
        slideInLeft: { from: { opacity: "0", transform: "translateX(-16px)" }, to: { opacity: "1", transform: "none" } },
        slideInRight: { from: { opacity: "0", transform: "translateX(16px)" }, to: { opacity: "1", transform: "none" } },
        shimmer: { "0%": { backgroundPosition: "-200% 0" }, "100%": { backgroundPosition: "200% 0" } },
        orb: { "0%,100%": { transform: "translate(0,0) scale(1)" }, "33%": { transform: "translate(30px,-24px) scale(1.08)" }, "66%": { transform: "translate(-22px,16px) scale(.95)" } },
        dots: { "0%,80%,100%": { transform: "translateY(0)", opacity: ".4" }, "40%": { transform: "translateY(-5px)", opacity: "1" } },
        ringPulse: { "0%": { boxShadow: "0 0 0 0 rgba(245,138,31,.55)" }, "100%": { boxShadow: "0 0 0 12px rgba(245,138,31,0)" } },
        tick: { "0%": { transform: "scale(0) rotate(-20deg)" }, "70%": { transform: "scale(1.25) rotate(6deg)" }, "100%": { transform: "scale(1) rotate(0)" } },
      },
      animation: {
        "fade-up": "fadeUp .55s cubic-bezier(.2,.7,.2,1) both",
        floaty: "floaty 7s ease-in-out infinite",
        "spin-slow": "spinSlow 60s linear infinite",
        pop: "pop .45s cubic-bezier(.2,.7,.2,1) both",
        "slide-in-left": "slideInLeft .4s cubic-bezier(.2,.7,.2,1) both",
        "slide-in-right": "slideInRight .4s cubic-bezier(.2,.7,.2,1) both",
        shimmer: "shimmer 3.2s linear infinite",
        orb: "orb 16s ease-in-out infinite",
        "ring-pulse": "ringPulse 1.6s ease-out infinite",
        tick: "tick .4s cubic-bezier(.2,.7,.2,1) both",
      },
    },
  },
  plugins: [],
};
export default config;
