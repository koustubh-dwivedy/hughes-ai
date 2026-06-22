import type { Stamp, StampTone } from "./assetContent";

export interface ScannedDoc {
	letterhead: string;
	subhead?: string;
	meta: { label: string; value: string }[];
	paragraphs: string[];
	signature?: { name: string; title?: string };
	stamps?: Stamp[];
}

const SERIF = "Georgia, 'Times New Roman', serif";
const TYPED = "'Courier New', Courier, monospace";
const INK = "#2b2620";
const PAPER = "#f3efe2";

// Fractal-noise speckle, multiplied onto the page to read as a scan.
const NOISE =
	"url(\"data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='140' height='140'><filter id='n'><feTurbulence type='fractalNoise' baseFrequency='0.85' numOctaves='2' stitchTiles='stitch'/></filter><rect width='100%25' height='100%25' filter='url(%23n)' opacity='0.55'/></svg>\")";

const STAMP_COLOR: Record<StampTone, string> = {
	red: "#a4342f",
	blue: "#274a78",
	ink: "#43392b",
};

const STAMP_SPOTS = [
	{ pos: { top: 70, right: 28 }, deg: 9 },
	{ pos: { bottom: 120, left: 34 }, deg: -7 },
	{ pos: { top: 150, right: 48 }, deg: 4 },
];

function StampMark({ stamp, index }: { stamp: Stamp; index: number }) {
	const color = STAMP_COLOR[stamp.tone];
	const p = STAMP_SPOTS[index % STAMP_SPOTS.length];
	return (
		<span
			aria-hidden
			style={{
				position: "absolute",
				...p.pos,
				transform: `rotate(${p.deg}deg)`,
				border: `3px double ${color}`,
				borderRadius: 4,
				color,
				opacity: 0.72,
				padding: "2px 10px",
				fontFamily: SERIF,
				fontWeight: 700,
				fontSize: 14,
				letterSpacing: "0.08em",
				textTransform: "uppercase",
				whiteSpace: "nowrap",
				pointerEvents: "none",
			}}
		>
			{stamp.text}
		</span>
	);
}

function Signature({ name, title }: { name: string; title?: string }) {
	return (
		<div style={{ marginTop: 28, fontFamily: TYPED, color: INK }}>
			<div style={{ fontSize: 13 }}>Sincerely,</div>
			<svg
				width="160"
				height="46"
				viewBox="0 0 160 46"
				role="img"
				aria-label={`Signature of ${name}`}
				style={{ display: "block", margin: "2px 0" }}
			>
				<title>Signature of {name}</title>
				<path
					d="M4 30 C 18 6, 30 40, 44 18 S 70 2, 86 26 C 96 40, 104 8, 118 24 S 150 10, 158 30"
					fill="none"
					stroke={INK}
					strokeWidth="2"
					strokeLinecap="round"
				/>
			</svg>
			<div style={{ fontSize: 13, fontWeight: 700 }}>{name}</div>
			{title && <div style={{ fontSize: 12, color: "#5b5446" }}>{title}</div>}
		</div>
	);
}

/** Heavy/aged scanned-paper render of a printed document (demo mockup). */
export default function ScannedDocument({ doc }: { doc: ScannedDoc }) {
	return (
		<div
			data-testid="scanned-document"
			style={{
				position: "relative",
				width: "min(620px, 92vw)",
				maxHeight: "86vh",
				overflowY: "auto",
				transform: "rotate(-1.2deg)",
				backgroundColor: PAPER,
				color: INK,
				border: "1px solid #d6cdb8",
				boxShadow:
					"0 26px 60px rgba(0,0,0,0.5), inset 0 0 90px rgba(120,98,52,0.1)",
				padding: "44px 46px 52px",
				fontFamily: TYPED,
			}}
		>
			<div
				aria-hidden
				style={{
					position: "absolute",
					inset: 0,
					backgroundImage: NOISE,
					opacity: 0.16,
					mixBlendMode: "multiply",
					pointerEvents: "none",
				}}
			/>
			{(doc.stamps ?? []).map((s, i) => (
				<StampMark key={s.text} stamp={s} index={i} />
			))}

			<div style={{ borderBottom: `3px double ${INK}`, paddingBottom: 8 }}>
				<div
					style={{
						fontFamily: SERIF,
						fontWeight: 700,
						fontSize: 20,
						letterSpacing: "0.02em",
					}}
				>
					{doc.letterhead}
				</div>
				{doc.subhead && (
					<div
						style={{
							fontFamily: SERIF,
							fontStyle: "italic",
							fontSize: 13,
							color: "#5b5446",
						}}
					>
						{doc.subhead}
					</div>
				)}
			</div>

			<div style={{ margin: "14px 0", fontSize: 12.5, lineHeight: 1.7 }}>
				{doc.meta.map((m) => (
					<div key={m.label}>
						<span style={{ color: "#6b6253" }}>{m.label}:</span> {m.value}
					</div>
				))}
			</div>

			<div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
				{doc.paragraphs.map((p, i) => (
					<p
						key={`${i}-${p.slice(0, 10)}`}
						style={{
							margin: 0,
							fontSize: 13,
							lineHeight: 1.75,
							textAlign: "justify",
						}}
					>
						{p}
					</p>
				))}
			</div>

			{doc.signature && (
				<Signature name={doc.signature.name} title={doc.signature.title} />
			)}

			<div
				style={{
					marginTop: 24,
					fontSize: 10,
					color: "#8a8270",
					fontFamily: TYPED,
				}}
			>
				Illustrative mock document — not a real file.
			</div>
		</div>
	);
}
