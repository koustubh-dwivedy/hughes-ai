import { configureStore } from "@reduxjs/toolkit";
import { setupListeners } from "@reduxjs/toolkit/query";
import { threadSlice } from "../../features/intelligence/threadSlice";
import { baseApi } from "./client";
import { telemetryMiddleware } from "./telemetryMiddleware";

export function createStore() {
	const store = configureStore({
		reducer: {
			[baseApi.reducerPath]: baseApi.reducer,
			[threadSlice.name]: threadSlice.reducer,
		},
		middleware: (getDefault) =>
			getDefault().concat(baseApi.middleware, telemetryMiddleware),
	});
	setupListeners(store.dispatch);
	return store;
}

export const store = createStore();

export type AppStore = ReturnType<typeof createStore>;
export type RootState = ReturnType<AppStore["getState"]>;
export type AppDispatch = AppStore["dispatch"];
