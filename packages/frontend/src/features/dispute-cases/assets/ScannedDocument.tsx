import type { Address, FormContent, LetterContent } from "./assetContent";

const SERIF = "Georgia, 'Times New Roman', Times, serif";
const CURSIVE = "'Segoe Script', 'Snell Roundhand', 'Brush Script MT', cursive";
const INK = "#1f2733";
const PAPER = "#fffefb";
const MUTED = "#6b7280";

const paperStyle: React.CSSProperties = {
	position: "relative",
	width: "min(640px, 92vw)",
	maxHeight: "86vh",
	overflowY: "auto",
	backgroundColor: PAPER,
	color: INK,
	border: "1px solid #e3ddcf",
	boxShadow: "0 18px 50px rgba(15,23,42,0.28)",
	padding: "48px 52px 56px",
	fontFamily: SERIF,
	fontSize: 14,
	lineHeight: 1.55,
};

const paraStyle: React.CSSProperties = {
	margin: "10px 0",
	textAlign: "justify",
};

function ReceivedNote({ note }: { note?: string }) {
	if (!note) return null;
	return (
		<div
			style={{
				position: "absolute",
				top: 16,
				right: 18,
				fontSize: 11,
				color: "#9aa0a6",
				border: "1px solid #cfd3d8",
				borderRadius: 3,
				padding: "1px 6px",
				letterSpacing: "0.04em",
			}}
		>
			{note}
		</div>
	);
}

function SignatureBlock({ name, title }: { name: string; title?: string }) {
	return (
		<div style={{ marginTop: 22 }}>
			<div
				style={{
					fontFamily: CURSIVE,
					fontStyle: "italic",
					fontSize: 24,
					color: INK,
					lineHeight: 1.1,
				}}
			>
				{name}
			</div>
			<div style={{ fontSize: 13, marginTop: 4 }}>{name}</div>
			{title && <div style={{ fontSize: 12, color: MUTED }}>{title}</div>}
		</div>
	);
}

function AddressBlock({ a }: { a: Address }) {
	return (
		<div style={{ fontSize: 13 }}>
			<div style={{ fontWeight: 700 }}>{a.name}</div>
			{a.lines.map((l) => (
				<div key={l}>{l}</div>
			))}
		</div>
	);
}

function LetterLayout({ content }: { content: LetterContent }) {
	return (
		<>
			{content.draft && (
				<div
					style={{
						textAlign: "right",
						fontSize: 11,
						letterSpacing: "0.12em",
						color: "#b45309",
						textTransform: "uppercase",
						marginBottom: 4,
					}}
				>
					Draft
				</div>
			)}
			<AddressBlock a={content.sender} />
			<div style={{ margin: "16px 0", fontSize: 13 }}>{content.date}</div>
			<AddressBlock a={content.recipient} />
			{content.re && (
				<div style={{ margin: "16px 0 4px", fontWeight: 700 }}>
					RE: {content.re}
				</div>
			)}
			<div style={{ marginTop: content.re ? 8 : 16 }}>{content.salutation}</div>
			{content.body.map((p, i) => (
				<p key={`${i}-${p.slice(0, 10)}`} style={paraStyle}>
					{p}
				</p>
			))}
			<div style={{ marginTop: 16 }}>{content.closing}</div>
			<SignatureBlock
				name={content.signatory.name}
				title={content.signatory.title}
			/>
			{content.enclosures && content.enclosures.length > 0 && (
				<div style={{ marginTop: 20, fontSize: 12, color: MUTED }}>
					Enclosures: {content.enclosures.join("; ")}
				</div>
			)}
		</>
	);
}

function FormLayout({ content }: { content: FormContent }) {
	return (
		<>
			<div style={{ borderBottom: `2px solid ${INK}`, paddingBottom: 8 }}>
				<div style={{ fontSize: 19, fontWeight: 700 }}>{content.header}</div>
				{content.subheader && (
					<div style={{ fontSize: 13, fontStyle: "italic", color: MUTED }}>
						{content.subheader}
					</div>
				)}
			</div>
			<div style={{ margin: "14px 0", fontSize: 13 }}>
				{content.meta.map((m) => (
					<div key={m.label}>
						<span style={{ color: MUTED }}>{m.label}:</span> {m.value}
					</div>
				))}
			</div>
			{content.body.map((p, i) => (
				<p key={`${i}-${p.slice(0, 10)}`} style={paraStyle}>
					{p}
				</p>
			))}
			{content.table && <StatementTable table={content.table} />}
			{content.signatory && (
				<SignatureBlock
					name={content.signatory.name}
					title={content.signatory.title}
				/>
			)}
		</>
	);
}

function StatementTable({
	table,
}: { table: NonNullable<FormContent["table"]> }) {
	return (
		<div style={{ marginTop: 14 }}>
			{table.caption && (
				<div style={{ fontSize: 12, color: MUTED, marginBottom: 4 }}>
					{table.caption}
				</div>
			)}
			<table
				style={{
					width: "100%",
					borderCollapse: "collapse",
					fontSize: 12.5,
					fontFamily: SERIF,
				}}
			>
				<thead>
					<tr>
						{table.columns.map((col, i) => (
							<th
								key={col}
								style={{
									textAlign: i === 0 ? "left" : "right",
									borderBottom: `1px solid ${INK}`,
									padding: "4px 6px",
									fontWeight: 700,
								}}
							>
								{col}
							</th>
						))}
					</tr>
				</thead>
				<tbody>
					{table.rows.map((row, r) => (
						<tr
							key={row.join("|")}
							style={{
								backgroundColor:
									r === table.highlightRow ? "#fef3c7" : "transparent",
							}}
						>
							{row.map((cell, cIdx) => (
								<td
									key={`${r}-${cIdx}-${cell}`}
									style={{
										textAlign: cIdx === 0 ? "left" : "right",
										padding: "4px 6px",
										borderBottom: "1px solid #ece7da",
										fontWeight:
											r === table.highlightRow && cIdx === 1 ? 700 : 400,
									}}
								>
									{cell}
								</td>
							))}
						</tr>
					))}
				</tbody>
			</table>
		</div>
	);
}

/** Clean, authentic scanned render of a printed letter or form (demo mockup). */
export default function ScannedDocument({
	content,
}: { content: LetterContent | FormContent }) {
	return (
		<div data-testid="scanned-document" style={paperStyle}>
			<ReceivedNote note={content.receivedNote} />
			{content.format === "letter" ? (
				<LetterLayout content={content} />
			) : (
				<FormLayout content={content} />
			)}
			<div style={{ marginTop: 26, fontSize: 10, color: "#aab0b6" }}>
				Illustrative mock document — not a real file.
			</div>
		</div>
	);
}
