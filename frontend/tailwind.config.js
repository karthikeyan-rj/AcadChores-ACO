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
        background: '#08090B',
        foreground: '#F4F4F5',
        card: {
          DEFAULT: '#121419',
          hover: '#181B21',
        },
        border: {
          DEFAULT: 'rgba(255,255,255,0.07)',
          light: 'rgba(255,255,255,0.12)',
          strong: 'rgba(255,255,255,0.15)',
        },
        primary: {
          DEFAULT: '#7C3AED',
          hover: '#6D28D9',
          muted: 'rgba(124,58,237,0.12)',
          glow: 'rgba(124,58,237,0.25)',
        },
        accent: {
          DEFAULT: '#ADFF2F',
          muted: 'rgba(173,255,47,0.08)',
          dim: 'rgba(173,255,47,0.15)',
        },
        success: '#4ADE80',
        warning: '#FBBF24',
        danger: {
          DEFAULT: '#F87171',
          muted: 'rgba(248,113,113,0.1)',
        },
        surface: {
          DEFAULT: '#0D0F12',
          2: '#121419',
          3: '#181B21',
          4: '#1E2128',
        },
        muted: '#71717A',
        'text-secondary': '#A1A1AA',
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', '-apple-system', 'sans-serif'],
        mono: ['JetBrains Mono', 'Fira Code', 'monospace'],
        display: ['Inter', 'system-ui', 'sans-serif'],
      },
      fontSize: {
        '2xs': ['0.65rem', { lineHeight: '0.9rem' }],
      },
      borderRadius: {
        'sm': '6px',
        'md': '10px',
        'lg': '14px',
        'xl': '18px',
      },
      boxShadow: {
        'matte': '0 1px 3px rgba(0,0,0,0.4), 0 1px 2px rgba(0,0,0,0.3)',
        'matte-md': '0 4px 12px rgba(0,0,0,0.4), 0 2px 4px rgba(0,0,0,0.3)',
        'matte-lg': '0 8px 24px rgba(0,0,0,0.5), 0 4px 8px rgba(0,0,0,0.3)',
        'inner-glow': 'inset 0 1px 0 rgba(255,255,255,0.03)',
        'violet-glow': '0 0 20px rgba(124,58,237,0.15)',
      },
      animation: {
        'fade-in': 'fadeIn 0.2s ease-out',
        'slide-up': 'slideUp 0.25s ease-out',
        'pulse-slow': 'pulse 3s ease-in-out infinite',
        'glow-line': 'glowLine 2s ease-in-out infinite',
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
        pulse: {
          '0%, 100%': { opacity: '1' },
          '50%': { opacity: '0.6' },
        },
        glowLine: {
          '0%, 100%': { opacity: '0.3' },
          '50%': { opacity: '0.8' },
        },
      },
    },
  },
  plugins: [],
}
