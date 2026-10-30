import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// The dev server proxies /api to FastAPI, so the browser never needs the backend URL
// (and the Gemini key stays on the backend). host:true lets a phone on the same Wi-Fi
// open http://<laptop-ip>:5173 and use its camera via the file input.
export default defineConfig({
  plugins: [react()],
  // Don't follow Windows path redirections/symlinks to a "real" path (avoids blank pages
  // when the project lives in a redirected or very long folder).
  resolve: { preserveSymlinks: true },
  server: {
    host: true,
    port: 5173,
    proxy: { '/api': { target: 'http://127.0.0.1:8000', changeOrigin: true } },
  },
})
