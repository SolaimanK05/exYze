import react from '@vitejs/plugin-react'
import { defineConfig } from 'vitest/config'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    // The FastAPI server runs on :8000 in the local setup (see 01 Architecture and Contracts).
    proxy: {
      '/api': 'http://localhost:8000',
    },
  },
  test: {
    include: ['src/**/*.test.ts'],
  },
})
