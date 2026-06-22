/**
 * Public surface for the member-journey data. Types live in `journeyTypes`;
 * the timeline is assembled deterministically in `journeyGenerator`.
 */
export type {
	ComplaintTier,
	Touchpoint,
	TouchpointCategory,
	TouchpointType,
} from "./journeyTypes";
export { CATEGORY_LABEL, TYPE_CATEGORY, TYPE_LABEL } from "./journeyTypes";
export { buildJourney as getMemberJourney } from "./journeyGenerator";
