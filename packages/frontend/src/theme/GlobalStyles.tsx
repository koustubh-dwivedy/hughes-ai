import "@fontsource/inter/400.css";
import "@fontsource/inter/500.css";
import "@fontsource/inter/600.css";
import { useEffect } from "react";
import { colors, typography } from "./tokens";

export default function GlobalStyles() {
	useEffect(() => {
		document.body.style.margin = "0";
		document.body.style.fontFamily = typography.fontFamily;
		document.body.style.backgroundColor = colors.slate[50];
	}, []);
	return null;
}
