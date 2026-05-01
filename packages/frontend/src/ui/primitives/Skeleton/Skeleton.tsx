import { useEffect } from "react";
import { colors, radii } from "../../../theme/tokens";

const STYLE_ID = "hughes-skeleton-style";

const keyframes = `
@keyframes shimmer {
  0% { opacity: 1; }
  50% { opacity: 0.4; }
  100% { opacity: 1; }
}
`;

function injectKeyframes(): void {
	if (typeof document === "undefined") return;
	if (document.getElementById(STYLE_ID)) return;
	const style = document.createElement("style");
	style.id = STYLE_ID;
	style.textContent = keyframes;
	document.head.appendChild(style);
}

export interface SkeletonProps {
	width?: number | string;
	height?: number | string;
	borderRadius?: string;
	animated?: boolean;
}

export default function Skeleton({
	width,
	height = "1rem",
	borderRadius,
	animated = true,
}: SkeletonProps) {
	const prefersReduced =
		typeof window !== "undefined"
			? window.matchMedia("(prefers-reduced-motion: reduce)").matches
			: false;

	const shouldAnimate = animated && !prefersReduced;

	useEffect(() => {
		if (shouldAnimate) {
			injectKeyframes();
		}
	}, [shouldAnimate]);

	return (
		<div
			role="status"
			aria-label="loading"
			style={{
				display: "block",
				backgroundColor: colors.slate[200],
				borderRadius: borderRadius ?? radii.md,
				width: width ?? "100%",
				height,
				animation: shouldAnimate ? "shimmer 1.5s ease-in-out infinite" : "none",
			}}
		/>
	);
}
