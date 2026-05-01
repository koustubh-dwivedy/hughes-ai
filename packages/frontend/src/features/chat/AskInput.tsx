import { useState } from "react";

interface Props {
	onSubmit: (question: string) => void;
	loading: boolean;
}

export default function AskInput({ onSubmit, loading }: Props) {
	const [value, setValue] = useState("");

	function handleSubmit(e: React.FormEvent) {
		e.preventDefault();
		const q = value.trim();
		if (q) onSubmit(q);
	}

	return (
		<form onSubmit={handleSubmit} style={{ display: "flex", gap: "0.5rem" }}>
			<input
				value={value}
				onChange={(e) => setValue(e.target.value)}
				placeholder="Ask a question about lending…"
				disabled={loading}
				style={{ flex: 1, padding: "0.5rem" }}
			/>
			<button type="submit" disabled={loading || value.trim() === ""}>
				{loading ? "Loading…" : "Ask"}
			</button>
		</form>
	);
}
