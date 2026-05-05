"""OpenUI DSL payload types (HUG-178 Phase A).

Wraps the LLM-emitted DSL as opaque text plus validation metadata. We do
NOT codegen Pydantic models for OpenUI's 54 components — the DSL is a
single string parsed at the JS layer (the OpenUI parser is in
`@openuidev/react-lang`). The Python types here exist purely so the
HUG-178 Phase B Node-subprocess validator has a typed shape to populate
when it reports back, and so HUG-179's frontend code receives a stable
JSON envelope.

Phase A ships this module without any caller — Phase B wires
`agent_runner.py` to populate it before the SSE flush, and the agent's
`final_answer.openui_dsl` becomes the `dsl_text` field.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class OpenUIValidationError(BaseModel):
    """One error reported by the OpenUI server-side parser.

    Mirrors `@openuidev/lang-core`'s `OpenUIError` shape so the frontend
    can render parse-error context without re-parsing the DSL.
    """

    code: str
    message: str = ""


class OpenUIDslPayload(BaseModel):
    """Server-side envelope around an LLM-emitted OpenUI DSL string."""

    dsl_text: str
    validated: bool = False
    validation_errors: list[OpenUIValidationError] = Field(default_factory=list)
    validated_at: datetime | None = None

    @property
    def is_renderable(self) -> bool:
        """A payload is renderable when validation completed without errors.

        The OpenUI parser is permissive and renders what it can even with
        errors, but we use this flag to choose between the OpenUI path
        and the legacy ResultPanel fallback in HUG-179.
        """
        return self.validated and not self.validation_errors
