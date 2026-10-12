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
  },
});
