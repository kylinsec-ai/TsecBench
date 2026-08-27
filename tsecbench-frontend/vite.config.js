import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  server: {
    port: 5173,
    host: '0.0.0.0',
    proxy: {
      '/openapi': {
        target: process.env.TSECBENCH_PROXY_TARGET || 'https://tsecbench.zc.tencent.com',
        changeOrigin: true,
      },
    },
  },
})