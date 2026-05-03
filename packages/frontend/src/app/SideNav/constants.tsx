import {
	AlertTriangle,
	BarChart2,
	Database,
	GitBranch,
	Landmark,
	Sparkles,
	Users,
} from "lucide-react";
import { colors, spacing, typography } from "../../theme/tokens";
import type { NavEntry } from "./types";

export const INTELLIGENCE: NavEntry[] = [
	{
		label: "Data Intelligence",
		href: "/intelligence",
		icon: <Sparkles size={16} />,
	},
];

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

export const DATA: NavEntry[] = [
	{
		label: "Sources & Freshness",
		href: "/data/sources",
		icon: <Database size={16} />,
	},
	{
		label: "Data Models",
		href: "/data/models",
		icon: <GitBranch size={16} />,
	},
];

export const SECTION_LABEL: React.CSSProperties = {
	padding: `${spacing[2]} ${spacing[3]} ${spacing[1]}`,
	fontSize: typography.size.xs,
	fontWeight: typography.weight.semibold,
	color: colors.slate[500],
	textTransform: "uppercase",
	letterSpacing: "0.06em",
};

export const INTELLIGENCE_PATH_PREFIXES = ["/intelligence", "/chat"];
