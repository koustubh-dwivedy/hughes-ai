export default async function globalSetup(): Promise<void> {
	// Use 127.0.0.1 — Node 18 fetch resolves "localhost" to ::1 (IPv6) but
	// uvicorn binds IPv4 only by default, causing ECONNREFUSED.
	const url = process.env.API_URL ?? "http://127.0.0.1:8000";
	try {
		const res = await fetch(`${url}/health`);
		if (!res.ok) throw new Error(`HTTP ${res.status}`);
	} catch (err) {
		throw new Error(
			`\n\nAPI at ${url} is not reachable (${err}).\n` +
				"Start the full stack first:\n" +
				"  make dev          # Docker: Postgres, Redis, Vector\n" +
				"  make seed         # load synthetic data (once)\n" +
				"  cd packages/api && uvicorn api.main:app --reload\n\n",
		);
	}
}
