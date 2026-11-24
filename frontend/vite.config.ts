/// <reference types="vitest/config" />
import { fileURLToPath, URL } from 'node:url';
import tailwindcss from '@tailwindcss/vite';
import react from '@vitejs/plugin-react';
import { defineConfig } from 'vite';

export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: { '@': fileURLToPath(new URL('./src', import.meta.url)) },
  },
  server: {
    // Both can be moved so several checkouts can run side by side: PORT=5183 API_TARGET=http://localhost:8010 pnpm dev
    port: Number(process.env.PORT ?? 5173),
    strictPort: true,
    proxy: { '/api': { target: process.env.API_TARGET ?? 'http://localhost:8000', changeOrigin: true } },
  },
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: ['./src/test/setup.ts'],
    css: true,
  },
});
