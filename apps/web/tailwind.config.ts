import type { Config } from "tailwindcss";

export default {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      fontFamily: {
        // SLBSans (Schlumberger brand sans) — vendored from
        // github.com/Amory0709/SLB100FamilyDay/assets/fonts/
        sans: ["SLBSans", "Helvetica Neue", "Helvetica", "Arial", "system-ui", "sans-serif"],
        serif: ["SLBSans", "Helvetica Neue", "Helvetica", "Arial", "serif"],
        display: ["SLBSans", "Helvetica Neue", "Helvetica", "Arial", "sans-serif"],
        mono: ["ui-monospace", "monospace"],
      },
      colors: {
        background: "var(--color-background)",
        foreground: "var(--color-foreground)",
        card: {
          DEFAULT: "var(--color-card)",
          foreground: "var(--color-card-foreground)",
        },
        primary: {
          DEFAULT: "var(--color-primary)",
          foreground: "var(--color-primary-foreground)",
        },
        muted: {
          DEFAULT: "var(--color-muted)",
          foreground: "var(--color-muted-foreground)",
        },
        border: "var(--color-border)",
        slb: { DEFAULT: "#0033CC", soft: "#1F4ED8", tint: "#E6ECFA", ghost: "#F4F7FD" },
        ink: "#0B1220",
        paper: "#FFFFFF",
        line: "#E2E8F0",
        rust: "#A04A2A",
        gold: "#C8A864",
        cream: "#F1ECDF",
      },
      boxShadow: { frame: "0 24px 60px -24px rgba(0,51,204,0.20)" },
    },
  },
} satisfies Config;
