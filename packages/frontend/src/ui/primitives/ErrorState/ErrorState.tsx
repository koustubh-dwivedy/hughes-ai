import { colors, radii, spacing, typography } from "../../../theme/tokens";

export interface ErrorStateProps {
	message: string;
	onRetry?: () => void;
	title?: string;
}

function WarningIcon() {
	return (
		<svg
			width="40"
			height="40"
			viewBox="0 0 24 24"
			fill="none"
			stroke="#dc2626"
			strokeWidth={2}
			strokeLinecap="round"
			strokeLinejoin="round"
			aria-hidden="true"
		>
			<path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z" />
			<line x1="12" y1="9" x2="12" y2="13" />
			<line x1="12" y1="17" x2="12.01" y2="17" />
		</svg>
	);
}

export default function ErrorState({
	message,
	onRetry,
	title = "Something went wrong",
}: ErrorStateProps) {
	return (
		<div
			role="alert"
			style={{
				display: "flex",
				flexDirection: "column",
				alignItems: "center",
				justifyContent: "center",
				textAlign: "center",
				padding: spacing[8],
				gap: spacing[3],
			}}
		>
			<WarningIcon />

			<p
				style={{
					margin: 0,
					fontSize: typography.size.lg,
					fontWeight: typography.weight.semibold,
					color: colors.slate[800],
				}}
			>
				{title}
			</p>

			<p
				style={{
					margin: 0,
					fontSize: typography.size.sm,
					color: colors.slate[500],
				}}
			>
				{message}
			</p>

			{onRetry !== undefined && (
				<button
					type="button"
					onClick={onRetry}
					style={{
						marginTop: spacing[2],
						padding: `${spacing[2]} ${spacing[4]}`,
						backgroundColor: colors.indigo[600],
						color: colors.white,
						border: "none",
						borderRadius: radii.md,
						fontSize: typography.size.sm,
						fontWeight: typography.weight.medium,
						cursor: "pointer",
					}}
				>
					Try again
				</button>
			)}
		</div>
	);
}
