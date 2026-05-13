/**
 * Shared recharts XAxis configuration for categorical data with
 * potentially long labels (product names, branch names, etc).
 *
 * The default recharts XAxis renders horizontally with auto-skipped
 * labels — fine for sparse data but produces collisions when every
 * tick must be shown (e.g. a 6-bar waterfall keyed on product). This
 * helper returns a props object that rotates labels 30° down-left,
 * truncates anything over 16 chars, and reserves vertical space
 * below the plot so the rotated text doesn't bleed into the next
 * element.
 *
 * Exported as a props builder rather than a component because
 * recharts' `BarChart`/`ComposedChart` discovers axes by walking its
 * direct React children and matching against the `XAxis` component
 * reference — wrapping `XAxis` inside another component breaks that
 * discovery and the axis silently vanishes.
 *
 * Usage:
 *   <BarChart data={…} margin={CHART_MARGIN}>
 *     <XAxis {...categoricalXAxisProps({ dataKey: "label" })} />
 *     <YAxis … />
 *     …
 *   </BarChart>
 *
 * Tooltips remain unaffected — they read the raw `payload.label`,
 * not the formatted tick text.
 */

import { colors } from "../../theme/tokens";
import { truncateLabel } from "./formatters";

const DEFAULT_TRUNCATE = 16;
const DEFAULT_HEIGHT = 64;
const DEFAULT_ANGLE = -30;

const DEFAULT_TICK = {
	fontSize: 11,
	fill: colors.slate[500],
} as const;

export const CHART_MARGIN = {
	top: 8,
	right: 16,
	left: 0,
	bottom: 16,
} as const;

interface BuilderArgs {
	dataKey: string;
	/** Override the truncation cap when the chart has narrow labels. */
	truncate?: number;
	/** Override the reserved bottom height (px). */
	height?: number;
}

export function categoricalXAxisProps({
	dataKey,
	truncate = DEFAULT_TRUNCATE,
	height = DEFAULT_HEIGHT,
}: BuilderArgs) {
	return {
		dataKey,
		interval: 0 as const,
		angle: DEFAULT_ANGLE,
		textAnchor: "end" as const,
		height,
		tick: DEFAULT_TICK,
		tickFormatter: truncateLabel(truncate),
	};
}
