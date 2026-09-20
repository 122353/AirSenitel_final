import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import tailwindcss from '@tailwindcss/vite';

export default defineConfig({
  optimizeDeps: {
    // MapLibre 6's separately bundled module worker must not be moved into
    // Vite's dependency cache, where its sibling import would be missing.
    exclude: ['maplibre-gl'],
  },
  plugins: [
    react(),
    tailwindcss(),
  ],
  server: {
    port: 3000,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api(?=\/|$)/, ''),
      }
    }
  }
});
