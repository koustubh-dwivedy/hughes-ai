interface LogoProps {
	/** "icon" = bold H mark only; "wordmark" = full HUGHES type. */
	variant?: "icon" | "wordmark";
	/** Inverts the PNG so the black logo renders white on a dark surface. */
	onDark?: boolean;
	height?: number;
}

export default function Logo({
	variant = "wordmark",
	onDark = false,
	height,
}: LogoProps) {
	const src = variant === "icon" ? "/logo1.png" : "/logo2.png";
	const fallbackHeight = variant === "icon" ? 32 : 36;
	return (
		<img
			src={src}
			alt="Hughes AI"
			height={height ?? fallbackHeight}
			style={{
				display: "block",
				height: height ?? fallbackHeight,
				width: "auto",
				objectFit: "contain",
				filter: onDark ? "brightness(0) invert(1)" : undefined,
			}}
		/>
	);
}
