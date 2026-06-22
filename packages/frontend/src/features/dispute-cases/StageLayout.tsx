import { colors, radii, spacing, typography } from "../../theme/tokens";
import Stepper from "./Stepper";

interface StageLayoutProps {
	stages: readonly string[];
	currentStage: number;
	selected: number;
	onSelect: (index: number) => void;
	/** Title of the stage currently shown (the right-column header). */
	title: string;
	/** Element shown to the right of the title (e.g. a provenance badge). */
	accessory?: React.ReactNode;
	children: React.ReactNode;
}

/**
 * The case-journey panel: a single elevated card with a vertical step rail on
 * the left and the active stage's content on the right. Replaces the old
 * unframed horizontal rail + separate content card so the journey reads as one
 * connected unit and the current/viewed step is unmistakable.
 */
export default function StageLayout({
	stages,
	currentStage,
	selected,
	onSelect,
	title,
	accessory,
	children,
}: StageLayoutProps) {
	return (
		<section
			style={{
				border: `1px solid ${colors.slate[200]}`,
				borderRadius: radii.xl,
				backgroundColor: colors.white,
				boxShadow:
					"0 1px 2px rgba(15,23,42,0.04), 0 8px 24px rgba(15,23,42,0.06)",
				display: "grid",
				gridTemplateColumns: "minmax(0, 240px) minmax(0, 1fr)",
				overflow: "hidden",
			}}
		>
			<aside
				style={{
					borderRight: `1px solid ${colors.slate[200]}`,
					backgroundColor: colors.slate[50],
					padding: `${spacing[5]} ${spacing[3]}`,
				}}
			>
				<Stepper
					stages={stages}
					currentStage={currentStage}
					selected={selected}
					onSelect={onSelect}
				/>
			</aside>
			<div style={{ minWidth: 0, padding: spacing[6] }}>
				<div
					style={{
						display: "flex",
						alignItems: "flex-start",
						justifyContent: "space-between",
						gap: spacing[3],
						marginBottom: spacing[5],
						paddingBottom: spacing[4],
						borderBottom: `1px solid ${colors.slate[200]}`,
					}}
				>
					<div
						style={{
							display: "flex",
							flexDirection: "column",
							gap: spacing[1],
						}}
					>
						<span
							style={{
								fontSize: typography.size.xs,
								color: colors.slate[500],
								letterSpacing: "0.04em",
							}}
						>
							Step {selected + 1} of {stages.length}
						</span>
						<h3
							style={{
								margin: 0,
								fontSize: typography.size.lg,
								fontWeight: typography.weight.semibold,
								color: colors.slate[900],
							}}
						>
							{title}
						</h3>
					</div>
					{accessory}
				</div>
				{children}
			</div>
		</section>
	);
}
