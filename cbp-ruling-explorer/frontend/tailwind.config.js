/** @type {import('tailwindcss').Config} */
// 与 MUI 共存：关闭 preflight 以避免重置样式与 MUI 冲突。
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  corePlugins: {
    preflight: false,
  },
  theme: {
    extend: {
      colors: {
        'cbp-navy': '#1A3E72',
        'cbp-blue': '#2E6FB0',
      },
    },
  },
  plugins: [],
};
