/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ['"IBM Plex Sans"', 'system-ui', 'sans-serif'],
        mono: ['"IBM Plex Mono"', 'ui-monospace', 'SFMono-Regular', 'monospace'],
      },
      colors: {
        // IBM Carbon gray scale (light theme)
        gray: {
          10: '#f4f4f4',
          20: '#e0e0e0',
          30: '#c6c6c6',
          40: '#a8a8a8',
          50: '#8d8d8d',
          60: '#6f6f6f',
          70: '#525252',
          80: '#393939',
          90: '#262626',
          100: '#161616',
        },
        blue: {
          10: '#edf5ff',
          20: '#d0e2ff',
          60: '#0f62fe',
          70: '#0353e9',
        },
        red: {
          10: '#fff1f1',
          60: '#da1e28',
        },
        green: {
          50: '#24a148',
        },
        yellow: {
          30: '#f1c21b',
        },
        // Hairline border
        line: '#e0e0e0',
        // Gate family fills (flat, Composer-style)
        gate: {
          pauli: '#4589ff',
          h: '#fa4d56',
          phase: '#a56eff',
          rot: '#009d9a',
          ctrl: '#24a148',
          meas: '#8d8d8d',
        },
      },
    },
  },
  plugins: [],
}
