import type React from "react";

export interface SparkPoint {
	value: number;
}

export interface KpiTileProps {
	label: string;
	value: string;
	delta?: string;
	deltaPositive?: boolean;
	sparkline?: SparkPoint[];
	icon?: React.ReactNode;
	infoTooltip?: string;
	onClick?: () => void;
	loading?: boolean;
}
