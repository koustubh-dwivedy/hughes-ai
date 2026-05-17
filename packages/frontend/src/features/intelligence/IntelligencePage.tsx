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
import { useEffect, useMemo, useRef } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { useAppDispatch, useAppSelector } from "../../shared/api/hooks";
import { colors, spacing } from "../../theme/tokens";
import {
	type ThreadMessageWire,
	useCreateThreadMutation,
	useGetThreadQuery,
	usePostMessageMutation,
} from "./api";
import ClarificationControl from "./components/ClarificationControl";
import ComposerInput from "./components/ComposerInput";
import EmptyState from "./components/EmptyState";
import MessageList from "./components/MessageList";
import ThinkingBubble from "./components/ThinkingBubble";
import ThreadRail from "./components/ThreadRail";
import ResearchWorkspace from "./research/ResearchWorkspace";
import {
	pendingQuestionCleared,
	pendingQuestionRebound,
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
	const streamingThreadId = useAppSelector((s) => s.thread.streamingThreadId);
	const pendingQuestion = useAppSelector((s) => s.thread.pendingQuestion);
	// True iff the in-flight stream belongs to the thread the user is
	// currently viewing. Used to gate the auto-scroll triggers and the
	// optimistic pending-bubble. Without this gate, switching to a
	// different thread mid-stream made the source-thread's streaming
	// UI disappear (because setCurrentThread used to wipe buffers).
	const liveOnThisThread = streaming && streamingThreadId === threadId;
	const conversationRef = useRef<HTMLDivElement | null>(null);
	// True iff the user was scrolled to (or near) the bottom of the
	// conversation *before* the most recent re-render. We sample this
	// in a layout-phase effect so that the subsequent commit-phase
	// auto-scroll only fires when the user is following the live tail —
	// it never yanks someone who scrolled up to re-read history.
	const wasAtBottomRef = useRef(true);

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
		dispatch(pendingQuestionSubmitted({ content, threadId: activeThreadId }));
		if (!activeThreadId) {
			const created = await createThread({}).unwrap();
			activeThreadId = created.thread_id;
			// Rebind the pendingQuestion (dispatched above with threadId=null)
			// to the real thread id. Without this, a later "+ New thread"
			// click would return the user to /intelligence (threadId=null)
			// where the still-null-scoped pending falsely matches the view
			// and suppresses the starter screen.
			dispatch(pendingQuestionRebound({ threadId: activeThreadId }));
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

	// Guard against RTK Query returning the previously-cached thread's data
	// during the brief moment after navigating to `/intelligence` (no id),
	// where `thread` may still hold the previous fetch's payload before the
	// hook re-evaluates against `skipToken`. Without this guard the old
	// answer flickers back into view after clicking "+ New thread".
	const messages = threadId ? (thread?.messages ?? []) : [];
	const clarifyMsg = lastClarifyMessage(messages);
	// Hide the empty state when WE are in the middle of creating a thread
	// from the starter-question flow — `pendingQuestion.threadId === null`
	// means the user just clicked a starter from `/intelligence` and we're
	// about to navigate to the new thread URL. Don't hide for a stale
	// pending from a different thread (e.g. user clicked "+ New thread"
	// while another thread is streaming): in that case we want the empty
	// state to show on `/intelligence` so the user has somewhere to land.
	const pendingForThisView =
		pendingQuestion !== null && pendingQuestion.threadId === null;
	const showEmptyState =
		!threadId && messages.length === 0 && !pendingForThisView;

	// Pending bubble: only show on the thread that submitted it and
	// only while the persisted history doesn't yet include the user's
	// message. RTK Query refetches `thread` on stream close — the
	// moment `messages` includes our pending content we drop the
	// bubble. The threadId filter prevents A's optimistic bubble from
	// surfacing on thread B if the user switches mid-stream.
	const pendingUserContent = useMemo(() => {
		if (!pendingQuestion) return null;
		if (pendingQuestion.threadId !== threadId) return null;
		const matched = messages.some(
			(m) => m.role === "user" && m.content === pendingQuestion.content,
		);
		return matched ? null : pendingQuestion.content;
	}, [pendingQuestion, messages, threadId]);

	useEffect(() => {
		// Only clear the pendingQuestion once its source thread has
		// caught up — i.e. we're viewing it AND its persisted user-row
		// has landed. Wrong-thread views keep the question alive so the
		// bubble reappears when the user returns to the source thread.
		if (
			pendingQuestion &&
			pendingQuestion.threadId === threadId &&
			pendingUserContent === null
		) {
			dispatch(pendingQuestionCleared());
		}
	}, [pendingQuestion, pendingUserContent, threadId, dispatch]);

	// USER-INITIATED auto-scroll. When the user submits a new turn the
	// `liveOnThisThread` flag flips false→true and `pendingUserContent`
	// flips null→set. Both signal the user wants to follow the new
	// turn; always pin to the tail, regardless of where their scroll
	// was. The live flag (vs the bare `streaming`) also makes the
	// bubble auto-scroll into view when the user *returns* to a thread
	// whose stream is still alive after they had clicked away.
	const prevLiveRef = useRef(liveOnThisThread);
	const prevPendingRef = useRef(pendingUserContent);
	useEffect(() => {
		const el = conversationRef.current;
		if (!el) return;
		const liveStarted = liveOnThisThread && !prevLiveRef.current;
		const pendingArrived =
			pendingUserContent !== null && prevPendingRef.current === null;
		prevLiveRef.current = liveOnThisThread;
		prevPendingRef.current = pendingUserContent;
		if (liveStarted || pendingArrived) {
			el.scrollTop = el.scrollHeight;
		}
	}, [liveOnThisThread, pendingUserContent]);

	// PASSIVE auto-scroll. New persisted messages can arrive mid-turn
	// (e.g. when the SSE close triggers a refetch). Only follow the
	// tail if the user is already there; never yank them down if
	// they're reading earlier history.
	// biome-ignore lint/correctness/useExhaustiveDependencies: messages.length is a trigger signal; we don't read its value inside the effect.
	useEffect(() => {
		const el = conversationRef.current;
		if (!el) return;
		if (!wasAtBottomRef.current) return;
		el.scrollTop = el.scrollHeight;
	}, [messages.length]);

	function handleScroll(): void {
		const el = conversationRef.current;
		if (!el) return;
		// 40 px of slack so the user doesn't have to land exactly on
		// the bottom edge to stay anchored to the tail.
		wasAtBottomRef.current =
			el.scrollTop + el.clientHeight >= el.scrollHeight - 40;
	}

	return (
		<div style={layoutStyle}>
			<ThreadRail currentThreadId={threadId} onNewThread={handleNewThread} />
			<div style={mainStyle}>
				<div
					ref={conversationRef}
					onScroll={handleScroll}
					style={conversationStyle}
					data-testid="conversation-pane"
				>
					{showEmptyState ? (
						<EmptyState onSelect={(q) => void handleSubmit(q)} />
					) : (
						<>
							<MessageList
								messages={messages}
								pendingUserContent={pendingUserContent}
							/>
							{threadId ? <ResearchWorkspace threadId={threadId} /> : null}
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
				<ComposerInput onSubmit={handleSubmit} disabled={liveOnThisThread} />
			</div>
		</div>
	);
}
