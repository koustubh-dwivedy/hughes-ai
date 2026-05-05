import { fireEvent, render, screen } from "@testing-library/react";
import { Provider as ReduxProvider } from "react-redux";
import { describe, expect, it, vi } from "vitest";
import { createStore } from "../../../shared/api/store";
import { setDraft } from "../threadSlice";
import ComposerInput from "./ComposerInput";

function renderWithStore(
	store: ReturnType<typeof createStore>,
	props: { onSubmit: (s: string) => void; disabled?: boolean },
) {
	return render(
		<ReduxProvider store={store}>
			<ComposerInput {...props} />
		</ReduxProvider>,
	);
}

describe("ComposerInput", () => {
	it("disables Send when the draft is empty", () => {
		const store = createStore();
		renderWithStore(store, { onSubmit: vi.fn() });
		expect(screen.getByRole("button", { name: "Send" })).toBeDisabled();
	});

	it("enables Send and submits on click after typing", () => {
		const store = createStore();
		store.dispatch(setDraft("hello"));
		const onSubmit = vi.fn();
		renderWithStore(store, { onSubmit });
		const send = screen.getByRole("button", { name: "Send" });
		expect(send).not.toBeDisabled();
		fireEvent.click(send);
		expect(onSubmit).toHaveBeenCalledWith("hello");
		// Draft is cleared after submit.
		expect(store.getState().thread.draftInput).toBe("");
	});

	it("submits on Cmd+Enter / Ctrl+Enter", () => {
		const store = createStore();
		store.dispatch(setDraft("how is rate spread?"));
		const onSubmit = vi.fn();
		renderWithStore(store, { onSubmit });
		const textarea = screen.getByLabelText("Ask Hughes");
		fireEvent.keyDown(textarea, { key: "Enter", metaKey: true });
		expect(onSubmit).toHaveBeenCalledWith("how is rate spread?");
	});

	it("does not submit on bare Enter (multiline)", () => {
		const store = createStore();
		store.dispatch(setDraft("line one"));
		const onSubmit = vi.fn();
		renderWithStore(store, { onSubmit });
		fireEvent.keyDown(screen.getByLabelText("Ask Hughes"), { key: "Enter" });
		expect(onSubmit).not.toHaveBeenCalled();
	});

	it("treats whitespace-only drafts as empty", () => {
		const store = createStore();
		store.dispatch(setDraft("   \n  "));
		const onSubmit = vi.fn();
		renderWithStore(store, { onSubmit });
		expect(screen.getByRole("button", { name: "Send" })).toBeDisabled();
		fireEvent.click(screen.getByRole("button", { name: "Send" }));
		expect(onSubmit).not.toHaveBeenCalled();
	});

	it("respects the disabled prop while a turn is streaming", () => {
		const store = createStore();
		store.dispatch(setDraft("queued"));
		const onSubmit = vi.fn();
		renderWithStore(store, { onSubmit, disabled: true });
		expect(screen.getByLabelText("Ask Hughes")).toBeDisabled();
		expect(screen.getByRole("button", { name: "Send" })).toBeDisabled();
		fireEvent.keyDown(screen.getByLabelText("Ask Hughes"), {
			key: "Enter",
			ctrlKey: true,
		});
		expect(onSubmit).not.toHaveBeenCalled();
	});
});
