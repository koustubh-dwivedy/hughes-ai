import { colors, typography } from "../../theme/tokens";

const TAB_OPTIONS = [
	{ key: "new", label: "New" },
	{ key: "renewed", label: "Renewed" },
	{ key: "paid_off", label: "Paid Off" },
] as const;

interface Props {
	active: string | null;
	onSelect: (key: string) => void;
}

export default function Tabs({ active, onSelect }: Props) {
	return (
		<div
			role="tablist"
			style={{ display: "flex", gap: "0.5rem", marginBottom: "1rem" }}
		>
			{TAB_OPTIONS.map(({ key, label }) => (
				<button
					key={key}
					type="button"
					role="tab"
					aria-selected={active === key}
					onClick={() => onSelect(key)}
					style={{
						padding: "0.25rem 0.75rem",
						border: "1px solid",
						borderColor:
							active === key ? colors.indigo[600] : colors.slate[300],
						backgroundColor:
							active === key ? colors.indigo[600] : "transparent",
						color: active === key ? "white" : colors.slate[700],
						borderRadius: "0.25rem",
						cursor: "pointer",
						fontSize: typography.size.sm,
					}}
				>
					{label}
				</button>
			))}
		</div>
	);
}
