/** @type {import('tailwindcss').Config} */
// Colours are CSS variables (see src/index.css) so the theme lives in one place.
const v = (name) => `rgb(var(--${name}) / <alpha-value>)`
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        surface: v('surface'),
        card: v('card'),
        line: v('line'),
        ink: v('ink'),
        muted: v('muted'),
        brand: v('brand'),
        'brand-ink': v('brand-ink'),
        'brand-soft': v('brand-soft'),
        good: v('good'),
        'good-ink': v('good-ink'),
        'good-bg': v('good-bg'),
        'good-line': v('good-line'),
        warn: v('warn'),
        'warn-ink': v('warn-ink'),
        'warn-bg': v('warn-bg'),
        'warn-line': v('warn-line'),
        bad: v('bad'),
        'bad-ink': v('bad-ink'),
        'bad-bg': v('bad-bg'),
        'bad-line': v('bad-line'),
      },
      fontFamily: { sans: ['Inter', 'system-ui', 'Segoe UI', 'Roboto', 'sans-serif'] },
    },
  },
  plugins: [],
}
