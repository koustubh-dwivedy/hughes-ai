import { formatDate } from "../format";
import {
	TYPE_CATEGORY,
	TYPE_LABEL,
	type Touchpoint,
	type TouchpointCategory,
} from "./journeyTypes";

export type CategoryFilter = "all" | TouchpointCategory;

export interface JourneyFilterState {
	query: string;
	category: CategoryFilter;
	/** Inclusive ISO start/end bounds (YYYY-MM-DD); undefined = unbounded. */
	start?: string;
	end?: string;
}

function matchesQuery(t: Touchpoint, q: string): boolean {
	const haystack = [
		t.summary,
		t.channel ?? "",
		t.tier ?? "",
		TYPE_LABEL[t.type],
		formatDate(t.date),
		t.date,
		// Amount is searchable both bare ("412") and formatted ("$412").
		t.amount != null ? `${t.amount} $${t.amount.toLocaleString()}` : "",
	]
		.join(" ")
		.toLowerCase();
	return haystack.includes(q);
}

function inCategory(t: Touchpoint, category: CategoryFilter): boolean {
	return category === "all" || TYPE_CATEGORY[t.type] === category;
}

function inRange(t: Touchpoint, start?: string, end?: string): boolean {
	if (start && t.date < start) return false;
	if (end && t.date > end) return false;
	return true;
}

/** Filters touchpoints by free-text query, category, and an explicit date range. */
export function filterTouchpoints(
	list: Touchpoint[],
	{ query, category, start, end }: JourneyFilterState,
): Touchpoint[] {
	const q = query.trim().toLowerCase();
	return list.filter(
		(t) =>
			inCategory(t, category) &&
			inRange(t, start, end) &&
			(!q || matchesQuery(t, q)),
	);
}
