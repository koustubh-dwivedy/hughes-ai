import { Popover } from "@mantine/core";
import { useState } from "react";
import { colors, radii, spacing, typography } from "../../theme/tokens";

const PRESETS = [
	{ label: "Today", getValue: () => new Date().toISOString().slice(0, 10) },
	{
		label: "Start of Month",
		getValue: () => {
			const d = new Date();
			return new Date(d.getFullYear(), d.getMonth(), 1)
				.toISOString()
				.slice(0, 10);
		},
	},
	{
		label: "Last Month",
		getValue: () => {
			const d = new Date();
			return new Date(d.getFullYear(), d.getMonth() - 1, 1)
				.toISOString()
				.slice(0, 10);
		},
	},
] as const;

interface DatePickerProps {
	value: string | undefined;
	onChange: (date: string | undefined) => void;
}

const pillStyle: React.CSSProperties = {
	display: "inline-flex",
	alignItems: "center",
	gap: spacing[1],
	padding: `${spacing[1]} ${spacing[3]}`,
	border: `1px solid ${colors.slate[300]}`,
	borderRadius: radii.md,
	backgroundColor: colors.white,
	cursor: "pointer",
	fontSize: typography.size.sm,
	color: colors.slate[700],
	fontFamily: typography.fontFamily,
};

const presetBtnStyle: React.CSSProperties = {
	display: "block",
	width: "100%",
	textAlign: "left",
	background: "none",
	border: "none",
	cursor: "pointer",
	padding: `${spacing[2]} ${spacing[3]}`,
	fontSize: typography.size.sm,
	color: colors.slate[700],
	borderRadius: radii.sm,
};

export default function DatePicker({ value, onChange }: DatePickerProps) {
	const [open, setOpen] = useState(false);

	function handlePreset(getValue: () => string) {
		onChange(getValue());
		setOpen(false);
	}

	function handleCustom(e: React.ChangeEvent<HTMLInputElement>) {
		if (e.target.value) onChange(e.target.value);
	}

	return (
		<Popover opened={open} onChange={setOpen} position="bottom-end" withArrow>
			<Popover.Target>
				<button
					type="button"
					aria-label="Select as-of date"
					aria-expanded={open}
					onClick={() => setOpen((o) => !o)}
					style={pillStyle}
				>
					📅 {value ?? "Select date"}
				</button>
			</Popover.Target>
			<Popover.Dropdown
				style={{
					padding: spacing[3],
					minWidth: 200,
					backgroundColor: colors.white,
					border: `1px solid ${colors.slate[200]}`,
					borderRadius: radii.lg,
				}}
			>
				{PRESETS.map((p) => (
					<button
						key={p.label}
						type="button"
						style={presetBtnStyle}
						onClick={() => handlePreset(p.getValue)}
					>
						{p.label}
					</button>
				))}
				<div
					style={{
						height: 1,
						backgroundColor: colors.slate[200],
						margin: `${spacing[2]} 0`,
					}}
				/>
				<label
					htmlFor="header-date-custom"
					style={{
						fontSize: typography.size.xs,
						color: colors.slate[500],
						display: "block",
						marginBottom: spacing[1],
					}}
				>
					Custom date
				</label>
				<input
					id="header-date-custom"
					type="date"
					value={value ?? ""}
					onChange={handleCustom}
					style={{
						width: "100%",
						padding: `${spacing[1]} ${spacing[2]}`,
						border: `1px solid ${colors.slate[300]}`,
						borderRadius: radii.sm,
						fontSize: typography.size.sm,
						color: colors.slate[700],
						boxSizing: "border-box",
					}}
				/>
			</Popover.Dropdown>
		</Popover>
	);
}
