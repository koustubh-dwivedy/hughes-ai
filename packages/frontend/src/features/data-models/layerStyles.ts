import { colors } from "../../theme/tokens";
import type { LayerName } from "./types";

export interface LayerStyle {
	background: string;
	border: string;
	accent: string;
}

export const LAYER_STYLES: Record<LayerName, LayerStyle> = {
	Sources: {
		background: colors.slate[50],
		border: colors.slate[300],
		accent: colors.slate[500],
	},
	Staging: {
		background: colors.slate[100],
		border: colors.slate[400],
		accent: colors.slate[600],
	},
	Core: {
		background: colors.white,
		border: colors.slate[500],
		accent: colors.slate[700],
	},
	Marts: {
		background: colors.indigo[50],
		border: colors.indigo[500],
		accent: colors.indigo[700],
	},
	Dashboards: {
		background: colors.indigo[100],
		border: colors.indigo[700],
		accent: colors.indigo[700],
	},
};
