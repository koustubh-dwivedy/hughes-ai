import { Drawer } from "@mantine/core";
import { useState } from "react";
import type { TrustResponse } from "../../shared/api/api";
import { colors, spacing, typography } from "../../theme/tokens";
import { useGetTrustQuery } from "./api";

function formatDate(isoDate: string): string {
	try {
		const d = new Date(isoDate);
		return d.toLocaleString("en-US", {
			month: "short",
			day: "numeric",
			hour: "2-digit",
			minute: "2-digit",
			hour12: false,
		});
	} catch {
		return isoDate;
	}
}

interface TrustSheetProps {
	trust: TrustResponse;
	opened: boolean;
	onClose: () => void;
}

function TrustSheet({ trust, opened, onClose }: TrustSheetProps) {
	const matchPct = (trust.reconciliation_match_rate * 100).toFixed(1);

	return (
		<Drawer
			opened={opened}
			onClose={onClose}
			position="bottom"
			size="auto"
			title="Data trust & freshness"
			aria-label="Trust details"
		>
			<div style={{ padding: spacing[4] }}>
				<p
					style={{
						margin: `0 0 ${spacing[2]}`,
						fontSize: typography.size.sm,
						color: colors.slate[700],
					}}
				>
					Origence records:{" "}
					<strong>{trust.origence_row_count.toLocaleString()}</strong>
				</p>
				<p
					style={{
						margin: `0 0 ${spacing[2]}`,
						fontSize: typography.size.sm,
						color: colors.slate[700],
					}}
				>
					Symitar records:{" "}
					<strong>{trust.symitar_row_count.toLocaleString()}</strong>
				</p>
				<p
					style={{
						margin: `0 0 ${spacing[2]}`,
						fontSize: typography.size.sm,
						color: colors.slate[700],
					}}
				>
					Reconciliation match rate: <strong>{matchPct}%</strong>
				</p>
				{trust.known_caveats.length > 0 && (
					<details style={{ marginTop: spacing[3] }}>
						<summary
							style={{
								cursor: "pointer",
								fontSize: typography.size.sm,
								color: colors.slate[600],
								fontWeight: typography.weight.medium,
							}}
						>
							Known caveats ({trust.known_caveats.length})
						</summary>
						<ul style={{ marginTop: spacing[2], paddingLeft: spacing[4] }}>
							{trust.known_caveats.map((c) => (
								<li
									key={c}
									style={{
										fontSize: typography.size.sm,
										color: colors.slate[600],
									}}
								>
									{c}
								</li>
							))}
						</ul>
					</details>
				)}
			</div>
		</Drawer>
	);
}

export default function TrustFooter() {
	const { data: trust } = useGetTrustQuery();
	const [sheetOpen, setSheetOpen] = useState(false);

	if (!trust) return null;

	const matchPct = (trust.reconciliation_match_rate * 100).toFixed(1);
	const caveatCount = trust.known_caveats.length;
	const asOf = trust.as_of_date ? formatDate(trust.as_of_date) : undefined;

	return (
		<>
			<footer aria-label="Data trust">
				<button
					type="button"
					aria-label="Open trust details"
					onClick={() => setSheetOpen(true)}
					style={{
						width: "100%",
						height: 40,
						display: "flex",
						alignItems: "center",
						justifyContent: "center",
						backgroundColor: colors.slate[800],
						color: colors.slate[300],
						fontSize: typography.size.xs,
						gap: spacing[3],
						cursor: "pointer",
						border: "none",
						fontFamily: typography.fontFamily,
					}}
				>
					<span style={{ color: "#4ade80" }}>✓</span>
					{asOf && <span>Data fresh as of {asOf}</span>}
					{asOf && <span>·</span>}
					<span>{matchPct}% reconciliation match</span>
					{caveatCount > 0 && (
						<>
							<span>·</span>
							<span>
								{caveatCount} caveat{caveatCount !== 1 ? "s" : ""}{" "}
								<span aria-hidden="true">ⓘ</span>
							</span>
						</>
					)}
				</button>
			</footer>
			{sheetOpen && (
				<TrustSheet
					trust={trust}
					opened={sheetOpen}
					onClose={() => setSheetOpen(false)}
				/>
			)}
		</>
	);
}
