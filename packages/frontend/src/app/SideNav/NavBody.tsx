import { Fragment } from "react";
import { useLocation } from "react-router-dom";
import { colors, spacing } from "../../theme/tokens";
import NavItem from "./NavItem";
import {
	PRODUCT_SECTIONS,
	SECTION_LABEL,
	SWITCH_PRODUCT,
	productForPath,
} from "./constants";

interface NavBodyProps {
	collapsed: boolean;
}

const dividerStyle: React.CSSProperties = {
	height: 1,
	backgroundColor: colors.slate[700],
	margin: `${spacing[2]} 0`,
};

/**
 * Renders the nav for the active product only (lending vs disputes), derived
 * from the current path, plus a "Switch product" control that returns to the
 * launchpad. Keeping this in its own module holds SideNav.tsx under the
 * 300-line structural cap.
 */
export default function NavBody({ collapsed }: NavBodyProps) {
	const { pathname } = useLocation();
	const sections = PRODUCT_SECTIONS[productForPath(pathname)];

	return (
		<div style={{ flex: 1, paddingTop: spacing[2], overflowY: "auto" }}>
			{sections.map((section, index) => (
				<Fragment key={section.label}>
					{index > 0 && <div style={dividerStyle} />}
					{!collapsed && <p style={SECTION_LABEL}>{section.label}</p>}
					{section.entries.map((item) => (
						<NavItem key={item.href} {...item} collapsed={collapsed} />
					))}
				</Fragment>
			))}
			<div style={dividerStyle} />
			<NavItem {...SWITCH_PRODUCT} collapsed={collapsed} />
		</div>
	);
}
