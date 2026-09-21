/** @type {import('tailwindcss').Config} */
export default {
  darkMode: "class",
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ["Inter", "system-ui", "sans-serif"],
        display: ["Plus Jakarta Sans", "Inter", "sans-serif"],
      },
      colors: {
        // Custom Dark Purple Editorial & Calm Palette:
        primary: {
          50: "#F5F2FA",
          100: "#EBE5F6", // Pale Lavender (Accent light)
          200: "#D6CBEC",
          300: "#B6A3DE",
          400: "#9376C8",
          500: "#6F4FB1", // Dark Purple (Primary accent)
          600: "#5D3F9C",
          700: "#4B2E83",
          800: "#3C2468",
          900: "#2E1B50",
          950: "#20123C",
        },
        secondary: {
          50: "#F5F2FA",
          100: "#EBE5F6",
          200: "#D6CBEC",
          300: "#B6A3DE",
          400: "#9376C8",
          500: "#6F4FB1",
          600: "#5D3F9C",
          700: "#4B2E83",
          800: "#3C2468",
          900: "#2E1B50",
          950: "#20123C",
        },
        lavender: {
          DEFAULT: "#6F4FB1",
          light: "#EBE5F6",
          50: "#F5F2FA",
          100: "#EBE5F6",
          200: "#D6CBEC",
          300: "#B6A3DE",
          400: "#9376C8",
          500: "#6F4FB1",
          600: "#5D3F9C",
          700: "#4B2E83",
        },
        success: {
          DEFAULT: "#8FAF9A", // Soft Sage
          light: "#EAF2EC",   // Pale Sage
          50: "#F4F8F5",
          100: "#EAF2EC",
          200: "#D4E5D8",
          300: "#B8D4BF",
          400: "#8FAF9A",
          500: "#759B82",
          600: "#5D826A",
          700: "#4A6854",
          800: "#3A5242",
          900: "#2B3D31",
        },
        warning: {
          DEFAULT: "#C49A5A", // Soft Amber
          light: "#F7F0E2",   // Pale Amber
          50: "#FDFBF7",
          100: "#F7F0E2",
          200: "#EFE1C5",
          300: "#E1CDA3",
          400: "#D1B47C",
          500: "#C49A5A",
          600: "#A87F42",
          700: "#876432",
          800: "#694C24",
          900: "#4E3719",
        },
        danger: {
          DEFAULT: "#C47F82", // Dusty Rose
          light: "#F8EAEA",   // Pale Rose
          50: "#FCF6F6",
          100: "#F8EAEA",
          200: "#F1D5D6",
          300: "#E5B9BB",
          400: "#D6999C",
          500: "#C47F82",
          600: "#AA6669",
          700: "#8C4F52",
          800: "#6E3B3E",
          900: "#52292B",
        },
        ivory: {
          DEFAULT: "#F8F7F4", // Soft Ivory
          50: "#FCFBF9",
          100: "#F8F7F4",
          200: "#EFECE6",
          300: "#E7E5E0", // Soft Gray (Borders)
          400: "#D3CFCA",
          500: "#A9A49E",
          600: "#6B6B6B", // Muted Gray (Secondary text)
          700: "#454545",
          800: "#333333",
          900: "#252525", // Soft Charcoal (Primary text)
          950: "#1A1A1A",
        },
        surface: {
          DEFAULT: "#FFFFFF", // Warm White (Cards / content)
          50: "#FCFBF9",
          100: "#F8F7F4", // Soft Ivory
          200: "#E7E5E0", // Soft Gray
          800: "#222120",
          900: "#1A1918",
        },
      },
      borderRadius: {
        "2xl": "1rem",
        "3xl": "1.5rem",
        "4xl": "2rem",
      },
      boxShadow: {
        "subtle": "0 1px 2px 0 rgba(0, 0, 0, 0.04)",
        "soft": "0 4px 20px -2px rgba(15, 23, 42, 0.06), 0 2px 6px -1px rgba(15, 23, 42, 0.04)",
        "card": "0 1px 3px 0 rgba(15, 23, 42, 0.04), 0 1px 2px -1px rgba(15, 23, 42, 0.04)",
        "card-hover": "0 16px 32px -8px rgba(15, 23, 42, 0.08), 0 4px 12px -2px rgba(15, 23, 42, 0.04)",
        "glass": "0 8px 32px 0 rgba(15, 23, 42, 0.06)",
        "dropdown": "0 12px 40px -10px rgba(15, 23, 42, 0.16), 0 4px 12px -4px rgba(15, 23, 42, 0.08)",
        "glow-primary": "0 0 24px -2px rgba(111, 79, 177, 0.4)",
        "glow-secondary": "0 0 24px -2px rgba(168, 85, 247, 0.35)",
        "glow-success": "0 0 24px -2px rgba(16, 185, 129, 0.35)",
      },
      animation: {
        "fade-in": "fadeIn 0.3s cubic-bezier(0.16, 1, 0.3, 1)",
        "slide-up": "slideUp 0.35s cubic-bezier(0.16, 1, 0.3, 1)",
        "slide-down": "slideDown 0.25s cubic-bezier(0.16, 1, 0.3, 1)",
        "slide-in-right": "slideInRight 0.3s cubic-bezier(0.16, 1, 0.3, 1)",
        "pulse-slow": "pulse 3s infinite",
        "bounce-slow": "bounce 2s infinite",
        "spin-slow": "spin 3s linear infinite",
        "float": "float 6s ease-in-out infinite",
        "gradient-x": "gradientX 7s ease infinite",
        "shimmer": "shimmer 3.5s ease-in-out infinite",
        "glow-pulse": "glowPulse 2.6s ease-in-out infinite",
        "wiggle": "wiggle 0.9s ease-in-out infinite",
      },
      keyframes: {
        fadeIn: {
          "0%": { opacity: "0" },
          "100%": { opacity: "1" },
        },
        slideUp: {
          "0%": { transform: "translateY(12px)", opacity: "0" },
          "100%": { transform: "translateY(0)", opacity: "1" },
        },
        slideDown: {
          "0%": { transform: "translateY(-12px)", opacity: "0" },
          "100%": { transform: "translateY(0)", opacity: "1" },
        },
        slideInRight: {
          "0%": { transform: "translateX(16px)", opacity: "0" },
          "100%": { transform: "translateX(0)", opacity: "1" },
        },
        float: {
          "0%, 100%": { transform: "translateY(0px)" },
          "50%": { transform: "translateY(-14px)" },
        },
        gradientX: {
          "0%, 100%": { backgroundPosition: "0% 50%" },
          "50%": { backgroundPosition: "100% 50%" },
        },
        shimmer: {
          "0%": { transform: "translateX(-150%)" },
          "50%": { transform: "translateX(400%)" },
          "100%": { transform: "translateX(400%)" },
        },
        glowPulse: {
          "0%, 100%": { boxShadow: "0 0 0 0 rgba(111, 79, 177, 0)" },
          "50%": { boxShadow: "0 0 26px 2px rgba(111, 79, 177, 0.55)" },
        },
        wiggle: {
          "0%, 100%": { transform: "rotate(0deg)" },
          "25%": { transform: "rotate(-10deg)" },
          "75%": { transform: "rotate(10deg)" },
        },
      },
    },
  },
  plugins: [],
};
