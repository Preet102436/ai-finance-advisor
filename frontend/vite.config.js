import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    // Vite's dev server rejects requests whose Host header isn't localhost
    // by default (DNS-rebinding protection). A leading-dot entry allows
    // that domain and all its subdomains, which is what a Cloudflare quick
    // tunnel (cloudflared tunnel --url ...) uses - a fresh random
    // *.trycloudflare.com subdomain each run. Remove this once you no
    // longer need to share the app over a tunnel.
    allowedHosts: [".trycloudflare.com"],
    // The frontend calls the backend at /api/... (see src/lib/apiClient.js),
    // and the dev server forwards those to FastAPI on port 8000, so the
    // browser only ever talks to one origin (no CORS setup needed).
    proxy: {
      "/api": {
        target: "http://127.0.0.1:8000",
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, ""),
      },
    },
  },
});
