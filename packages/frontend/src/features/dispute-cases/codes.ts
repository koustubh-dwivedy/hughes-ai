/**
 * e-OSCAR ACDV dispute reason codes + furnisher response codes, their labels,
 * and the response-code → outcome mapping used by the data-accuracy track.
 * Split from `types.ts` to keep each file under the 300-line structural cap.
 */

/**
 * The 10 e-OSCAR dispute categories and the full 32-code → category mapping,
 * transcribed verbatim from `ACDV_Dispute_Code_Master_Table.xlsx`. This is the
 * authoritative source for the "Type" (category) shown on the dispute dashboard.
 */
export type DisputeCategory =
	| "Ownership"
	| "Closed Account"
	| "Account Specific"
	| "Account Comments"
	| "Account Dates"
	| "Account Derogatory Payments"
	| "Collection"
	| "Bankruptcy"
	| "Fraud"
	| "Account Not Specific";

export const DISPUTE_CATEGORY: Record<string, DisputeCategory> = {
	// Ownership
	"001": "Ownership",
	"002": "Ownership",
	"101": "Ownership",
	// Closed Account
	"023": "Closed Account",
	"024": "Closed Account",
	// Account Specific
	"015": "Account Specific",
	"100": "Account Specific",
	"108": "Account Specific",
	"118": "Account Specific",
	"119": "Account Specific",
	// Account Comments
	"010": "Account Comments",
	"116": "Account Comments",
	"117": "Account Comments",
	// Account Dates
	"114": "Account Dates",
	"115": "Account Dates",
	// Account Derogatory Payments
	"039": "Account Derogatory Payments",
	"106": "Account Derogatory Payments",
	// Collection
	"006": "Collection",
	"012": "Collection",
	// Bankruptcy
	"019": "Bankruptcy",
	"037": "Bankruptcy",
	"102": "Bankruptcy",
	// Fraud
	"103": "Fraud",
	"104": "Fraud",
	// Account Not Specific
	"031": "Account Not Specific",
	"038": "Account Not Specific",
	"040": "Account Not Specific",
	"041": "Account Not Specific",
	"110": "Account Not Specific",
	"111": "Account Not Specific",
	"112": "Account Not Specific",
	"120": "Account Not Specific",
};

/** The dispute category for a reason code (per the master table). */
export function categoryForReason(code: string): DisputeCategory {
	return DISPUTE_CATEGORY[code] ?? "Account Not Specific";
}

/** e-OSCAR dispute reason codes modeled by the demo (data-accuracy + fraud). */
export type ReasonCode =
	| "001"
	| "015"
	| "103"
	| "104"
	| "106"
	| "112"
	| "114"
	| "115"
	| "116"
	| "117"
	| "118"
	| "119";

/** e-OSCAR furnisher response codes (the "Responding to an ACDV" set). */
export type ResponseCode =
	| "01"
	| "03"
	| "04"
	| "07"
	| "21"
	| "22"
	| "23"
	| "24";

export const REASON_CODE_LABEL: Record<ReasonCode, string> = {
	"001": "Not his/hers",
	"015": "Credit limit / original amount",
	"103": "Identity fraud (new-account)",
	"104": "Account takeover",
	"106": "Account status / payment history",
	"112": "Inaccurate information (non-specific)",
	"114": "Account dates",
	"115": "Date of first delinquency",
	"116": "Compliance condition code",
	"117": "Special comment / narrative",
	"118": "Current balance / amount past due",
	"119": "Charge-off / payment amount",
};

export const RESPONSE_CODE_LABEL: Record<ResponseCode, string> = {
	"01": "Verified — accurate as reported",
	"03": "Delete account",
	"04": "Misrouted — reroute",
	"07": "Delete due to fraud",
	"21": "Updated disputed field",
	"22": "Updated disputed + other fields",
	"23": "Accurate — updated unrelated fields",
	"24": "Not specific — verified & updated",
};

/** The DataAccuracyOutcome implied by a resolved response code. */
export function responseOutcome(code: ResponseCode): string {
	if (code === "21" || code === "22") return "Corrected & refurnished";
	if (code === "03" || code === "07") return "Field deleted";
	if (code === "24") return "Verified (non-specific)";
	return "Verified as reported";
}

/** Resolution outcome from the reviewer's sign-off option (or autonomous). */
export function daOutcome(
	recommended: ResponseCode,
	option: string | undefined,
): string {
	if (option === "more_info") return "Pending — more information requested";
	if (option === "override") return "Field deleted";
	return responseOutcome(recommended);
}
