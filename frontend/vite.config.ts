import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  build: {
    rollupOptions: {
      output: {
        manualChunks: {
          'react-vendor': ['react', 'react-dom'],
          'charts-vendor': ['recharts'],
          'markdown-vendor': ['react-markdown', 'remark-gfm'],
          'icons-vendor': ['lucide-react'],
        },
      },
    },
  },
})
