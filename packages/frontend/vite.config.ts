import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

export default defineConfig({
	plugins: [react()],
	server: {
		proxy: {
			"/api": {
				target: "http://127.0.0.1:8000",
				rewrite: (path: string) => path.replace(/^\/api/, ""),
			},
		},
	},
	test: {
		environment: "jsdom",
		setupFiles: ["./src/test/setup.ts"],
		globals: true,
		include: ["src/test/**/*.test.{ts,tsx}", "src/**/__tests__/**/*.test.{ts,tsx}"],
	},
});
