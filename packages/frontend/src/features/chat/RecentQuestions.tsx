import { useNavigate } from "react-router-dom";
import { useGetHistoryListQuery } from "../history/api";
import { colors, radii, spacing, typography } from "../../theme/tokens";

interface RecentQuestionsProps {
	limit?: number;
}

const wrapperStyle: React.CSSProperties = {
	padding: spacing[4],
	display: "flex",
	flexDirection: "column",
	gap: spacing[3],
};

const headingStyle: React.CSSProperties = {
	margin: 0,
	fontSize: typography.size.sm,
	fontWeight: typography.weight.medium,
	color: colors.slate[600],
};

const itemStyle: React.CSSProperties = {
	display: "flex",
	alignItems: "center",
	justifyContent: "space-between",
	gap: spacing[3],
	padding: `${spacing[3]} ${spacing[4]}`,
	background: colors.white,
	border: `1px solid ${colors.slate[200]}`,
	borderRadius: radii.lg,
	cursor: "pointer",
	fontSize: typography.size.sm,
	color: colors.slate[800],
	textAlign: "left",
	fontFamily: typography.fontFamily,
};

function formatTimestamp(iso: string): string {
	try {
		const d = new Date(iso);
		const now = new Date();
		const sameDay = d.toDateString() === now.toDateString();
		if (sameDay) {
			return d.toLocaleTimeString(undefined, {
				hour: "numeric",
				minute: "2-digit",
			});
		}
		return d.toLocaleDateString(undefined, { month: "short", day: "numeric" });
	} catch {
		return "";
	}
}

export default function RecentQuestions({ limit = 5 }: RecentQuestionsProps) {
	const navigate = useNavigate();
	const { data } = useGetHistoryListQuery({ kind: "ask" });
	const items = (data ?? []).slice(0, limit);
	if (items.length === 0) return null;
	return (
		<section aria-label="Recent questions" style={wrapperStyle}>
			<h3 style={headingStyle}>Recent questions</h3>
			<div
				style={{
					display: "flex",
					flexDirection: "column",
					gap: spacing[2],
				}}
			>
				{items.map((q) => (
					<button
						type="button"
						key={q.id}
						onClick={() => navigate(`/intelligence?history=${q.id}`)}
						style={itemStyle}
					>
						<span
							style={{
								overflow: "hidden",
								textOverflow: "ellipsis",
								whiteSpace: "nowrap",
								flex: 1,
							}}
						>
							{q.question}
						</span>
						<span
							style={{
								fontSize: typography.size.xs,
								color: colors.slate[400],
								flexShrink: 0,
							}}
						>
							{formatTimestamp(q.created_at)}
						</span>
					</button>
				))}
			</div>
		</section>
	);
}
