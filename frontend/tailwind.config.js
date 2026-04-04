/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        mono: ['JetBrains Mono', 'Fira Code', 'SF Mono', 'Consolas', 'monospace'],
      },
      colors: {
        accent: '#0077cc',
        'accent-light': '#00b4d8',
        'accent-purple': '#7c3aed',
        surface: '#f8f8fc',
        'surface-2': '#f0f0f5',
        'surface-3': '#e8e8f0',
        qborder: '#d0d0e0',
        'qborder-bright': '#b0b0c8',
      },
    },
  },
  plugins: [],
}
