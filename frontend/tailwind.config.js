/** @type {import('tailwindcss').Config} */
module.exports = {
  darkMode: "class",
  content: [
    "./app/**/*.{js,ts,jsx,tsx}",
    "./components/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        jai: {
          // ── JAGGAER Brand — from jaggaer.com design system ──
          // Solution categorical colors
          analytics: "#CF825B",
          "analytics-light": "#FDF4EF",
          "analytics-border": "#F0D4BE",
          reporting: "#E44E50",
          "reporting-light": "#FDF0F0",
          "reporting-border": "#F5B8B9",
          admin: "#993555",
          "admin-light": "#F9EEF2",
          "admin-border": "#DDA8BB",
          platform: "#DF4F77",
          "platform-light": "#FDF1F5",
          "platform-border": "#F2B3C6",
          // Primary = Platform pink (JAGGAER main brand color)
          primary: "#DF4F77",
          "primary-hover": "#C93B61",
          "primary-light": "#FDF1F5",
          "primary-border": "#F2B3C6",
          accent: "#DF4F77",
          "accent-light": "#FDF1F5",
          "accent-border": "#F2B3C6",
          brand: "#DF4F77",
          "brand-light": "#FDF1F5",
          "brand-border": "#F2B3C6",
          // Dark navy (text, headers, dark sections)
          navy: "#1B2A4A",
          "navy-light": "#2D3E5C",
          // Functional
          info: "#0EA5E9",
          "info-light": "#F0F9FF",
          "info-border": "#BAE6FD",
          success: "#059669",
          "success-light": "#ECFDF5",
          warning: "#F59E0B",
          "warning-light": "#FFFBEB",
          danger: "#E44E50",
          "danger-light": "#FDF0F0",
          // Sidebar
          sidebar: "#FAFAFA",
          "sidebar-border": "#E2E8F0",
          "sidebar-active": "#FDF1F5",
          "sidebar-text": "#334155",
          "sidebar-muted": "#94A3B8",
          // Surface
          surface: "#FFFFFF",
          "surface-secondary": "#F8FAFC",
          "surface-tertiary": "#F1F5F9",
        },
      },
      fontFamily: {
        sans: ["Inter", "-apple-system", "BlinkMacSystemFont", "sans-serif"],
        mono: ["JetBrains Mono", "monospace"],
      },
      boxShadow: {
        "card": "0 1px 3px 0 rgba(0,0,0,0.04), 0 1px 2px -1px rgba(0,0,0,0.03)",
        "card-hover": "0 4px 12px -2px rgba(0,0,0,0.08), 0 2px 6px -2px rgba(0,0,0,0.04)",
        "dialog": "0 20px 60px -12px rgba(0,0,0,0.2), 0 8px 20px -8px rgba(0,0,0,0.1)",
      },
      keyframes: {
        "sla-pulse": {
          "0%, 100%": { opacity: "1" },
          "50%": { opacity: "0.6" },
        },
        "fade-in": {
          "0%": { opacity: "0" },
          "100%": { opacity: "1" },
        },
        "fade-up": {
          "0%": { opacity: "0", transform: "translateY(8px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
        "scale-in": {
          "0%": { opacity: "0", transform: "scale(0.95)" },
          "100%": { opacity: "1", transform: "scale(1)" },
        },
        "slide-in-right": {
          "0%": { opacity: "0", transform: "translateX(100%)" },
          "100%": { opacity: "1", transform: "translateX(0)" },
        },
        "slide-in-left": {
          "0%": { opacity: "0", transform: "translateX(-12px)" },
          "100%": { opacity: "1", transform: "translateX(0)" },
        },
        "bounce-dots": {
          "0%, 80%, 100%": { transform: "scale(0)" },
          "40%": { transform: "scale(1)" },
        },
      },
      animation: {
        "sla-pulse": "sla-pulse 2s ease-in-out infinite",
        "fade-in": "fade-in 200ms ease-out",
        "fade-up": "fade-up 250ms ease-out",
        "scale-in": "scale-in 200ms ease-out",
        "slide-in-right": "slide-in-right 250ms ease-out",
        "slide-in-left": "slide-in-left 200ms ease-out",
        "bounce-dots": "bounce-dots 1.4s infinite ease-in-out both",
      },
    },
  },
  plugins: [],
};
