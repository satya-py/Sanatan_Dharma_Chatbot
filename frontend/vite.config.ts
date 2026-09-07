import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  // Vite only exposes variables matching envPrefix to client code, and the
  // default is "VITE_" alone. API_BASE_URL would be silently undefined at
  // build time without this, leaving the app pointed at localhost.
  // Keep this list specific: a broad prefix (or "") would inline every
  // variable in the build environment into the public bundle.
  envPrefix: ['VITE_', 'API_'],
})
