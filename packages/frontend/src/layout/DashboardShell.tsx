import type { ReactNode } from "react";
import { useDashboardContext } from "../shared/context/DashboardContext";
import { colors, spacing, typography } from "../theme/tokens";
import ErrorBoundary from "../ui/primitives/ErrorBoundary";

interface DashboardShellProps {
	title: string;
	as_of_date?: string;
	loading?: boolean;
	error?: string | null;
	empty?: boolean;
	children: ReactNode;
}

/**
 * @example
 * <DashboardShell title="Deposit Portfolio" as_of_date="2024-03-31" loading={isLoading} error={err}>
 *   <KpiTile label="Total Balance" value="$142M" />
 * </DashboardShell>
 */
export default function DashboardShell({
	title,
	as_of_date,
	loading = false,
	error = null,
	empty = false,
	children,
}: DashboardShellProps) {
	const { asOfDate: contextDate } = useDashboardContext();
	const displayDate = as_of_date ?? contextDate;
	return (
		<section aria-labelledby="shell-title">
			<header
				style={{
					display: "flex",
					alignItems: "baseline",
					gap: spacing[4],
					marginBottom: spacing[6],
					borderBottom: `1px solid ${colors.slate[200]}`,
					paddingBottom: spacing[3],
				}}
			>
				<h2
					id="shell-title"
					style={{
						margin: 0,
						fontSize: typography.size.xl,
						fontWeight: typography.weight.semibold,
						color: colors.slate[900],
					}}
				>
					{title}
				</h2>
				{displayDate && (
					<span
						style={{
							fontSize: typography.size.xs,
							color: colors.slate[500],
						}}
					>
						As of {displayDate}
					</span>
				)}
			</header>

			{loading && (
				<output
					aria-label="loading dashboard"
					style={{
						display: "block",
						padding: spacing[8],
						textAlign: "center",
						color: colors.slate[400],
						fontSize: typography.size.sm,
					}}
				>
					Loading…
				</output>
			)}

			{!loading && error !== null && error !== undefined && (
				<div
					role="alert"
					style={{
						padding: spacing[4],
						backgroundColor: "#fef2f2",
						border: "1px solid #fecaca",
						borderRadius: "0.5rem",
						color: "#dc2626",
						fontSize: typography.size.sm,
					}}
				>
					{error}
				</div>
			)}

			{!loading && !error && empty && (
				<p
					style={{
						color: colors.slate[400],
						fontSize: typography.size.sm,
						textAlign: "center",
						padding: spacing[8],
					}}
				>
					No data available.
				</p>
			)}

			{!loading && !error && !empty && (
				<ErrorBoundary>{children}</ErrorBoundary>
			)}
		</section>
	);
}
