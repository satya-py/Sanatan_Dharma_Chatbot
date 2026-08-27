/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        saffron: {
          50: '#fff9f2',
          100: '#ffe5cc',
          200: '#ffbf80',
          300: '#ff9933', // Traditional Saffron
          400: '#ff8000',
          500: '#ff6600',
          600: '#cc5200',
          700: '#993d00',
          800: '#662900',
          900: '#331400',
          dark: '#E65100', // Deep Saffron
        },
        gold: {
          50: '#fffdf0',
          100: '#fff9bf',
          200: '#fff380',
          300: '#ffd700', // Metallic Gold
          400: '#cca300',
          500: '#997a00',
          600: '#665200',
          DEFAULT: '#FFD700',
          dark: '#DAA520',
        },
        temple: {
          marble: '#FDFBF7',  // Marble white cream
          charcoal: '#1A1008', // Holy wood smoke / dark theme bg
          brown: '#2D1E12',
          saffron: '#FF6F00',
        }
      },
      fontFamily: {
        sans: ['Outfit', 'Inter', 'sans-serif'],
      },
      animation: {
        'float-slow': 'float 6s ease-in-out infinite',
        'pulse-wave': 'pulse-wave 1.5s ease-in-out infinite',
        'spin-slow': 'spin 12s linear infinite',
      },
      keyframes: {
        float: {
          '0%, 100%': { transform: 'translateY(0)' },
          '50%': { transform: 'translateY(-8px)' },
        },
        'pulse-wave': {
          '0%, 100%': { transform: 'scale(1)', opacity: '0.4' },
          '50%': { transform: 'scale(1.2)', opacity: '0.8' },
        }
      }
    },
  },
  plugins: [],
}
