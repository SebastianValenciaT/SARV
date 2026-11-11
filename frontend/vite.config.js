import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  // Puerto fijo: el backend solo permite CORS desde :5173. Si está ocupado, falla en vez de saltar a otro.
  server: { port: 5173, strictPort: true },
})
