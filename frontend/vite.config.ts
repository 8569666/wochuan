import { defineConfig } from 'vitest/config'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  server: { port: 5173, strictPort: true, proxy: { '/api': { target: process.env.API_TARGET || 'http://127.0.0.1:8000', changeOrigin: false } } },
  test: { environment: 'jsdom', include: ['src/tests/**/*.spec.ts'] },
})
