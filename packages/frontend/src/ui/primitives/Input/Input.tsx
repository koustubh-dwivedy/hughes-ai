import { TextInput } from "@mantine/core";
import type { TextInputProps } from "@mantine/core";

// Thin wrapper with Hughes defaults
export default function Input(props: TextInputProps) {
	return <TextInput {...props} />;
}
