import { emit } from "../../shared/telemetry/client";
/**
 * "Contact Us" CTA (originally HUG-270 as "Book a Demo"). Lives in the
 * AppHeader's right zone, before the search trigger. Links externally to
 * the marketing site; opens in a new tab to preserve in-app chat/dashboard state.
 *
 * Visual treatment: filled indigo, matches the "+ New thread" button's
 * energy without being garish. The trailing ↗ glyph telegraphs that
 * this leaves the app.
 */
import { colors, radii, spacing, typography } from "../../theme/tokens";

const HREF = "https://tryhughes.com/contact.html";

const buttonStyle: React.CSSProperties = {
	display: "inline-flex",
	alignItems: "center",
	gap: spacing[1],
	padding: `${spacing[2]} ${spacing[4]}`,
	background: colors.indigo[700],
	color: colors.white,
	border: "none",
	borderRadius: radii.md,
	fontSize: typography.size.sm,
	fontWeight: typography.weight.medium,
	fontFamily: typography.fontFamily,
	textDecoration: "none",
	cursor: "pointer",
	transition: "background 120ms ease",
};

const arrowStyle: React.CSSProperties = {
	fontSize: typography.size.xs,
	marginLeft: spacing[1],
	opacity: 0.85,
};

export default function BookDemoButton() {
	const onClick = (): void => {
		emit({
			type: "nav.external_clicked",
			destination: "book_demo",
			href: HREF,
		});
	};
	return (
		<a
			href={HREF}
			target="_blank"
			rel="noopener noreferrer"
			aria-label="Contact Us on tryhughes.com"
			data-testid="book-demo-button"
			style={buttonStyle}
			onClick={onClick}
		>
			Contact Us
			<span aria-hidden="true" style={arrowStyle}>
				↗
			</span>
		</a>
	);
}
