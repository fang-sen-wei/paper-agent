/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        primary: '#171717',
        secondary: '#404040',
        accent: '#D4AF37',
        background: '#FFFFFF',
        surface: '#F8F8F8',
        muted: '#737373',
      },
      fontFamily: {
        heading: ['"Crimson Pro"', 'serif'],
        body: ['"Atkinson Hyperlegible"', 'sans-serif'],
      },
    },
  },
  plugins: [],
}
