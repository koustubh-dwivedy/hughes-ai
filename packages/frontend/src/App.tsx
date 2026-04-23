import { useState } from "react";
import AskInput from "./components/AskInput";
import HistoryPanel from "./components/HistoryPanel";
import ResultPanel from "./components/ResultPanel";
import TrustPanel from "./components/TrustPanel";
import type { AskResponse } from "./lib/api";
import { postAsk } from "./lib/api";

export default function App() {
	const [result, setResult] = useState<AskResponse | null>(null);
	const [error, setError] = useState<string | null>(null);
	const [loading, setLoading] = useState(false);
	const [refreshKey, setRefreshKey] = useState(0);

	async function handleAsk(question: string): Promise<void> {
		setLoading(true);
		setError(null);
		try {
			const res = await postAsk(question);
			setResult(res);
			setRefreshKey((k) => k + 1);
		} catch (e) {
			setError(e instanceof Error ? e.message : "Request failed");
		} finally {
			setLoading(false);
		}
	}

	return (
		<main style={{ maxWidth: 1100, margin: "0 auto", padding: "2rem" }}>
			<h1>Hughes AI</h1>
			<AskInput onSubmit={handleAsk} loading={loading} />
			{error !== null && (
				<p role="alert" style={{ color: "red" }}>
					{error}
				</p>
			)}
			<div style={{ display: "flex", gap: "2rem", marginTop: "1.5rem" }}>
				<div style={{ flex: 2 }}>
					{result !== null && <ResultPanel result={result} />}
				</div>
				<div style={{ flex: 1 }}>
					<HistoryPanel onSelect={setResult} refreshKey={refreshKey} />
					<TrustPanel />
				</div>
			</div>
		</main>
	);
}
