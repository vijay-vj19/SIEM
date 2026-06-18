/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      fontFamily: {
        mono: ['JetBrains Mono', 'Fira Code', 'Consolas', 'monospace'],
      },
      colors: {
        soc: {
          bg: '#0a0e1a',
          surface: '#111827',
          border: '#1f2937',
          accent: '#3b82f6',
        },
      },
    },
  },
  plugins: [],
}
