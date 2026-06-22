import { Check, Minus } from "lucide-react";
import { colors, radii, spacing, typography } from "../../theme/tokens";
import Tag from "../../ui/primitives/Tag";
import type { FieldSource } from "./types";

export function SectionCard({
	title,
	accessory,
	children,
}: {
	title: string;
	/** Optional element rendered to the right of the title (e.g. a badge). */
	accessory?: React.ReactNode;
	children: React.ReactNode;
}) {
	return (
		<section
			style={{
				border: `1px solid ${colors.slate[200]}`,
				borderRadius: radii.xl,
				backgroundColor: colors.white,
				padding: spacing[6],
			}}
		>
			<div
				style={{
					display: "flex",
					alignItems: "center",
					justifyContent: "space-between",
					gap: spacing[3],
					marginBottom: spacing[4],
				}}
			>
				<h3
					style={{
						margin: 0,
						fontSize: typography.size.base,
						fontWeight: typography.weight.semibold,
						color: colors.slate[900],
					}}
				>
					{title}
				</h3>
				{accessory}
			</div>
			{children}
		</section>
	);
}

/** A labeled group within a stage, separated by a hairline + micro-heading. */
export function SubSection({
	title,
	children,
}: {
	title: string;
	children: React.ReactNode;
}) {
	return (
		<div
			style={{
				display: "flex",
				flexDirection: "column",
				gap: spacing[3],
				paddingTop: spacing[4],
				borderTop: `1px solid ${colors.slate[200]}`,
			}}
		>
			<span
				style={{
					fontSize: typography.size.xs,
					fontWeight: typography.weight.semibold,
					textTransform: "uppercase",
					letterSpacing: "0.04em",
					color: colors.slate[500],
				}}
			>
				{title}
			</span>
			{children}
		</div>
	);
}

const sourceVariant: Record<FieldSource, "info" | "success" | "default"> = {
	LOS: "info",
	core: "success",
	computed: "default",
};

/** A labeled value, optionally tagged with its data source (LOS / core). */
export function Field({
	label,
	value,
	source,
}: { label: string; value: string; source?: FieldSource }) {
	return (
		<div style={{ display: "flex", flexDirection: "column", gap: spacing[1] }}>
			<span
				style={{
					fontSize: typography.size.xs,
					color: colors.slate[500],
					textTransform: "uppercase",
					letterSpacing: "0.04em",
				}}
			>
				{label}
			</span>
			<span
				style={{
					display: "inline-flex",
					alignItems: "center",
					gap: spacing[2],
					fontSize: typography.size.sm,
					color: colors.slate[900],
				}}
			>
				{value}
				{source && <Tag label={source} variant={sourceVariant[source]} />}
			</span>
		</div>
	);
}

export function FieldGrid({ children }: { children: React.ReactNode }) {
	return (
		<div
			style={{
				display: "grid",
				gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))",
				gap: spacing[4],
			}}
		>
			{children}
		</div>
	);
}

/** A boolean compliance flag shown as a check/dash chip. */
export function Flag({ label, on }: { label: string; on: boolean }) {
	return (
		<span
			style={{
				display: "inline-flex",
				alignItems: "center",
				gap: spacing[2],
				fontSize: typography.size.sm,
				color: on ? colors.slate[900] : colors.slate[400],
			}}
		>
			<span
				style={{
					display: "inline-flex",
					alignItems: "center",
					justifyContent: "center",
					width: 18,
					height: 18,
					borderRadius: "9999px",
					backgroundColor: on ? "#16a34a" : colors.slate[200],
					color: colors.white,
				}}
			>
				{on ? <Check size={12} /> : <Minus size={12} />}
			</span>
			{label}
		</span>
	);
}
