import Tag from "../../../ui/primitives/Tag";
import { type AiProvenance, PROVENANCE_LABEL } from "./aiTypes";

const VARIANT: Record<AiProvenance, "default" | "info" | "warning"> = {
	deterministic: "default",
	ai_assisted: "info",
	agentic: "warning",
};

/** Labels a step as Deterministic vs AI-assisted vs Agentic AI. */
export default function ProvenanceBadge({
	provenance,
}: { provenance: AiProvenance }) {
	const label = PROVENANCE_LABEL[provenance];
	const isAi = provenance !== "deterministic";
	return (
		<Tag label={isAi ? `✨ ${label}` : label} variant={VARIANT[provenance]} />
	);
}
