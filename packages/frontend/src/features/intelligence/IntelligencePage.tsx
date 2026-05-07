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
import { useEffect, useMemo } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { useAppDispatch, useAppSelector } from "../../shared/api/hooks";
import { colors, radii, spacing, typography } from "../../theme/tokens";
import {
	type ThreadMessageWire,
	useCreateThreadMutation,
	useGetThreadQuery,
	usePostMessageMutation,
} from "./api";
import ClarificationControl from "./components/ClarificationControl";
import ComposerInput from "./components/ComposerInput";
import MessageList from "./components/MessageList";
import ThinkingBubble from "./components/ThinkingBubble";
import ThreadRail from "./components/ThreadRail";
import {
	pendingQuestionCleared,
	pendingQuestionSubmitted,
	setCurrentThread,
} from "./threadSlice";

const layoutStyle: React.CSSProperties = {
	display: "flex",
	flexDirection: "row",
	position: "absolute",
	inset: 0,
	background: colors.white,
};

const mainStyle: React.CSSProperties = {
	display: "flex",
	flexDirection: "column",
	flex: 1,
	minWidth: 0,
	minHeight: 0,
};

const conversationStyle: React.CSSProperties = {
	flex: 1,
	overflowY: "auto",
	minHeight: 0,
};

const STARTER_QUESTIONS: readonly string[] = [
	"What's our loan-to-deposit ratio this month?",
	"Show deposit balance by branch as of the latest month.",
	"What's our origination volume this year?",
	"Top 5 deposit products by total balance.",
];

const emptyStateStyle: React.CSSProperties = {
	flex: 1,
	display: "flex",
	flexDirection: "column",
	alignItems: "center",
	justifyContent: "center",
	gap: spacing[4],
	padding: spacing[6],
	textAlign: "center",
};

const emptyHeadingStyle: React.CSSProperties = {
	fontSize: typography.size.xl,
	fontWeight: typography.weight.medium,
	color: colors.slate[800],
	margin: 0,
};

const emptySubheadStyle: React.CSSProperties = {
	fontSize: typography.size.sm,
	color: colors.slate[600],
	maxWidth: 480,
	margin: 0,
};

const suggestionsRowStyle: React.CSSProperties = {
	display: "grid",
	gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))",
	gap: spacing[2],
	width: "min(720px, 100%)",
	marginTop: spacing[2],
};

const suggestionButtonStyle: React.CSSProperties = {
	background: colors.white,
	color: colors.slate[800],
	border: `1px solid ${colors.slate[200]}`,
	borderRadius: radii.md,
	padding: `${spacing[3]} ${spacing[4]}`,
	cursor: "pointer",
	fontSize: typography.size.sm,
	fontFamily: typography.fontFamily,
	textAlign: "left",
	lineHeight: 1.4,
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
	const pendingQuestion = useAppSelector((s) => s.thread.pendingQuestion);

	const { data: thread } = useGetThreadQuery(threadId ?? skipToken);
	const [createThread] = useCreateThreadMutation();
	const [postMessage] = usePostMessageMutation();

	// Sync URL → slice so child components (composer, indicator) see it.
	useEffect(() => {
		dispatch(setCurrentThread(threadId));
	}, [threadId, dispatch]);

	async function handleSubmit(content: string): Promise<void> {
		let activeThreadId = threadId;
		// Optimistic UI: show the user's bubble immediately so the chat
		// doesn't feel dead while the network round-trips (HUG-201 A).
		dispatch(
			pendingQuestionSubmitted({ content, threadId: activeThreadId }),
		);
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
	// Hide the empty state once we know a question is pending — avoids the
	// brief flash where the page navigates to /intelligence/<id> but the
	// thread fetch hasn't returned yet (so messages.length is 0).
	const showEmptyState =
		!threadId && messages.length === 0 && pendingQuestion === null;

	// Pending bubble: only show while the persisted history doesn't yet
	// include the user's submitted message. RTK Query refetches `thread`
	// on stream close — the moment `messages` includes our pending content
	// we drop the bubble.
	const pendingUserContent = useMemo(() => {
		if (!pendingQuestion) return null;
		const matched = messages.some(
			(m) => m.role === "user" && m.content === pendingQuestion.content,
		);
		return matched ? null : pendingQuestion.content;
	}, [pendingQuestion, messages]);

	useEffect(() => {
		if (pendingQuestion && pendingUserContent === null) {
			dispatch(pendingQuestionCleared());
		}
	}, [pendingQuestion, pendingUserContent, dispatch]);

	// Animate only the most recent terminal answer (so re-renders /
	// scrolling existing threads don't re-type prior answers).
	const animatedTerminalId = useMemo(() => {
		for (let i = messages.length - 1; i >= 0; i--) {
			const m = messages[i];
			if (m.role === "tool") return m.message_id;
		}
		return null;
	}, [messages]);

	return (
		<div style={layoutStyle}>
			<ThreadRail currentThreadId={threadId} onNewThread={handleNewThread} />
			<div style={mainStyle}>
				<div style={conversationStyle}>
					{showEmptyState ? (
						<div style={emptyStateStyle}>
							<h2 style={emptyHeadingStyle}>Ask Hughes</h2>
							<p style={emptySubheadStyle}>
								Open-ended questions about loans, deposits, originations,
								delinquency, and portfolio performance.
							</p>
							<div style={suggestionsRowStyle}>
								{STARTER_QUESTIONS.map((q) => (
									<button
										key={q}
										type="button"
										style={suggestionButtonStyle}
										onClick={() => void handleSubmit(q)}
									>
										{q}
									</button>
								))}
							</div>
						</div>
					) : (
						<>
							<MessageList
								messages={messages}
								animatedTerminalId={animatedTerminalId}
								pendingUserContent={pendingUserContent}
							/>
							<div style={{ padding: spacing[3] }}>
								<ThinkingBubble />
							</div>
							<ClarificationControl
								message={clarifyMsg}
								onSubmit={(option) => void handleSubmit(option)}
							/>
						</>
					)}
				</div>
				<ComposerInput onSubmit={handleSubmit} disabled={streaming} />
			</div>
		</div>
	);
}
