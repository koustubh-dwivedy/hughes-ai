import type { Meta, StoryObj } from "@storybook/react";
import TrustPanel from "./TrustPanel";

const meta: Meta<typeof TrustPanel> = { component: TrustPanel };
export default meta;

type Story = StoryObj<typeof TrustPanel>;

const mockTrust = JSON.stringify({
	origence_row_count: 12_543,
	symitar_row_count: 12_480,
	reconciliation_match_rate: 0.9951,
	known_caveats: ["Exclude pending.", "Deposits are Symitar-only."],
});

export const Loaded: Story = {
	beforeEach() {
		globalThis.fetch = (() =>
			Promise.resolve(
				new Response(mockTrust, {
					status: 200,
					headers: { "Content-Type": "application/json" },
				}),
			)) as typeof fetch;
	},
};
