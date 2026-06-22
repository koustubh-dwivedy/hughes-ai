import type { AssetKind } from "../ai/aiTypes";
import { FRAUD_SIGNATURES } from "./journeySignaturesFraud";
import { VOD_SIGNATURES } from "./journeySignaturesVod";
import type {
	MemberSignature,
	Touchpoint,
	TouchpointType,
} from "./journeyTypes";

const SIGNATURES: Record<string, MemberSignature> = {
	...FRAUD_SIGNATURES,
	...VOD_SIGNATURES,
};

const FALLBACK: MemberSignature = {
	joinDate: "2019-01-01",
	events: [
		{
			date: "2019-01-01",
			type: "membership",
			summary: "Joined the credit union.",
		},
	],
};

interface FillerPattern {
	type: TouchpointType;
	channel?: string;
	label: string;
	money?: [number, number];
	assetKind?: AssetKind;
}

/** Routine activity woven around the signature events to fill the timeline. */
const FILLER_PATTERNS: FillerPattern[] = [
	{
		type: "letter",
		channel: "Mail",
		label: "Quarterly statement mailed",
		assetKind: "statement",
	},
	{
		type: "transaction",
		channel: "ACH",
		label: "Direct deposit (payroll)",
		money: [1800, 2600],
	},
	{ type: "card", channel: "POS", label: "Card purchase", money: [12, 180] },
	{
		type: "payment",
		channel: "Auto-pay",
		label: "Loan payment posted",
		money: [180, 520],
	},
	{ type: "fee", label: "NSF fee assessed", money: [29, 35] },
	{ type: "call", channel: "Phone", label: "Routine servicing call" },
	{
		type: "message",
		channel: "Online banking",
		label: "Secure message exchanged",
	},
	{ type: "card", channel: "ATM", label: "ATM withdrawal", money: [40, 300] },
	{ type: "email", channel: "Email", label: "e-Statement ready" },
	{
		type: "transaction",
		channel: "Transfer",
		label: "Internal transfer",
		money: [50, 900],
	},
];

const FILLER_COUNT = 22;
const TIMELINE_END = Date.parse("2026-05-31");

/** FNV-1a hash → stable per-member seed (no Math.random; deterministic). */
function seedFrom(s: string): number {
	let h = 2166136261;
	for (let i = 0; i < s.length; i++) {
		h = Math.imul(h ^ s.charCodeAt(i), 16777619);
	}
	return h >>> 0;
}

function makeRng(seed: number): () => number {
	let x = seed || 1;
	return () => {
		x = (Math.imul(x, 1664525) + 1013904223) >>> 0;
		return x / 4294967296;
	};
}

function isoDate(ms: number): string {
	return new Date(ms).toISOString().slice(0, 10);
}

function generateFiller(memberNumber: string, joinDate: string): Touchpoint[] {
	const seed = seedFrom(memberNumber);
	const rng = makeRng(seed);
	const start = Date.parse(joinDate);
	const span = Math.max(TIMELINE_END - start, 0);
	const offset = seed % FILLER_PATTERNS.length;
	const out: Touchpoint[] = [];
	for (let i = 0; i < FILLER_COUNT; i++) {
		const p = FILLER_PATTERNS[(i + offset) % FILLER_PATTERNS.length];
		const date = isoDate(start + ((i + 0.5) / FILLER_COUNT) * span);
		const amount = p.money
			? Math.round(p.money[0] + rng() * (p.money[1] - p.money[0]))
			: undefined;
		out.push({
			date,
			type: p.type,
			channel: p.channel,
			summary:
				amount != null ? `${p.label} — $${amount.toLocaleString()}` : p.label,
			amount,
			reference: p.assetKind
				? { type: "document", label: "Statement", asset: { kind: p.assetKind } }
				: undefined,
		});
	}
	return out;
}

/**
 * The full member journey: hand-authored signature events + deterministic
 * routine filler, sorted most-recent first. Stable for a given member number.
 */
export function buildJourney(memberNumber: string): Touchpoint[] {
	const sig = SIGNATURES[memberNumber] ?? FALLBACK;
	return [...sig.events, ...generateFiller(memberNumber, sig.joinDate)].sort(
		(a, b) => b.date.localeCompare(a.date),
	);
}
