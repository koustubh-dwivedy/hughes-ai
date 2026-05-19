import { emit } from "../../shared/telemetry/client";
import { radii, spacing } from "../../theme/tokens";
/**
 * HUG-270 — wraps the Hughes Logo in an anchor that links to the
 * marketing site. Used by SideNav in all three Logo render slots
 * (collapsed icon, expanded wordmark, mobile drawer wordmark).
 *
 * Convention: brand logo = home. Telegraphs clickability via subtle
 * hover background tint + cursor pointer; doesn't shout like a CTA.
 * Opens in a new tab to preserve in-app state (chat / dashboards).
 */
import Logo from "../AppHeader/Logo";

const HREF = "https://tryhughes.com";

interface Props {
	variant: "icon" | "wordmark";
	height: number;
}

const linkStyle: React.CSSProperties = {
	display: "inline-flex",
	alignItems: "center",
	justifyContent: "center",
	padding: `${spacing[1]} ${spacing[2]}`,
	borderRadius: radii.md,
	textDecoration: "none",
	cursor: "pointer",
	transition: "background 120ms ease",
};

export default function LogoHomeLink({ variant, height }: Props) {
	const onClick = (): void => {
		emit({
			type: "nav.external_clicked",
			destination: "home",
			href: HREF,
		});
	};
	return (
		<a
			href={HREF}
			target="_blank"
			rel="noopener noreferrer"
			aria-label="Hughes — visit tryhughes.com home page"
			title="Visit tryhughes.com"
			data-testid="logo-home-link"
			style={linkStyle}
			onClick={onClick}
			onMouseEnter={(e) => {
				e.currentTarget.style.background = "rgba(255,255,255,0.06)";
			}}
			onMouseLeave={(e) => {
				e.currentTarget.style.background = "transparent";
			}}
		>
			<Logo variant={variant} onDark height={height} />
		</a>
	);
}
