#!/usr/bin/env node
// Emit the OpenUI Lang DSL system prompt to stdout.
//
// Run via the package script (resolves OpenUI deps from frontend's
// node_modules):
//
//   pnpm --filter frontend run openui:prompt > \
//     packages/nl-engine/src/nl_engine/agent/openui_prompt.txt
//
// Or via the Makefile: `make openui-prompt`.
//
// The output is the ~20K-char instruction manual the agent receives so it
// can emit valid DSL using the registered 54 components. Loaded as a
// committed text artifact at agent module-load time (HUG-178 Phase B).
//
// Re-run this script (and re-commit the artifact) whenever
// @openuidev/react-ui or @openuidev/lang-core is bumped.

import {
  openuiLibrary,
  openuiPromptOptions,
} from "@openuidev/react-ui/genui-lib";

const prompt = openuiLibrary.prompt(openuiPromptOptions);
process.stdout.write(prompt);
