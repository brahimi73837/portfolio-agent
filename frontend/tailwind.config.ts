import type { Config } from "tailwindcss";
const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: { accent: "#4f46e5" }, // indigo; tweak to your brand color
    },
  },
  plugins: [require("@tailwindcss/typography")],
};
export default config;
