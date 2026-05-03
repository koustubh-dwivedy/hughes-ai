import { useEffect, useRef, useState } from "react";
import { useSearchParams } from "react-router-dom";
import type { AskResponse } from "../../shared/api/api";
import { historyDetailToAskResponse } from "../../shared/api/api";
import log from "../../shared/lib/logger";
import { useGetHistoryDetailQuery } from "../history/api";
import AskInput from "./AskInput";
import HistoryDrawer from "./HistoryDrawer";
import RecentQuestions from "./RecentQuestions";
import Thread, { type ThreadMessage } from "./Thread";
import { usePostAskMutation } from "./api";
import SuggestedPrompts from "./messages/SuggestedPrompts";

function makeId(prefix: string): string {
	return `${prefix}-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 8)}`;
}

function formatAskError(err: unknown): string {
	if (err && typeof err === "object" && "status" in err) {
		const status = (err as { status: unknown }).status;
		if (typeof status === "number") return `HTTP ${status}`;
		if (status === "FETCH_ERROR") return "Network error";
		return "Request failed";
	}
	return err instanceof Error ? err.message : "Request failed";
}

export default function Chat() {
	const [messages, setMessages] = useState<ThreadMessage[]>([]);
	const [historyOpen, setHistoryOpen] = useState(false);
	const [searchParams, setSearchParams] = useSearchParams();
	const historyId = searchParams.get("history");
	const [postAsk, { isLoading: loading }] = usePostAskMutation();
	const { data: historyDetail, error: historyError } = useGetHistoryDetailQuery(
		historyId ?? "",
		{ skip: !historyId },
	);
	const loadedHistoryIdRef = useRef<string | null>(null);

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
			appendError(formatAskError(e));
		}
	}

	useEffect(() => {
		if (!historyDetail) {
			if (historyError) {
				log.warn({ err: String(historyError) }, "history_load_failed");
			}
			return;
		}
		const detailId = String(historyDetail.id);
		if (loadedHistoryIdRef.current === detailId) return;
		loadedHistoryIdRef.current = detailId;
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
		<div
			style={{
				display: "flex",
				flexDirection: "column",
				gap: "1rem",
				maxWidth: 960,
				margin: "0 auto",
			}}
		>
			{messages.length === 0 ? (
				<>
					<SuggestedPrompts onSelect={(p) => void handleAsk(p)} />
					<RecentQuestions />
				</>
			) : (
				<Thread messages={messages} />
			)}
			<AskInput
				onSubmit={handleAsk}
				loading={loading}
				onOpenHistory={() => setHistoryOpen(true)}
			/>
			<HistoryDrawer
				opened={historyOpen}
				onClose={() => setHistoryOpen(false)}
			/>
		</div>
	);
}
