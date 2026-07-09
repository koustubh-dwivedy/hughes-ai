import { Paperclip } from "lucide-react";
import { useState } from "react";
import { colors, radii, spacing, typography } from "../../theme/tokens";
import Tag from "../../ui/primitives/Tag";
import AssetViewerModal from "./assets/AssetViewerModal";
import { type AssetContext, buildAssetContent } from "./assets/assetContent";
import { SectionCard } from "./caseUi";
import {
	acknowledgeAttachment,
	getOverride,
	useCaseProgressVersion,
} from "./data/caseProgressStore";
import type { AcdvAttachment } from "./types";

interface Props {
	caseId: string;
	attachments: AcdvAttachment[];
	context: AssetContext;
}

function isAcknowledged(
	a: AcdvAttachment,
	session: string[] | undefined,
): boolean {
	return a.acknowledged || Boolean(session?.includes(a.fileName));
}

/**
 * Consumer images / documents the CRA pushed with the ACDV. The furnisher must
 * take at least one action (View/Print/Download) on each — opening one here
 * marks it acknowledged, which unblocks the data-accuracy Decide gate.
 */
export default function AcdvAttachmentsPanel({
	caseId,
	attachments,
	context,
}: Props) {
	useCaseProgressVersion();
	const [openIdx, setOpenIdx] = useState<number | null>(null);
	const acknowledged = getOverride(caseId)?.acknowledged;

	const open = (i: number) => {
		acknowledgeAttachment(caseId, attachments[i].fileName);
		setOpenIdx(i);
	};

	return (
		<SectionCard title="ACDV attachments">
			<div
				style={{ display: "flex", flexDirection: "column", gap: spacing[2] }}
			>
				{attachments.map((a, i) => {
					const done = isAcknowledged(a, acknowledged);
					return (
						<div
							key={a.fileName}
							style={{
								display: "flex",
								alignItems: "center",
								gap: spacing[3],
								flexWrap: "wrap",
								padding: spacing[3],
								borderRadius: radii.md,
								border: `1px solid ${colors.slate[200]}`,
							}}
						>
							<button
								type="button"
								onClick={() => open(i)}
								style={{
									display: "inline-flex",
									alignItems: "center",
									gap: spacing[2],
									padding: `${spacing[1]} ${spacing[3]}`,
									borderRadius: radii.md,
									border: `1px solid ${colors.slate[300]}`,
									backgroundColor: colors.white,
									color: colors.slate[800],
									fontSize: typography.size.sm,
									fontWeight: typography.weight.medium,
									cursor: "pointer",
									font: "inherit",
								}}
							>
								<Paperclip size={13} />
								{a.label}
							</button>
							<span
								style={{
									fontSize: typography.size.xs,
									color: colors.slate[500],
								}}
							>
								{a.fileName} · {a.fileType}
							</span>
							<Tag
								label={done ? "Viewed" : "Action required — not yet viewed"}
								variant={done ? "success" : "warning"}
							/>
						</div>
					);
				})}
			</div>
			{openIdx !== null && (
				<AssetViewerModal
					content={buildAssetContent(
						attachments[openIdx].kind,
						{
							type: "document",
							label: attachments[openIdx].label,
							asset: {
								kind: attachments[openIdx].kind,
								title: attachments[openIdx].label,
							},
						},
						context,
					)}
					onClose={() => setOpenIdx(null)}
				/>
			)}
		</SectionCard>
	);
}
