/**
 * Markdown renderer for the assistant's prose answer (HUG-203).
 *
 * Wraps `react-markdown` with GFM (tables, task lists, autolinks,
 * strikethrough) and `rehype-sanitize` (defense-in-depth against any
 * raw HTML the LLM might emit). Component overrides map Markdown
 * elements to our design tokens so prose styling stays consistent
 * with the rest of the chat surface.
 *
 * Used in both the persisted AssistantTerminal and the in-flight
 * StreamingAssistant — partial Markdown re-parses cleanly on every
 * token delta, mirroring how ChatGPT / Claude.ai render mid-stream.
 */

import ReactMarkdown, { type Components } from "react-markdown";
import rehypeSanitize from "rehype-sanitize";
import remarkGfm from "remark-gfm";
import { colors, radii, spacing, typography } from "../../../theme/tokens";

interface Props {
	children: string;
	className?: string;
	/** Optional outer wrapper style — copied from the caller's
	 *  summaryStyle so the markdown root inherits its layout context. */
	style?: React.CSSProperties;
}

const tableWrapStyle: React.CSSProperties = {
	overflowX: "auto",
	margin: `${spacing[2]} 0`,
};

const tableStyle: React.CSSProperties = {
	width: "100%",
	borderCollapse: "collapse",
	fontSize: typography.size.xs,
	border: `1px solid ${colors.slate[200]}`,
	borderRadius: radii.md,
	overflow: "hidden",
};

const thStyle: React.CSSProperties = {
	background: colors.slate[100],
	textAlign: "left",
	padding: `${spacing[1]} ${spacing[3]}`,
	fontWeight: typography.weight.medium,
	color: colors.slate[700],
	borderBottom: `1px solid ${colors.slate[200]}`,
};

const tdStyle: React.CSSProperties = {
	padding: `${spacing[1]} ${spacing[3]}`,
	borderBottom: `1px solid ${colors.slate[100]}`,
};

const inlineCodeStyle: React.CSSProperties = {
	fontFamily:
		'ui-monospace, SFMono-Regular, "SF Mono", Menlo, Consolas, monospace',
	fontSize: "0.92em",
	background: colors.slate[100],
	color: colors.slate[800],
	padding: "1px 6px",
	borderRadius: radii.sm,
	border: `1px solid ${colors.slate[200]}`,
};

const preStyle: React.CSSProperties = {
	fontFamily:
		'ui-monospace, SFMono-Regular, "SF Mono", Menlo, Consolas, monospace',
	fontSize: typography.size.xs,
	background: colors.slate[100],
	color: colors.slate[800],
	padding: spacing[3],
	borderRadius: radii.md,
	border: `1px solid ${colors.slate[200]}`,
	overflowX: "auto",
	margin: `${spacing[2]} 0`,
};

const linkStyle: React.CSSProperties = {
	color: colors.indigo[700],
	textDecoration: "underline",
	textUnderlineOffset: 2,
};

const listStyle: React.CSSProperties = {
	margin: `${spacing[2]} 0`,
	paddingLeft: spacing[6],
	lineHeight: 1.55,
};

const headingStyle = (scale: "lg" | "base" | "sm"): React.CSSProperties => ({
	fontSize:
		scale === "lg"
			? typography.size.lg
			: scale === "base"
				? typography.size.base
				: typography.size.sm,
	fontWeight: typography.weight.medium,
	color: colors.slate[800],
	margin: `${spacing[3]} 0 ${spacing[1]}`,
});

const paragraphStyle: React.CSSProperties = {
	margin: `${spacing[1]} 0`,
};

const components: Components = {
	p: ({ node: _n, ...rest }) => <p style={paragraphStyle} {...rest} />,
	h1: ({ node: _n, ...rest }) => <h1 style={headingStyle("lg")} {...rest} />,
	h2: ({ node: _n, ...rest }) => <h2 style={headingStyle("lg")} {...rest} />,
	h3: ({ node: _n, ...rest }) => <h3 style={headingStyle("base")} {...rest} />,
	h4: ({ node: _n, ...rest }) => <h4 style={headingStyle("base")} {...rest} />,
	h5: ({ node: _n, ...rest }) => <h5 style={headingStyle("sm")} {...rest} />,
	h6: ({ node: _n, ...rest }) => <h6 style={headingStyle("sm")} {...rest} />,
	ul: ({ node: _n, ...rest }) => <ul style={listStyle} {...rest} />,
	ol: ({ node: _n, ...rest }) => <ol style={listStyle} {...rest} />,
	a: ({ node: _n, href, children, ...rest }) => (
		<a
			href={href}
			style={linkStyle}
			target="_blank"
			rel="noreferrer noopener"
			{...rest}
		>
			{children}
		</a>
	),
	table: ({ node: _n, children }) => (
		<div style={tableWrapStyle}>
			<table style={tableStyle}>{children}</table>
		</div>
	),
	th: ({ node: _n, ...rest }) => <th style={thStyle} {...rest} />,
	td: ({ node: _n, ...rest }) => <td style={tdStyle} {...rest} />,
	code: ({ node: _n, className: cn, children, ...rest }) => {
		// `code` inside a `pre` block has no className; bare inline code
		// also has no className unless rehype-highlight sets one. Treat
		// the absence of a fenced parent as "inline" — react-markdown
		// passes `inline` on older versions but not v10, so we infer.
		const text = String(children);
		const looksFenced = text.includes("\n");
		if (looksFenced) {
			return (
				<code className={cn} {...rest}>
					{children}
				</code>
			);
		}
		return (
			<code style={inlineCodeStyle} className={cn} {...rest}>
				{children}
			</code>
		);
	},
	pre: ({ node: _n, ...rest }) => <pre style={preStyle} {...rest} />,
};

export default function MarkdownText({ children, className, style }: Props) {
	return (
		<div className={className} style={style} data-markdown="true">
			<ReactMarkdown
				remarkPlugins={[remarkGfm]}
				rehypePlugins={[rehypeSanitize]}
				components={components}
			>
				{children}
			</ReactMarkdown>
		</div>
	);
}
