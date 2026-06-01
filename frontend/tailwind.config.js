/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './pages/**/*.{js,ts,jsx,tsx,mdx}',
    './components/**/*.{js,ts,jsx,tsx,mdx}',
    './app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        background: '#F7F7F7',
        foreground: '#2B2B2B',
        // Primary brand: #FF4F00 (orange-red)
        primary: {
          50:  '#FFF2EE',
          100: '#FFE0D5',
          200: '#FFBFAA',
          300: '#FF9475',
          400: '#FF6B40',
          500: '#FF4F00',  // brand primary
          600: '#CC3F00',
          700: '#993000',
        },
        // Secondary: #2B2B2B (near-black)
        secondary: {
          50:  '#F5F5F5',
          100: '#E8E8E8',
          200: '#D0D0D0',
          300: '#ABABAB',
          400: '#7A7A7A',
          500: '#555555',
          600: '#3D3D3D',
          700: '#2B2B2B',  // brand secondary
          800: '#1A1A1A',
          900: '#0D0D0D',
        },
        // Tertiary: #0051FF (blue)
        tertiary: {
          50:  '#EEF3FF',
          100: '#D5E1FF',
          200: '#AABEFF',
          300: '#7598FF',
          400: '#3D72FF',
          500: '#0051FF',  // brand tertiary
          600: '#0041CC',
          700: '#003199',
        },
        // Neutral
        neutral: {
          50:  '#FFFFFF',
          100: '#F7F7F7',  // brand neutral
          200: '#EFEFEF',
          300: '#E0E0E0',
          400: '#BDBDBD',
          500: '#9E9E9E',
          600: '#757575',
          700: '#616161',
          800: '#424242',
          900: '#212121',
        },
        // Keep surface alias for backward compat
        surface: {
          50:  '#FFFFFF',
          100: '#F7F7F7',
          200: '#EFEFEF',
          300: '#E0E0E0',
          400: '#BDBDBD',
          500: '#9E9E9E',
          600: '#757575',
          700: '#616161',
          800: '#424242',
          900: '#212121',
        },
        // Keep accent alias pointing to primary
        accent: {
          50:  '#FFF2EE',
          100: '#FFE0D5',
          200: '#FFBFAA',
          300: '#FF9475',
          400: '#FF6B40',
          500: '#FF4F00',
          600: '#CC3F00',
          700: '#993000',
        },
      },
      fontFamily: {
        display: ['Plus Jakarta Sans', 'Inter', 'sans-serif'],
        body: ['Inter', 'sans-serif'],
      },
      boxShadow: {
        card: '0 1px 3px 0 rgba(0,0,0,0.07), 0 1px 2px -1px rgba(0,0,0,0.06)',
        'card-hover': '0 6px 20px 0 rgba(0,0,0,0.10)',
        soft: '0 2px 8px rgba(0,0,0,0.05)',
      },
      borderRadius: {
        xl:  '0.75rem',
        '2xl': '1rem',
        '3xl': '1.25rem',
      },
    },
  },
  plugins: [],
}