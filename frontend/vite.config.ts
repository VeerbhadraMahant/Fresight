import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Dev proxies /api to the backend. In production the app talks to the API via
// VITE_API_BASE (build-time) or a reverse proxy that routes /api (see nginx.conf).
const API_TARGET = process.env.VITE_DEV_API ?? "http://127.0.0.1:8000";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": { target: API_TARGET, changeOrigin: true },
    },
  },
  build: {
    // recharts (~550 KB) is the bulk; split it so app code stays cacheable
    chunkSizeWarningLimit: 900,
    rollupOptions: {
      output: {
        manualChunks: { charts: ["recharts"] },
      },
    },
  },
});
