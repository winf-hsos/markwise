import { defineConfig } from "vite";
import { svelte } from "@sveltejs/vite-plugin-svelte";

// The build goes into the Python package, so that the app runs without Node.js.
// During development, /api is forwarded to `markwise serve` on 127.0.0.1:8765.
export default defineConfig({
  plugins: [svelte()],
  base: "./",
  build: { outDir: "../src/markwise/app/static", emptyOutDir: true },
  server: { port: 5173, strictPort: true, proxy: { "/api": "http://127.0.0.1:8765" } },
});
