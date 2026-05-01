import { Search, UserCircle2 } from "lucide-react";
import { useDashboardContext } from "../../shared/context/DashboardContext";
import { colors, radii, spacing, typography } from "../../theme/tokens";
import DatePicker from "./DatePicker";

const stripStyle: React.CSSProperties = {
	height: 56,
	minHeight: 56,
	display: "flex",
	alignItems: "center",
	justifyContent: "space-between",
	padding: `0 ${spacing[6]}`,
	backgroundColor: colors.white,
	borderBottom: `1px solid ${colors.slate[200]}`,
	gap: spacing[4],
};

const badgeStyle: React.CSSProperties = {
	fontSize: typography.size.sm,
	fontWeight: typography.weight.semibold,
	color: colors.indigo[600],
	backgroundColor: colors.indigo[50],
	padding: `${spacing[1]} ${spacing[3]}`,
	borderRadius: "9999px",
	letterSpacing: "0.02em",
};

const searchBtnStyle: React.CSSProperties = {
	display: "flex",
	alignItems: "center",
	gap: spacing[2],
	padding: `${spacing[2]} ${spacing[4]}`,
	border: `1px solid ${colors.slate[200]}`,
	borderRadius: "9999px",
	backgroundColor: colors.slate[50],
	cursor: "pointer",
	fontSize: typography.size.sm,
	color: colors.slate[500],
	fontFamily: typography.fontFamily,
};

const kbdStyle: React.CSSProperties = {
	fontSize: typography.size.xs,
	color: colors.slate[400],
	border: `1px solid ${colors.slate[300]}`,
	borderRadius: radii.sm,
	padding: "1px 4px",
};

export default function AppHeader() {
	const { asOfDate, setAsOfDate } = useDashboardContext();

	return (
		<header aria-label="App header" style={stripStyle}>
			<div style={{ display: "flex", alignItems: "center", gap: spacing[3] }}>
				<span style={badgeStyle}>Hughes AI</span>
			</div>
			<button type="button" aria-label="Open search" style={searchBtnStyle}>
				<Search size={14} />
				<span>Search</span>
				<span style={kbdStyle}>⌘K</span>
			</button>
			<div style={{ display: "flex", alignItems: "center", gap: spacing[3] }}>
				<DatePicker value={asOfDate} onChange={setAsOfDate} />
				<button
					type="button"
					aria-label="User menu"
					style={{
						background: "none",
						border: "none",
						cursor: "pointer",
						color: colors.slate[600],
						display: "flex",
						alignItems: "center",
					}}
				>
					<UserCircle2 size={24} />
				</button>
			</div>
		</header>
	);
}
