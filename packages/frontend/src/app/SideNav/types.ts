import type React from "react";

export type CollapseState = "full" | "collapsed";

export interface NavEntry {
	label: string;
	href: string;
	icon: React.ReactNode;
}

/** A labeled group of nav entries within a product's scoped sidebar. */
export interface NavSection {
	label: string;
	entries: NavEntry[];
}

/** Which product's scoped sidebar is active. */
export type Product = "lending" | "disputes";

export interface SideNavProps {
	defaultCollapsed?: boolean;
}
