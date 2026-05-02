import { useState } from "react";
import type { AskResponse } from "../../shared/api/api";
import { postAsk } from "../../shared/api/api";
import AskInput from "./AskInput";
import HistoryPanel from "./HistoryPanel";
import Thread, { type ThreadMessage } from "./Thread";
import TrustPanel from "./TrustPanel";

function makeId(prefix: string): string {
	return `${prefix}-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 8)}`;
}

export default function Chat() {
	const [messages, setMessages] = useState<ThreadMessage[]>([]);
	const [loading, setLoading] = useState(false);
	const [refreshKey, setRefreshKey] = useState(0);

	function appendUser(question: string) {
		setMessages((prev) => [
			...prev,
			{ id: makeId("u"), kind: "user", question, timestamp: Date.now() },
		]);
	}

	function appendAssistant(result: AskResponse) {
		setMessages((prev) => [
			...prev,
			{ id: makeId("a"), kind: "assistant", result, timestamp: Date.now() },
		]);
	}

	function appendError(message: string) {
		setMessages((prev) => [
			...prev,
			{ id: makeId("e"), kind: "error", message, timestamp: Date.now() },
		]);
	}

	async function handleAsk(question: string): Promise<void> {
		appendUser(question);
		setLoading(true);
		try {
			const res = await postAsk(question);
			appendAssistant(res);
			setRefreshKey((k) => k + 1);
		} catch (e) {
			appendError(e instanceof Error ? e.message : "Request failed");
		} finally {
			setLoading(false);
		}
	}

	function handleHistorySelect(result: AskResponse) {
		appendAssistant(result);
	}

	return (
		<div>
			<h1>Hughes AI</h1>
			<div style={{ display: "flex", gap: "2rem", marginTop: "1.5rem" }}>
				<div
					style={{
						flex: 2,
						display: "flex",
						flexDirection: "column",
						gap: "1rem",
					}}
				>
					<Thread messages={messages} />
					<AskInput onSubmit={handleAsk} loading={loading} />
				</div>
				<div style={{ flex: 1 }}>
					<HistoryPanel
						onSelect={handleHistorySelect}
						refreshKey={refreshKey}
					/>
					<TrustPanel />
				</div>
			</div>
		</div>
	);
}
