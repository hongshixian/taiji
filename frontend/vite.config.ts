import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import tailwindcss from '@tailwindcss/vite'
import path from 'node:path'

// https://vite.dev/config/
export default defineConfig({
  plugins: [vue(), tailwindcss()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, 'src'),
    },
  },
  build: {
    rollupOptions: {
      output: {
        // vendor 拆分：稳定的第三方库单独成 chunk，利于长期缓存；
        // echarts 体积大且仅 Leaderboard 用到，单独 chunk 保持懒加载
        manualChunks(id: string) {
          if (id.includes('node_modules')) {
            if (id.includes('echarts') || id.includes('zrender') || id.includes('vue-echarts')) {
              return 'vendor-echarts'
            }
            if (id.includes('reka-ui')) return 'vendor-reka'
            if (id.includes('/vue/') || id.includes('vue-router') || id.includes('/@vue/') || id.includes('pinia')) {
              return 'vendor-vue'
            }
            return 'vendor'
          }
        },
      },
    },
    chunkSizeWarningLimit: 700,
  },
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:5000',
        changeOrigin: true,
      },
    },
  },
})
