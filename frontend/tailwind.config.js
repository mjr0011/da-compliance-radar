/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ['./app/**/*.{js,ts,jsx,tsx}', './components/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        // D&A brand — sampled from the logo
        navy: {
          50:  '#f0f3f7',
          100: '#dde3ec',
          200: '#b7c4d5',
          300: '#8497b3',
          400: '#506a8e',
          500: '#2d4a72',
          600: '#1c3258',
          700: '#142648',  // close to logo navy
          800: '#0e1c36',
          900: '#091428',
          950: '#050a18',
        },
        cream: {
          50:  '#fdfcf8',
          100: '#f7f3e9',
          200: '#ede5cf',
        },
        accent: {
          DEFAULT: '#c89b3c',  // warm gold accent
          soft: '#e2c98a',
        },
        risk: {
          low:      '#3f7f5f',
          medium:   '#b08a2e',
          high:     '#c25c2c',
          critical: '#9b2b2b',
        },
      },
      fontFamily: {
        display: ['"Bodoni Moda"', 'Georgia', 'serif'],
        sans: ['"Inter Tight"', 'system-ui', 'sans-serif'],
        mono: ['"JetBrains Mono"', 'ui-monospace', 'monospace'],
      },
      letterSpacing: {
        tightish: '-0.011em',
        wider2: '0.14em',
      },
      boxShadow: {
        card: '0 1px 0 rgba(20, 38, 72, 0.04), 0 8px 24px -12px rgba(20, 38, 72, 0.18)',
        innerline: 'inset 0 -1px 0 rgba(20, 38, 72, 0.08)',
      },
    },
  },
  plugins: [],
};
