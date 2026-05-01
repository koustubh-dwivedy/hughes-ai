import type React from "react";

export type CollapseState = "full" | "collapsed";

export interface NavEntry {
	label: string;
	href: string;
	icon: React.ReactNode;
}

export interface SideNavProps {
	defaultCollapsed?: boolean;
}
