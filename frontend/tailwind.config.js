/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    // Ventriloc — editorial data observatory. Light mode only.
    colors: {
      transparent: "transparent",
      current: "currentColor",
      canvas: "#ffffff",       // Canvas White  — page background
      ash: "#efefef",          // Ash           — primary surface / alternating band
      fog: "#f5f5f5",          // Fog           — secondary surface
      ivory: "#ebe6dd",        // Ivory         — warm accent surface (highlight rows)
      mist: "#e8e8e8",         // Mist          — dividers / borders
      graphite: "#202020",     // Graphite      — primary text / primary button fill
      steel: "#4d4d4d",        // Steel         — secondary text
      slate: "#828282",        // Slate         — tertiary text / axis labels
      ember: "#ff682c",        // Ember Orange  — accent: chart highlight, link underline, tiny icons ONLY
      brass: "#816729",        // Brass         — secondary chart accent
      white: "#ffffff",
      black: "#000000",
    },
    borderRadius: {
      none: "0px",
      sm: "6px",
      DEFAULT: "8px",
      card: "8px",
      tag: "20px",
      pill: "200px",
      full: "9999px",
    },
    boxShadow: {
      none: "none",
    },
    extend: {
      fontFamily: {
        // PolySans substitute — neo-grotesque, weight 400 only, -0.02em tracking
        display: ["'Space Grotesk'", "'Inter Tight'", "system-ui", "sans-serif"],
        sans: ["Inter", "system-ui", "-apple-system", "Roboto", "sans-serif"],
      },
      letterSpacing: {
        display: "-0.02em",
      },
      maxWidth: {
        shell: "1200px",
      },
      spacing: {
        4.5: "18px",
        9: "36px",
        15: "60px",
        35: "140px",
      },
      fontSize: {
        display: ["66px", { lineHeight: "0.91", letterSpacing: "-1.32px" }],
        "heading-lg": ["40px", { lineHeight: "1.2", letterSpacing: "-0.8px" }],
        heading: ["32px", { lineHeight: "1.19", letterSpacing: "-0.64px" }],
        subheading: ["18px", { lineHeight: "1.25", letterSpacing: "-0.02em" }],
      },
    },
  },
  plugins: [],
};
