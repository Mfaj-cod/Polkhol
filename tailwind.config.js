/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./app/templates/**/*.html",
    "./app/static/js/**/*.js"
  ],
  theme: {
    extend: {
      colors: {
        ink: "#070b15",
        storm: "#0f172a",
        mist: "#d1d5db",
        signal: "#34d399",
        flare: "#60a5fa",
        ember: "#f97316"
      },
      animation: {
        "aurora-shift": "aurora-shift 18s ease-in-out infinite",
        float: "float 8s ease-in-out infinite"
      },
      keyframes: {
        "aurora-shift": {
          "0%, 100%": { transform: "translate3d(0, 0, 0) scale(1)" },
          "50%": { transform: "translate3d(3%, -2%, 0) scale(1.04)" }
        },
        float: {
          "0%, 100%": { transform: "translateY(0px)" },
          "50%": { transform: "translateY(-8px)" }
        }
      }
    }
  },
  plugins: []
};


