import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import type { AskResponse } from "../../shared/api/api";
import {
	getHistoryDetail,
	historyDetailToAskResponse,
	postAsk,
} from "../../shared/api/api";
import log from "../../shared/lib/logger";
import AskInput from "./AskInput";
import Thread, { type ThreadMessage } from "./Thread";
import TrustPanel from "./TrustPanel";
import SuggestedPrompts from "./messages/SuggestedPrompts";

function makeId(prefix: string): string {
	return `${prefix}-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 8)}`;
}

export default function Chat() {
	const [messages, setMessages] = useState<ThreadMessage[]>([]);
	const [loading, setLoading] = useState(false);
	const [searchParams, setSearchParams] = useSearchParams();
	const historyId = searchParams.get("history");

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
		} catch (e) {
			appendError(e instanceof Error ? e.message : "Request failed");
		} finally {
			setLoading(false);
		}
	}

	useEffect(() => {
		if (!historyId) return;
		getHistoryDetail(historyId)
			.then((d) => {
				const now = Date.now();
				setMessages((prev) => [
					...prev,
					{
						id: makeId("u"),
						kind: "user",
						question: d.question,
						timestamp: now,
					},
					{
						id: makeId("a"),
						kind: "assistant",
						result: historyDetailToAskResponse(d),
						timestamp: now,
						streaming: false,
					},
				]);
				setSearchParams(
					(prev) => {
						prev.delete("history");
						return prev;
					},
					{ replace: true },
				);
			})
			.catch((err: unknown) => {
				log.warn(
					{ err: err instanceof Error ? err.message : String(err) },
					"history_load_failed",
				);
			});
	}, [historyId, setSearchParams]);

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
					{messages.length === 0 ? (
						<SuggestedPrompts onSelect={(p) => void handleAsk(p)} />
					) : (
						<Thread messages={messages} />
					)}
					<AskInput onSubmit={handleAsk} loading={loading} />
				</div>
				<div style={{ flex: 1 }}>
					<TrustPanel />
				</div>
			</div>
		</div>
	);
}
