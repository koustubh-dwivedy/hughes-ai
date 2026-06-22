import {
	AlertTriangle,
	BarChart2,
	Database,
	GitBranch,
	Inbox,
	Landmark,
	LayoutGrid,
	Sparkles,
	Users,
} from "lucide-react";
import { colors, spacing, typography } from "../../theme/tokens";
import type { NavEntry, NavSection, Product } from "./types";

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

export const DISPUTES: NavEntry[] = [
	{
		label: "Case Queue",
		href: "/disputes",
		icon: <Inbox size={16} />,
	},
];

/**
 * The sidebar is scoped to one product at a time (HUG CBD mockup). Each
 * product exposes its own labeled sections; `productForPath` picks the active
 * product from the current pathname so `NavBody` renders only that product's nav.
 */
export const LENDING_SECTIONS: NavSection[] = [
	{ label: "Intelligence", entries: INTELLIGENCE },
	{ label: "Dashboards", entries: DASHBOARDS },
	{ label: "Data", entries: DATA },
];

export const DISPUTE_SECTIONS: NavSection[] = [
	{ label: "Dispute Center", entries: DISPUTES },
];

export const PRODUCT_SECTIONS: Record<Product, NavSection[]> = {
	lending: LENDING_SECTIONS,
	disputes: DISPUTE_SECTIONS,
};

/** The launchpad route — the in-app "home" reached via "Switch product". */
export const SWITCH_PRODUCT: NavEntry = {
	label: "Switch product",
	href: "/",
	icon: <LayoutGrid size={16} />,
};

export function productForPath(pathname: string): Product {
	return pathname.startsWith("/disputes") ? "disputes" : "lending";
}

export const SECTION_LABEL: React.CSSProperties = {
	padding: `${spacing[2]} ${spacing[3]} ${spacing[1]}`,
	fontSize: typography.size.xs,
	fontWeight: typography.weight.semibold,
	color: colors.slate[500],
	textTransform: "uppercase",
	letterSpacing: "0.06em",
};

export const INTELLIGENCE_PATH_PREFIXES = ["/intelligence", "/chat"];
