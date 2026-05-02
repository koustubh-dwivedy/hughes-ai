import { useEffect, useRef } from "react";
import type { AskResponse } from "../../shared/api/api";
import { colors, spacing } from "../../theme/tokens";
import AssistantMessage from "./AssistantMessage";
import DaySeparator from "./DaySeparator";
import UserMessage from "./UserMessage";

export type ThreadMessage =
	| { id: string; kind: "user"; question: string; timestamp: number }
	| {
			id: string;
			kind: "assistant";
			result: AskResponse;
			timestamp: number;
			streaming?: boolean;
	  }
	| { id: string; kind: "error"; message: string; timestamp: number };

interface Props {
	messages: ThreadMessage[];
}

const containerStyle: React.CSSProperties = {
	display: "flex",
	flexDirection: "column",
	gap: spacing[3],
	padding: spacing[4],
	overflowY: "auto",
	maxHeight: "60vh",
	background: colors.slate[50],
	borderRadius: 8,
	border: `1px solid ${colors.slate[200]}`,
};

const errorStyle: React.CSSProperties = {
	alignSelf: "flex-start",
	padding: spacing[3],
	color: "#b91c1c",
	background: "#fef2f2",
	border: "1px solid #fecaca",
	borderRadius: 6,
	fontSize: "0.875rem",
};

function dateKey(ts: number): string {
	return new Date(ts).toISOString().slice(0, 10);
}

export default function Thread({ messages }: Props) {
	const scrollRef = useRef<HTMLDivElement | null>(null);

	const messageCount = messages.length;
	useEffect(() => {
		const el = scrollRef.current;
		if (el && messageCount > 0) el.scrollTop = el.scrollHeight;
	}, [messageCount]);

	let lastDate = "";
	return (
		<div
			ref={scrollRef}
			role="log"
			aria-label="Conversation"
			aria-live="polite"
			// biome-ignore lint/a11y/noNoninteractiveTabindex: scrollable region needs a focusable handle so keyboard users can pan the log (axe scrollable-region-focusable)
			tabIndex={0}
			style={containerStyle}
		>
			{messages.map((m) => {
				const dk = dateKey(m.timestamp);
				const showSeparator = dk !== lastDate;
				lastDate = dk;
				return (
					<div key={m.id} style={{ display: "contents" }}>
						{showSeparator && <DaySeparator dateKey={dk} />}
						{m.kind === "user" && (
							<UserMessage question={m.question} timestamp={m.timestamp} />
						)}
						{m.kind === "assistant" && (
							<AssistantMessage
								result={m.result}
								timestamp={m.timestamp}
								streaming={m.streaming ?? true}
							/>
						)}
						{m.kind === "error" && (
							<p role="alert" style={errorStyle}>
								{m.message}
							</p>
						)}
					</div>
				);
			})}
		</div>
	);
}
