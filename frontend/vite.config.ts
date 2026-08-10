import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      // REST API → 后端
      '/api': {
        target: 'http://localhost:8012',
        changeOrigin: true,
      },
      // WebSocket → 后端
      '/ws': {
        target: 'ws://localhost:8012',
        ws: true,
        changeOrigin: true,
      },
    },
  },
});
