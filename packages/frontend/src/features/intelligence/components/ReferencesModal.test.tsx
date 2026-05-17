import { render, screen } from "@testing-library/react";
import { Provider as ReduxProvider } from "react-redux";
import { describe, expect, it } from "vitest";
import { createStore } from "../../../shared/api/store";
import ReferencesModal from "./ReferencesModal";

function renderModal(
	overrides: Partial<React.ComponentProps<typeof ReferencesModal>> = {},
) {
	const props: React.ComponentProps<typeof ReferencesModal> = {
		open: true,
		onClose: () => {},
		rows: null,
		mfQuery: null,
		thinkingTrace: null,
		...overrides,
	};
	const store = createStore();
	return render(
		<ReduxProvider store={store}>
			<ReferencesModal {...props} />
		</ReduxProvider>,
	);
}

describe("ReferencesModal — non-scrolling header", () => {
	it("places the header OUTSIDE the scrolling body so it never scrolls", () => {
		renderModal();
		const header = screen.getByTestId("references-modal-header");
		const body = screen.getByTestId("references-modal-body");
		expect(header).toBeInTheDocument();
		expect(body).toBeInTheDocument();
		// Body is the overflow:auto container; header must NOT be inside it.
		expect(body.contains(header)).toBe(false);
		// Body owns the scroll; header is a peer flex child above it.
		expect(body.style.overflow).toBe("auto");
	});

	it("gives the header an opaque background + border so scrolled content cannot bleed through", () => {
		renderModal();
		const header = screen.getByTestId("references-modal-header");
		expect(header.style.background).not.toBe("");
		expect(header.style.background).not.toBe("transparent");
		// The border-bottom is the visual anchor that separates the header
		// from the scrolling content. Locks the "no floating" guarantee.
		expect(header.style.borderBottom).not.toBe("");
	});

	it("header does not shrink when body content grows (flex-shrink: 0)", () => {
		renderModal();
		const header = screen.getByTestId("references-modal-header");
		expect(header.style.flexShrink).toBe("0");
	});

	it("close button stays a descendant of the header", () => {
		renderModal();
		const closeButton = screen.getByTestId("references-modal-close");
		const header = screen.getByTestId("references-modal-header");
		expect(header.contains(closeButton)).toBe(true);
	});

	it("close button has accessible label + responds to clicks", () => {
		let closed = false;
		renderModal({
			onClose: () => {
				closed = true;
			},
		});
		const closeButton = screen.getByRole("button", {
			name: /close references/i,
		});
		closeButton.click();
		expect(closed).toBe(true);
	});

	it("returns null when not open (no portal leak)", () => {
		const { container } = renderModal({ open: false });
		expect(container.firstChild).toBeNull();
		expect(screen.queryByTestId("references-modal-header")).toBeNull();
	});
});
