import { useEffect, useMemo, useState } from "react";
import { codeToHtml } from "shiki";
import { colors, radii, spacing, typography } from "../../../theme/tokens";

interface Props {
	value: unknown;
	label?: string;
	onCopy?: () => void;
}

const wrapperStyle: React.CSSProperties = {
	border: `1px solid ${colors.slate[200]}`,
	borderRadius: radii.md,
	background: colors.slate[50],
	overflow: "hidden",
	marginTop: spacing[2],
};

const headerStyle: React.CSSProperties = {
	display: "flex",
	alignItems: "center",
	justifyContent: "space-between",
	padding: `${spacing[2]} ${spacing[3]}`,
	background: colors.slate[100],
	borderBottom: `1px solid ${colors.slate[200]}`,
	fontSize: typography.size.xs,
	color: colors.slate[600],
	fontWeight: typography.weight.medium,
	textTransform: "uppercase",
	letterSpacing: "0.04em",
};

function actionStyle(active: boolean): React.CSSProperties {
	return {
		background: active ? colors.indigo[50] : colors.white,
		border: `1px solid ${active ? colors.indigo[500] : colors.slate[300]}`,
		borderRadius: radii.sm,
		padding: `${spacing[1]} ${spacing[2]}`,
		fontSize: typography.size.xs,
		color: active ? colors.indigo[700] : colors.slate[700],
		cursor: "pointer",
		fontFamily: typography.fontFamily,
		textDecoration: "none",
	};
}

const codeStyle: React.CSSProperties = {
	padding: spacing[3],
	overflowX: "auto",
	fontSize: typography.size.xs,
	lineHeight: 1.5,
};

async function copyToClipboard(text: string): Promise<boolean> {
	if (!navigator.clipboard) return false;
	try {
		await navigator.clipboard.writeText(text);
		return true;
	} catch {
		return false;
	}
}

export default function JsonBlock({ value, label = "JSON", onCopy }: Props) {
	const pretty = useMemo(() => {
		try {
			return JSON.stringify(value, null, 2);
		} catch {
			return String(value);
		}
	}, [value]);

	const [html, setHtml] = useState<string>("");
	const [copied, setCopied] = useState(false);

	useEffect(() => {
		let cancelled = false;
		codeToHtml(pretty, { lang: "json", theme: "github-light" })
			.then((rendered) => {
				if (!cancelled) setHtml(rendered);
			})
			.catch(() => {
				if (!cancelled) setHtml(`<pre><code>${pretty}</code></pre>`);
			});
		return () => {
			cancelled = true;
		};
	}, [pretty]);

	async function handleCopy() {
		const ok = await copyToClipboard(pretty);
		if (ok) {
			setCopied(true);
			onCopy?.();
			setTimeout(() => setCopied(false), 1500);
		}
	}

	return (
		<section aria-label={`${label} block`} style={wrapperStyle}>
			<header style={headerStyle}>
				<span>{label}</span>
				<button
					type="button"
					aria-label={`Copy ${label}`}
					aria-pressed={copied}
					onClick={handleCopy}
					style={actionStyle(copied)}
				>
					{copied ? "Copied" : "Copy"}
				</button>
			</header>
			{html === "" ? (
				<pre style={codeStyle}>
					<code>{pretty}</code>
				</pre>
			) : (
				<div
					style={codeStyle}
					// biome-ignore lint/security/noDangerouslySetInnerHtml: shiki output is controlled and HTML-escaped
					dangerouslySetInnerHTML={{ __html: html }}
				/>
			)}
		</section>
	);
}
