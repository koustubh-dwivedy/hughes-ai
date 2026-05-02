import { notifications } from "@mantine/notifications";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { toast } from "../toast";

vi.mock("@mantine/notifications", () => ({
	notifications: { show: vi.fn() },
}));

describe("toast", () => {
	beforeEach(() => {
		vi.mocked(notifications.show).mockClear();
	});

	afterEach(() => {
		vi.restoreAllMocks();
	});

	describe("toast.success", () => {
		it("calls notifications.show with green color and default title", () => {
			toast.success("Operation complete");
			expect(notifications.show).toHaveBeenCalledWith({
				title: "Success",
				message: "Operation complete",
				color: "green",
				autoClose: 4000,
			});
		});

		it("uses custom title when provided", () => {
			toast.success("Saved!", "Changes saved");
			expect(notifications.show).toHaveBeenCalledWith(
				expect.objectContaining({ title: "Changes saved" }),
			);
		});
	});

	describe("toast.error", () => {
		it("calls notifications.show with red color and 6s autoClose", () => {
			toast.error("Something went wrong");
			expect(notifications.show).toHaveBeenCalledWith({
				title: "Error",
				message: "Something went wrong",
				color: "red",
				autoClose: 6000,
			});
		});

		it("uses custom title when provided", () => {
			toast.error("Request failed", "Network error");
			expect(notifications.show).toHaveBeenCalledWith(
				expect.objectContaining({ title: "Network error" }),
			);
		});
	});

	describe("toast.info", () => {
		it("calls notifications.show with blue color and 4s autoClose", () => {
			toast.info("Processing your request");
			expect(notifications.show).toHaveBeenCalledWith({
				title: "Info",
				message: "Processing your request",
				color: "blue",
				autoClose: 4000,
			});
		});

		it("uses custom title when provided", () => {
			toast.info("Queued for export", "Export started");
			expect(notifications.show).toHaveBeenCalledWith(
				expect.objectContaining({ title: "Export started" }),
			);
		});
	});
});
