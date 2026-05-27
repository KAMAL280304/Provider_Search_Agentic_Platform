import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    historyApiFallback: true,
    proxy: {
      '/chat': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      '/adk': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      '/run': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      '/apps': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      '/login': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      '/memory': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      '/health': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      '/logout': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      '/availability': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      '/appointments': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      '/dev': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      '/update-plan': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      '/dashboard': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      '/payer': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    }
  }
})
