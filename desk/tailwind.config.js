import frappeUIPreset, { content as frappeUIContent } from "frappe-ui/tailwind";

export default {
  presets: [frappeUIPreset],
  content: [
    "./index.html",
    "./src/**/*.{vue,js,ts,jsx,tsx}",
    ...frappeUIContent,
    // frappe-ui's own content list leaves experimental/ListView out; helpdesk
    // still renders it, so its classes have to be scanned here.
    "./node_modules/frappe-ui/experimental/ListView/**/*.{vue,js,ts,jsx,tsx}",
    "../../frappe/ui/src/**/*.{vue,js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        primary: {
          DEFAULT: "var(--primary)",
          hover: "var(--primary-hover, #1d4ed8)",
          active: "var(--primary-active, #1e40af)",
          light: "var(--primary-light, #eff6ff)",
          foreground: "var(--primary-foreground, #ffffff)",
        },
        secondary: {
          DEFAULT: "var(--secondary)",
          hover: "var(--secondary-hover, #e2e8f0)",
          active: "var(--secondary-active, #cbd5e1)",
          light: "var(--secondary-light, #f8fafc)",
          foreground: "var(--secondary-foreground, #0f172a)",
        },
      },
    },
  },
  plugins: [
    require("@tailwindcss/typography"),
    require("tailwindcss-rtl"),
    function ({ addUtilities }) {
      addUtilities({
        ".hide-scrollbar": {
          "scrollbar-width": "none",
          "-ms-overflow-style": "none",
          "&::-webkit-scrollbar": {
            display: "none",
          },
        },
      });
    },
  ],
};

