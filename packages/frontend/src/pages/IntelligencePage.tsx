// Thread-aware conversational page lives in the feature module
// (HUG-179). This file is the route-level re-export so router.tsx
// keeps importing from `pages/`.
export { default } from "../features/intelligence/IntelligencePage";
