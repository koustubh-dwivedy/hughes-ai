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

describe("ReferencesModal — sticky header", () => {
	it("renders the header with position: sticky so the close button stays in view when scrolling", () => {
		renderModal();
		const header = screen.getByTestId("references-modal-header");
		expect(header).toBeInTheDocument();
		// Inline style assertions: jsdom does not run the layout engine, so we
		// verify the CSS contract directly rather than via getComputedStyle.
		expect(header.style.position).toBe("sticky");
		expect(header.style.top).toBe("0px");
		expect(header.style.zIndex).toBe("1");
	});

	it("gives the sticky header an opaque background so scrolled content does not bleed through", () => {
		renderModal();
		const header = screen.getByTestId("references-modal-header");
		// Must NOT be transparent — if it were, table rows behind it during
		// scroll would show through the close button.
		expect(header.style.background).not.toBe("");
		expect(header.style.background).not.toBe("transparent");
	});

	it("close button stays a descendant of the sticky header (so it sticks with it)", () => {
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
