import { Drawer } from "@mantine/core";
import { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { colors, radii, spacing, typography } from "../../theme/tokens";
import { useGetHistoryListQuery } from "../history/api";

interface HistoryDrawerProps {
	opened: boolean;
	onClose: () => void;
}

function formatStamp(iso: string): string {
	try {
		const d = new Date(iso);
		return d.toLocaleString(undefined, {
			month: "short",
			day: "numeric",
			hour: "numeric",
			minute: "2-digit",
		});
	} catch {
		return iso;
	}
}

export default function HistoryDrawer({ opened, onClose }: HistoryDrawerProps) {
	const { data } = useGetHistoryListQuery({ kind: "ask" });
	const navigate = useNavigate();
	const [q, setQ] = useState("");
	const items = useMemo(() => {
		const list = data ?? [];
		const needle = q.trim().toLowerCase();
		if (needle === "") return list;
		return list.filter((x) => x.question.toLowerCase().includes(needle));
	}, [data, q]);

	return (
		<Drawer
			opened={opened}
			onClose={onClose}
			position="right"
			size={420}
			title="Conversation history"
		>
			<div
				style={{
					display: "flex",
					flexDirection: "column",
					gap: spacing[3],
					paddingBottom: spacing[6],
				}}
			>
				<input
					type="search"
					aria-label="Search history"
					placeholder="Search past questions…"
					value={q}
					onChange={(e) => setQ(e.target.value)}
					style={{
						padding: `${spacing[2]} ${spacing[3]}`,
						border: `1px solid ${colors.slate[200]}`,
						borderRadius: radii.md,
						fontSize: typography.size.sm,
						fontFamily: typography.fontFamily,
					}}
				/>
				{items.length === 0 ? (
					<p
						style={{
							margin: 0,
							color: colors.slate[500],
							fontSize: typography.size.sm,
						}}
					>
						No matching questions yet.
					</p>
				) : (
					<ul
						style={{
							listStyle: "none",
							padding: 0,
							margin: 0,
							display: "flex",
							flexDirection: "column",
							gap: spacing[2],
						}}
					>
						{items.map((item) => (
							<li key={item.id}>
								<button
									type="button"
									onClick={() => {
										onClose();
										navigate(`/intelligence?history=${item.id}`);
									}}
									style={{
										width: "100%",
										textAlign: "left",
										padding: `${spacing[3]} ${spacing[4]}`,
										border: `1px solid ${colors.slate[200]}`,
										borderRadius: radii.md,
										backgroundColor: colors.white,
										cursor: "pointer",
										fontFamily: typography.fontFamily,
									}}
								>
									<span
										style={{
											display: "block",
											fontSize: typography.size.sm,
											color: colors.slate[800],
											marginBottom: 2,
										}}
									>
										{item.question}
									</span>
									<span
										style={{
											fontSize: typography.size.xs,
											color: colors.slate[400],
										}}
									>
										{formatStamp(item.created_at)}
									</span>
								</button>
							</li>
						))}
					</ul>
				)}
			</div>
		</Drawer>
	);
}
