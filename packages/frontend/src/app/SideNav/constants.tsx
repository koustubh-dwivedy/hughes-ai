import {
	AlertTriangle,
	BarChart2,
	Landmark,
	MessageSquare,
	Users,
} from "lucide-react";
import { colors, spacing, typography } from "../../theme/tokens";
import type { NavEntry } from "./types";

export const DASHBOARDS: NavEntry[] = [
	{
		label: "Executive Summary",
		href: "/dashboards/executive",
		icon: <BarChart2 size={16} />,
	},
	{
		label: "Deposit Portfolio",
		href: "/dashboards/deposits",
		icon: <Landmark size={16} />,
	},
	{
		label: "Past Due",
		href: "/dashboards/past-due",
		icon: <AlertTriangle size={16} />,
	},
	{
		label: "Officer/Branch",
		href: "/dashboards/officer-branch",
		icon: <Users size={16} />,
	},
];

export const TOOLS: NavEntry[] = [
	{ label: "Chat", href: "/chat", icon: <MessageSquare size={16} /> },
];

export const SECTION_LABEL: React.CSSProperties = {
	padding: `${spacing[2]} ${spacing[3]} ${spacing[1]}`,
	fontSize: typography.size.xs,
	fontWeight: typography.weight.semibold,
	color: colors.slate[500],
	textTransform: "uppercase",
	letterSpacing: "0.06em",
};
