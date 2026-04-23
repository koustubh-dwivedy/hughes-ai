import { useEffect, useState } from "react";
import type { AskResponse, HistorySummary } from "../lib/api";
import {
	getHistory,
	getHistoryDetail,
	historyDetailToAskResponse,
	postRerun,
} from "../lib/api";

interface Props {
	onSelect: (result: AskResponse) => void;
	refreshKey: number;
}

export default function HistoryPanel({ onSelect, refreshKey }: Props) {
	const [history, setHistory] = useState<HistorySummary[]>([]);

	// biome-ignore lint/correctness/useExhaustiveDependencies: refreshKey is a prop counter — changing it re-renders and re-runs this effect
	useEffect(() => {
		getHistory()
			.then(setHistory)
			.catch(() => {});
	}, [refreshKey]);

	async function handleView(id: string): Promise<void> {
		const detail = await getHistoryDetail(id);
		onSelect(historyDetailToAskResponse(detail));
	}

	async function handleRerun(id: string): Promise<void> {
		const result = await postRerun(id);
		onSelect(result);
		getHistory()
			.then(setHistory)
			.catch(() => {});
	}

	if (history.length === 0) return null;

	return (
		<aside>
			<h2>History</h2>
			<ul style={{ listStyle: "none", padding: 0, margin: 0 }}>
				{history.map((item) => (
					<li key={item.id} style={{ marginBottom: "0.75rem" }}>
						<button
							type="button"
							onClick={() => {
								void handleView(item.id);
							}}
							style={{ display: "block", textAlign: "left", width: "100%" }}
						>
							{item.question}
						</button>
						<small>{new Date(item.created_at).toLocaleString()}</small>{" "}
						<button
							type="button"
							onClick={() => {
								void handleRerun(item.id);
							}}
						>
							Rerun
						</button>
					</li>
				))}
			</ul>
		</aside>
	);
}
