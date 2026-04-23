import { useState } from "react";
import AskInput from "./components/AskInput";
import ResultPanel from "./components/ResultPanel";
import type { AskResponse } from "./lib/api";
import { postAsk } from "./lib/api";

export default function App() {
	const [result, setResult] = useState<AskResponse | null>(null);
	const [error, setError] = useState<string | null>(null);
	const [loading, setLoading] = useState(false);

	async function handleAsk(question: string): Promise<void> {
		setLoading(true);
		setError(null);
		try {
			const res = await postAsk(question);
			setResult(res);
		} catch (e) {
			setError(e instanceof Error ? e.message : "Request failed");
		} finally {
			setLoading(false);
		}
	}

	return (
		<main style={{ maxWidth: 800, margin: "0 auto", padding: "2rem" }}>
			<h1>Hughes AI</h1>
			<AskInput onSubmit={handleAsk} loading={loading} />
			{error !== null && (
				<p role="alert" style={{ color: "red" }}>
					{error}
				</p>
			)}
			{result !== null && <ResultPanel result={result} />}
		</main>
	);
}
