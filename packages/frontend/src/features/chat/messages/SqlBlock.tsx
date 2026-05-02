import { useEffect, useState } from "react";
import { codeToHtml } from "shiki";
import { emit } from "../../../shared/telemetry/client";
import { colors, radii, spacing, typography } from "../../../theme/tokens";

interface Props {
	sql: string;
	queryId: string;
	editorUrl?: string;
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

const actionGroupStyle: React.CSSProperties = {
	display: "flex",
	gap: spacing[2],
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

export default function SqlBlock({ sql, queryId, editorUrl }: Props) {
	const [html, setHtml] = useState<string>("");
	const [copied, setCopied] = useState(false);

	useEffect(() => {
		let cancelled = false;
		codeToHtml(sql, { lang: "sql", theme: "github-light" })
			.then((rendered) => {
				if (!cancelled) setHtml(rendered);
			})
			.catch(() => {
				if (!cancelled) setHtml(`<pre><code>${sql}</code></pre>`);
			});
		return () => {
			cancelled = true;
		};
	}, [sql]);

	async function handleCopy() {
		const ok = await copyToClipboard(sql);
		if (ok) {
			setCopied(true);
			emit({ type: "chat.sql.copied", query_id: queryId });
			setTimeout(() => setCopied(false), 1500);
		}
	}

	return (
		<section aria-label="SQL block" style={wrapperStyle}>
			<header style={headerStyle}>
				<span>SQL</span>
				<div style={actionGroupStyle}>
					<button
						type="button"
						aria-label="Copy SQL"
						aria-pressed={copied}
						onClick={handleCopy}
						style={actionStyle(copied)}
					>
						{copied ? "Copied" : "Copy"}
					</button>
					{editorUrl !== undefined && (
						<a
							href={editorUrl}
							target="_blank"
							rel="noopener noreferrer"
							aria-label="Open SQL in editor"
							style={actionStyle(false)}
						>
							Open in editor
						</a>
					)}
				</div>
			</header>
			{html === "" ? (
				<pre style={codeStyle}>
					<code>{sql}</code>
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
