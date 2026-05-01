module.exports = {
	reactUri: "http://127.0.0.1:6006",
	// Must be a space-separated string — parse-options.js calls .split(' ') on this.
	// chromeFlags inside configurations is ignored by chrome-launcher (it's tabOptions, not launch options).
	chromeFlags:
		"--headless --disable-gpu --hide-scrollbars --no-sandbox --disable-setuid-sandbox --disable-dev-shm-usage --font-render-hinting=none",
	// Allow 0.2% per-pixel colour difference to absorb minor antialiasing variation
	// between the loki:update and loki:test Chrome runs (pixelmatch threshold = 0.002).
	chromeTolerance: 0.2,
	// Button/Loading renders Mantine's animated spinner — rotation angle varies between
	// Chrome runs even with animation: none, so it cannot be regression-tested.
	skipStories: "^Primitives\\/Button Loading$",
	configurations: {
		"chrome.laptop": {
			target: "chrome.app",
			width: 1366,
			height: 768,
		},
	},
};
