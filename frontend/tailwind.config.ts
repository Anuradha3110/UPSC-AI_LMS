import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./lib/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        // Light-blue/white brand scale. 600/800 match the hex the app
        // already shipped with (CTAs / hero panels) so this is a
        // relabeling of the existing palette, not a new one.
        brand: {
          50: "#F4F8FF",
          100: "#E6EFFE",
          200: "#CFE1FD",
          300: "#A6C8FB",
          400: "#6FA3F5",
          500: "#3B7DEA",
          600: "#0056D2",
          700: "#0044A8",
          800: "#00297A",
          900: "#001A52",
        },
      },
      boxShadow: {
        card: "0 1px 2px 0 rgb(15 23 42 / 0.04), 0 1px 3px 0 rgb(15 23 42 / 0.06)",
      },
    },
  },
  plugins: [],
};

export default config;
