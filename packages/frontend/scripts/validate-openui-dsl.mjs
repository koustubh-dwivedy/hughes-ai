#!/usr/bin/env node
// Parse an OpenUI Lang DSL string from stdin and emit a JSON validation
// summary to stdout. Used by `packages/api/src/api/services/openui_validator.py`
// (HUG-178 Phase B) — the API server spawns this script as a subprocess
// per terminal turn that carries `openui_dsl`.
//
// Output JSON shape:
//   { "valid": boolean, "errors": [{ "code": str, "message": str }, ...] }
//
// Exit codes:
//   0 — parsed (valid OR invalid; check `valid` field)
//   2 — script crashed before producing a result
//
// Run via the workspace pnpm script (`pnpm --filter frontend run
// openui:validate-dsl`) or directly: `node scripts/validate-openui-dsl.mjs`.

import { createParser } from "@openuidev/react-lang";
import { openuiLibrary } from "@openuidev/react-ui/genui-lib";

async function readStdin() {
  let buf = "";
  for await (const chunk of process.stdin) buf += chunk;
  return buf;
}

try {
  const dsl = await readStdin();
  const parser = createParser(openuiLibrary.toJSONSchema());
  const result = parser.parse(dsl);
  const errors = (result.meta?.errors ?? []).map((e) => ({
    code: String(e.code ?? "unknown"),
    message: String(e.message ?? ""),
  }));
  process.stdout.write(
    JSON.stringify({
      valid: errors.length === 0 && result.root !== null,
      errors,
    }),
  );
  process.exit(0);
} catch (e) {
  process.stdout.write(
    JSON.stringify({
      valid: false,
      errors: [
        {
          code: "parser_crash",
          message: String(e?.message ?? e),
        },
      ],
    }),
  );
  process.exit(2);
}
