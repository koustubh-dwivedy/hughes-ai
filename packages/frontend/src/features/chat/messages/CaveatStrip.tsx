import { useEffect } from "react";
import { emit } from "../../../shared/telemetry/client";
import { spacing } from "../../../theme/tokens";
import Tag from "../../../ui/primitives/Tag";

interface Props {
	caveats: string[];
}

const stripStyle: React.CSSProperties = {
	display: "flex",
	flexWrap: "wrap" as const,
	gap: spacing[2],
	marginBottom: spacing[3],
};

export default function CaveatStrip({ caveats }: Props) {
	useEffect(() => {
		caveats.forEach((_, i) => {
			emit({ type: "chat.caveat.viewed", caveat_index: i });
		});
	}, [caveats]);

	if (caveats.length === 0) return null;

	return (
		<section aria-label="Result caveats" style={stripStyle}>
			{caveats.map((caveat, i) => (
				<Tag
					key={`${i}-${caveat.slice(0, 24)}`}
					label={caveat}
					variant="warning"
					size="sm"
				/>
			))}
		</section>
	);
}
