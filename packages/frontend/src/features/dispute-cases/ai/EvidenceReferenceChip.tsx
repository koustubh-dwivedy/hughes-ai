import { ExternalLink, FileSearch, Paperclip } from "lucide-react";
import { useState } from "react";
import { colors, radii, spacing, typography } from "../../../theme/tokens";
import Tooltip from "../../../ui/primitives/Tooltip";
import AssetViewerModal from "../assets/AssetViewerModal";
import { type AssetContext, buildAssetContent } from "../assets/assetContent";
import type { EvidenceReference } from "./aiTypes";

const chipStyle: React.CSSProperties = {
	display: "inline-flex",
	alignItems: "center",
	gap: spacing[1],
	padding: `0 ${spacing[2]}`,
	borderRadius: radii.sm,
	border: `1px solid ${colors.slate[200]}`,
	backgroundColor: colors.white,
	color: colors.slate[700],
	fontSize: typography.size.xs,
	fontWeight: typography.weight.medium,
	textDecoration: "none",
	cursor: "pointer",
	lineHeight: "1.4rem",
	whiteSpace: "nowrap",
	font: "inherit",
};

interface Props {
	reference: EvidenceReference;
	/** Member/date context used to fill a mocked file asset. */
	context?: AssetContext;
}

/**
 * A cited-evidence chip. If the reference carries a mockable `asset`, it opens
 * that file in a blurred-backdrop overlay. Otherwise it renders an external
 * link (web-reachable) or a hover preview (internal pointer).
 */
export default function EvidenceReferenceChip({ reference, context }: Props) {
	const [open, setOpen] = useState(false);

	if (reference.asset) {
		const content = buildAssetContent(reference.asset.kind, reference, context);
		return (
			<>
				<button type="button" style={chipStyle} onClick={() => setOpen(true)}>
					<Paperclip size={12} />
					{reference.label}
				</button>
				{open && (
					<AssetViewerModal content={content} onClose={() => setOpen(false)} />
				)}
			</>
		);
	}

	const hasLink = Boolean(reference.url);
	const inner = (
		<>
			{hasLink ? <ExternalLink size={12} /> : <FileSearch size={12} />}
			{reference.label}
		</>
	);

	if (hasLink) {
		const link = (
			<a
				href={reference.url}
				target="_blank"
				rel="noopener noreferrer"
				style={chipStyle}
			>
				{inner}
			</a>
		);
		return reference.preview ? (
			<Tooltip label={reference.preview} multiline w={260}>
				{link}
			</Tooltip>
		) : (
			link
		);
	}

	const span = <span style={chipStyle}>{inner}</span>;
	return reference.preview ? (
		<Tooltip label={reference.preview} multiline w={260}>
			{span}
		</Tooltip>
	) : (
		span
	);
}
