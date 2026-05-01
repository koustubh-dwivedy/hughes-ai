import type React from "react";

export interface ChartCardProps {
	title: string;
	subtitle?: string;
	actions?: React.ReactNode;
	footer?: React.ReactNode;
	children?: React.ReactNode;
	loading?: boolean;
}
