import pino from "pino";

const logger = pino({
	browser: { asObject: true },
	level: "info",
});

export default logger;
