import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import type { AskResponse } from "../../shared/api/api";
import { historyDetailToAskResponse } from "../../shared/api/api";
import log from "../../shared/lib/logger";
import { useGetHistoryDetailQuery } from "../history/api";
import AskInput from "./AskInput";
import Thread, { type ThreadMessage } from "./Thread";
import TrustPanel from "./TrustPanel";
import { usePostAskMutation } from "./api";
import SuggestedPrompts from "./messages/SuggestedPrompts";

function makeId(prefix: string): string {
	return `${prefix}-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 8)}`;
}

export default function Chat() {
	const [messages, setMessages] = useState<ThreadMessage[]>([]);
	const [searchParams, setSearchParams] = useSearchParams();
	const historyId = searchParams.get("history");
	const [postAsk, { isLoading: loading }] = usePostAskMutation();
	const { data: historyDetail, error: historyError } = useGetHistoryDetailQuery(
		historyId ?? "",
		{ skip: !historyId },
	);

	function appendUser(question: string) {
		setMessages((prev) => [
			...prev,
			{ id: makeId("u"), kind: "user", question, timestamp: Date.now() },
		]);
	}

	function appendAssistant(result: AskResponse, streaming = true) {
		setMessages((prev) => [
			...prev,
			{
				id: makeId("a"),
				kind: "assistant",
				result,
				timestamp: Date.now(),
				streaming,
			},
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
		try {
			const res = await postAsk({ question }).unwrap();
			appendAssistant(res);
		} catch (e) {
			appendError(e instanceof Error ? e.message : "Request failed");
		}
	}

	useEffect(() => {
		if (!historyDetail) {
			if (historyError) {
				log.warn({ err: String(historyError) }, "history_load_failed");
			}
			return;
		}
		const now = Date.now();
		const detail = historyDetail;
		setMessages((prev) => [
			...prev,
			{
				id: makeId("u"),
				kind: "user",
				question: detail.question,
				timestamp: now,
			},
			{
				id: makeId("a"),
				kind: "assistant",
				result: historyDetailToAskResponse(detail),
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
	}, [historyDetail, historyError, setSearchParams]);

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
