import type React from "react";

export interface KpiTileProps {
	label: string;
	value: string;
	/** Primary delta string, e.g. "↑ $1.4M" */
	delta?: string;
	/** Secondary label clarifying the delta, e.g. "MoM" or "vs Feb" */
	deltaLabel?: string;
	deltaPositive?: boolean;
	/** One-line interpretation under the value, e.g. "fastest growth in 6 mo." */
	context?: string;
	icon?: React.ReactNode;
	infoTooltip?: string;
	onClick?: () => void;
	loading?: boolean;
}
