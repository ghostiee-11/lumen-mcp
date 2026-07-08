"""Bridges to Lumen internals.

lumen-mcp reuses Lumen's own code. A couple of pieces are not yet exposed as public API (see
UPSTREAM_LUMEN.md, PRs #1/#2). This module prefers the public API when present and falls back to
the validated private path otherwise, so the server works whether or not those PRs have landed in
the installed Lumen.
"""

from __future__ import annotations

import asyncio
import threading
from typing import Any

import yaml

# --- PR #1: vega-lite spec normalization -----------------------------------------------------
try:  # public API once PR #1 lands
    from lumen.ai.agents.vega_lite import normalize_vegalite_spec as _public_normalize

    _HAVE_PUBLIC_NORMALIZE = True
except Exception:  # pragma: no cover - depends on installed Lumen version
    _HAVE_PUBLIC_NORMALIZE = False


def _run_coro(coro: Any) -> Any:
    """Run a coroutine to completion from any context (sync tool or event loop)."""
    box: dict[str, Any] = {}

    def runner() -> None:
        loop = asyncio.new_event_loop()
        try:
            box["value"] = loop.run_until_complete(coro)
        finally:
            loop.close()

    thread = threading.Thread(target=runner)
    thread.start()
    thread.join()
    return box["value"]


def normalize_spec(spec: dict) -> dict:
    """Normalize + validate a raw Vega-Lite spec via Lumen.

    Returns ``{"spec": <normalized dict>, "sizing_mode": ..., "min_height": ...}`` (adds ``$schema``,
    default sizing, compound-chart handling, geo interactivity). Normalization is a hard prerequisite
    for rendering: ``pn.pane.Vega`` rejects a spec dict without ``$schema``.
    """
    if _HAVE_PUBLIC_NORMALIZE:
        return _public_normalize(dict(spec))

    from lumen.ai.agents import VegaLiteAgent

    agent = VegaLiteAgent()
    return _run_coro(agent._extract_spec({}, {"yaml_spec": yaml.dump(dict(spec))}))
