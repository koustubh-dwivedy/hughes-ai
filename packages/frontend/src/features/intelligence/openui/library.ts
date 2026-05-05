/**
 * OpenUI component library — single source of truth for the renderer
 * and (later, in HUG-178 Phase B) the agent's system prompt generator.
 *
 * Re-exports OpenUI's standard library from `@openuidev/react-ui/genui-lib`,
 * which registers the 54 components (Stack, Card, Table, LineChart,
 * BarChart, KpiTile, etc.) that the OpenUI prompt template assumes.
 *
 * The HUG-195 Day-1 spike (95% DSL validity on 20 must-pass questions
 * via Gemma 4 31B) used this exact library shape — keep production
 * aligned with what the spike validated.
 */

export {
  openuiLibrary as library,
  openuiPromptOptions,
} from "@openuidev/react-ui/genui-lib";
