/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./templates/**/*.html",
    "./static/js/**/*.js",
    "./blueprints/**/*.py",
  ],
  theme: {
    extend: {
      colors: {
        'tunis-red': {
          500: '#AE191B',
          600: '#DA191D'
        }
      },
      fontFamily: {
        'inter': ['Inter', 'sans-serif'],
      }
    },
  },
  plugins: [],
}