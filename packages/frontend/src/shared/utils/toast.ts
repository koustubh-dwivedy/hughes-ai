import { notifications } from "@mantine/notifications";

function success(message: string, title = "Success"): void {
	notifications.show({ title, message, color: "green", autoClose: 4000 });
}

function error(message: string, title = "Error"): void {
	notifications.show({ title, message, color: "red", autoClose: 6000 });
}

function info(message: string, title = "Info"): void {
	notifications.show({ title, message, color: "blue", autoClose: 4000 });
}

export const toast = { success, error, info };
