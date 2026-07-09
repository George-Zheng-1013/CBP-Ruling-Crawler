import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// Vite 配置：React 插件 + 开发服务器端口。
// 跨域由后端 CORS 处理，此处无需额外代理。
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    host: true,
  },
});
