/**
 * Thread-aware conversational page at /intelligence (HUG-179).
 *
 * Two URL shapes:
 *   /intelligence              — empty state. First send creates a
 *                                thread and navigates to its URL.
 *   /intelligence/:threadId    — hydrated from useGetThreadQuery.
 *
 * Renders ThreadRail + MessageList + StepIndicator +
 * ClarificationControl (when applicable) + ComposerInput. The ordering
 * is right-pane = conversation; left-pane = thread navigation.
 */

import { skipToken } from "@reduxjs/toolkit/query";
import { useEffect } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { useAppDispatch, useAppSelector } from "../../shared/api/hooks";
import { colors } from "../../theme/tokens";
import {
	type ThreadMessageWire,
	useCreateThreadMutation,
	useGetThreadQuery,
	usePostMessageMutation,
} from "./api";
import ClarificationControl from "./components/ClarificationControl";
import ComposerInput from "./components/ComposerInput";
import MessageList from "./components/MessageList";
import StepIndicator from "./components/StepIndicator";
import ThreadRail from "./components/ThreadRail";
import { setCurrentThread } from "./threadSlice";

const layoutStyle: React.CSSProperties = {
	display: "flex",
	flexDirection: "row",
	height: "100%",
	minHeight: "calc(100vh - 64px)",
	background: colors.white,
};

const mainStyle: React.CSSProperties = {
	display: "flex",
	flexDirection: "column",
	flex: 1,
	minWidth: 0,
};

const conversationStyle: React.CSSProperties = {
	flex: 1,
	overflowY: "auto",
};

function lastClarifyMessage(
	messages: ThreadMessageWire[],
): ThreadMessageWire | null {
	for (let i = messages.length - 1; i >= 0; i--) {
		const msg = messages[i];
		if (msg.role !== "tool") continue;
		const results = msg.tool_results;
		if (!results || results.length === 0) continue;
		const first = results[0] as { name?: string };
		if (first.name === "clarify") return msg;
		// Once we hit a non-clarify terminal, stop — older clarifications
		// have been resolved.
		if (first.name === "final_answer") return null;
	}
	return null;
}

export default function IntelligencePage() {
	const params = useParams<{ threadId?: string }>();
	const navigate = useNavigate();
	const dispatch = useAppDispatch();

	const threadId = params.threadId ?? null;
	const streaming = useAppSelector((s) => s.thread.streaming);

	const { data: thread } = useGetThreadQuery(threadId ?? skipToken);
	const [createThread] = useCreateThreadMutation();
	const [postMessage] = usePostMessageMutation();

	// Sync URL → slice so child components (composer, indicator) see it.
	useEffect(() => {
		dispatch(setCurrentThread(threadId));
	}, [threadId, dispatch]);

	async function handleSubmit(content: string): Promise<void> {
		let activeThreadId = threadId;
		if (!activeThreadId) {
			const created = await createThread({}).unwrap();
			activeThreadId = created.thread_id;
			navigate(`/intelligence/${activeThreadId}`, { replace: true });
		}
		// Fire and forget — the queryFn dispatches step/final into the
		// slice as the stream progresses; awaiting unwrap() is fine but
		// not required for correctness.
		void postMessage({ threadId: activeThreadId, content });
	}

	function handleNewThread(): void {
		navigate("/intelligence");
		dispatch(setCurrentThread(null));
	}

	const messages = thread?.messages ?? [];
	const clarifyMsg = lastClarifyMessage(messages);

	return (
		<div style={layoutStyle}>
			<ThreadRail currentThreadId={threadId} onNewThread={handleNewThread} />
			<div style={mainStyle}>
				<div style={conversationStyle}>
					<MessageList messages={messages} />
					<StepIndicator />
					<ClarificationControl
						message={clarifyMsg}
						onSubmit={(option) => void handleSubmit(option)}
					/>
				</div>
				<ComposerInput onSubmit={handleSubmit} disabled={streaming} />
			</div>
		</div>
	);
}
