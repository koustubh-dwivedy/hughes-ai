"""LangGraph ReAct agent for the conversational Data Intelligence module.

Replaces the one-shot NL→SQL pipeline with a tool-calling loop bounded
to 10 LLM steps per user turn. See ADR-0003 (`docs/decisions/`) and
HUG-176 in Linear for the architectural decisions.
"""
