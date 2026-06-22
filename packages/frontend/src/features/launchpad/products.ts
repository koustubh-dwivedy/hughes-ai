import { ShieldCheck, Sparkles } from "lucide-react";
import type { ComponentType } from "react";

export type ProductStatus = "live" | "soon";

export interface Product {
	id: string;
	name: string;
	tagline: string;
	/** lucide-react icon component, rendered by the launchpad card. */
	icon: ComponentType<{ size?: number }>;
	/** In-app route to enter the product. Omitted for "coming soon" tiles. */
	href?: string;
	status: ProductStatus;
}

/**
 * The Hughes platform's product catalog, shown on the launchpad.
 *
 * Two products are live — the Business Intelligence analytics suite and the
 * Credit-Bureau Dispute Center. (The `status` field stays so future products
 * can be added back as muted "coming soon" tiles.)
 */
export const PRODUCTS: Product[] = [
	{
		id: "lending-intelligence",
		name: "Business Intelligence",
		tagline:
			"Ask open-ended questions and explore grounded dashboards across originations, delinquency, and portfolio performance.",
		icon: Sparkles,
		href: "/dashboards/executive",
		status: "live",
	},
	{
		id: "dispute-center",
		name: "Dispute Center",
		tagline:
			"Work credit-bureau disputes end to end — validation-of-debt and identity-theft cases with FCRA / Metro 2 fidelity.",
		icon: ShieldCheck,
		href: "/disputes",
		status: "live",
	},
];
