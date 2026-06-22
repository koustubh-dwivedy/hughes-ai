import { ArrowRight } from "lucide-react";
import { useNavigate } from "react-router-dom";
import Logo from "../../app/AppHeader/Logo";
import { colors, radii, spacing, typography } from "../../theme/tokens";
import { PRODUCTS, type Product } from "./products";

const pageStyle: React.CSSProperties = {
	minHeight: "100vh",
	backgroundColor: colors.slate[900],
	display: "flex",
	flexDirection: "column",
	alignItems: "center",
	padding: `${spacing[12]} ${spacing[6]}`,
	boxSizing: "border-box",
};

const gridStyle: React.CSSProperties = {
	display: "grid",
	gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))",
	gap: spacing[5],
	width: "100%",
	maxWidth: 920,
};

function cardStyle(live: boolean): React.CSSProperties {
	return {
		textAlign: "left",
		display: "flex",
		flexDirection: "column",
		gap: spacing[3],
		padding: spacing[6],
		borderRadius: radii.xl,
		border: `1px solid ${colors.slate[700]}`,
		backgroundColor: colors.slate[800],
		color: colors.white,
		cursor: live ? "pointer" : "default",
		opacity: live ? 1 : 0.55,
		font: "inherit",
		transition: "border-color 150ms ease, transform 150ms ease",
	};
}

function ProductCard({ product }: { product: Product }) {
	const navigate = useNavigate();
	const live = product.status === "live";
	const Icon = product.icon;
	return (
		<button
			type="button"
			disabled={!live}
			aria-label={`${product.name}${live ? "" : " (coming soon)"}`}
			data-testid={`product-${product.id}`}
			style={cardStyle(live)}
			onClick={() => live && product.href && navigate(product.href)}
			onMouseEnter={(e) => {
				if (live) e.currentTarget.style.borderColor = colors.slate[400];
			}}
			onMouseLeave={(e) => {
				e.currentTarget.style.borderColor = colors.slate[700];
			}}
		>
			<div
				style={{
					display: "flex",
					alignItems: "center",
					justifyContent: "space-between",
				}}
			>
				<span
					style={{
						display: "inline-flex",
						alignItems: "center",
						justifyContent: "center",
						width: 40,
						height: 40,
						borderRadius: radii.lg,
						backgroundColor: colors.slate[700],
					}}
				>
					<Icon size={20} />
				</span>
				{!live && (
					<span
						style={{
							fontSize: typography.size.xs,
							fontWeight: typography.weight.semibold,
							textTransform: "uppercase",
							letterSpacing: "0.06em",
							color: colors.slate[400],
						}}
					>
						Coming soon
					</span>
				)}
			</div>
			<span
				style={{
					fontSize: typography.size.lg,
					fontWeight: typography.weight.semibold,
				}}
			>
				{product.name}
			</span>
			<span
				style={{
					fontSize: typography.size.sm,
					color: colors.slate[300],
					lineHeight: 1.5,
				}}
			>
				{product.tagline}
			</span>
			{live && (
				<span
					style={{
						display: "inline-flex",
						alignItems: "center",
						gap: spacing[1],
						marginTop: spacing[1],
						fontSize: typography.size.sm,
						fontWeight: typography.weight.medium,
						color: colors.white,
					}}
				>
					Enter <ArrowRight size={16} />
				</span>
			)}
		</button>
	);
}

export default function Launchpad() {
	return (
		<div style={pageStyle}>
			<div
				style={{
					display: "flex",
					flexDirection: "column",
					alignItems: "center",
					gap: spacing[2],
					marginBottom: spacing[12],
					textAlign: "center",
				}}
			>
				<Logo variant="wordmark" onDark height={28} />
				<h1
					style={{
						margin: 0,
						marginTop: spacing[4],
						fontSize: typography.size["2xl"],
						fontWeight: typography.weight.semibold,
						color: colors.white,
					}}
				>
					Choose a product
				</h1>
				<p
					style={{
						margin: 0,
						fontSize: typography.size.sm,
						color: colors.slate[400],
					}}
				>
					One platform for your credit union's analyst and operations teams.
				</p>
			</div>
			<div style={gridStyle}>
				{PRODUCTS.map((product) => (
					<ProductCard key={product.id} product={product} />
				))}
			</div>
		</div>
	);
}
