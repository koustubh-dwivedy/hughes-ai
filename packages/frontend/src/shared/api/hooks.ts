/**
 * Typed Redux hooks bound to the shared store. Use these instead of the
 * bare `useDispatch` / `useSelector` from react-redux so selectors get
 * `RootState` inference and dispatched actions get `AppDispatch`.
 */

import {
	type TypedUseSelectorHook,
	useDispatch,
	useSelector,
} from "react-redux";
import type { AppDispatch, RootState } from "./store";

export const useAppDispatch: () => AppDispatch = useDispatch;
export const useAppSelector: TypedUseSelectorHook<RootState> = useSelector;
