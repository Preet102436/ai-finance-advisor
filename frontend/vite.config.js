import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
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
