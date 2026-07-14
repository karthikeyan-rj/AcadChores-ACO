/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        background: '#0c0c10',
        foreground: '#e8e8ec',
        card: '#14151c',
        'card-hover': '#181922',
        border: '#1e1f2a',
        'border-light': '#272836',
        primary: {
          DEFAULT: '#6366f1',
          hover: '#5558e6',
          muted: '#6366f115',
        },
        accent: '#4ade80',
        'accent-muted': '#4ade8015',
        danger: '#f87171',
        'danger-muted': '#f8717115',
        warning: '#fbbf24',
        'warning-muted': '#fbbf2415',
        surface: '#101118',
        'surface-2': '#161720',
        'surface-3': '#1c1d28',
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', '-apple-system', 'sans-serif'],
        mono: ['JetBrains Mono', 'Fira Code', 'monospace'],
      },
      animation: {
        'fade-in': 'fadeIn 0.2s ease-out',
        'slide-up': 'slideUp 0.25s ease-out',
      },
      keyframes: {
        fadeIn: {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
        slideUp: {
          '0%': { transform: 'translateY(8px)', opacity: '0' },
          '100%': { transform: 'translateY(0)', opacity: '1' },
        },
      },
    },
  },
  plugins: [],
}
