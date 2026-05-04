"""Service layer: orchestrates repo + nl_engine, mediates between routes
and the underlying domain logic. Routes never call the agent or repo
directly; they go through a service so the wire format stays decoupled
from the implementation."""
