import { useEffect, useState } from "react";
import type { TrustResponse } from "../lib/api";
import { getTrust } from "../lib/api";

export default function TrustPanel() {
	const [trust, setTrust] = useState<TrustResponse | null>(null);

	useEffect(() => {
		getTrust()
			.then(setTrust)
			.catch(() => {});
	}, []);

	if (trust === null) return null;

	const matchPct = (trust.reconciliation_match_rate * 100).toFixed(1);

	return (
		<aside style={{ marginTop: "1.5rem" }}>
			<h2>Data Freshness</h2>
			<p>Origence records: {trust.origence_row_count.toLocaleString()}</p>
			<p>Symitar records: {trust.symitar_row_count.toLocaleString()}</p>
			<p>Reconciliation match rate: {matchPct}%</p>
			{trust.known_caveats.length > 0 && (
				<details>
					<summary>Known caveats ({trust.known_caveats.length})</summary>
					<ul>
						{trust.known_caveats.map((c) => (
							<li key={c}>{c}</li>
						))}
					</ul>
				</details>
			)}
		</aside>
	);
}
