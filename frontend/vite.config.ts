import { fileURLToPath, URL } from 'node:url';

import react from '@vitejs/plugin-react';
import { defineConfig } from 'vite';

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      // Keep in sync with tsconfig.json compilerOptions.paths ("@/*" -> "./src/*").
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
  server: {
    port: 3000,
    open: true,
    // Bind all interfaces so the dev server is reachable from outside the
    // container (sandboxes, devcontainers, LAN testing). Harmless locally.
    host: true,
    // Vite 5 rejects requests whose Host header it does not recognise. Allow
    // the hosted preview domains in addition to localhost, otherwise the dev
    // server answers "Blocked request" behind a proxy.
    allowedHosts: ['localhost', '127.0.0.1', '.e2b.app', '.github.dev', '.gitpod.io'],
    proxy: {
      // Forward the migrated v1 API to the backend. The deprecated /api/*
      // aliases are retained for dev-time backward compatibility.
      '/v1': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
});
