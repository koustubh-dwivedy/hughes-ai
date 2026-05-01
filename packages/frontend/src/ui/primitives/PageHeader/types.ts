import type { ReactNode } from "react";

export interface PageHeaderProps {
	eyebrow?: string; // small uppercase label above title, e.g. "Dashboard"
	title: string; // main heading
	subtitle?: string; // secondary text below title
	actions?: ReactNode; // right-aligned slot for buttons
	dateBadge?: ReactNode; // slot for <DateBadge> component
}
