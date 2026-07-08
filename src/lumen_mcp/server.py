"""FastMCP server exposing the keyless lumen-mcp tools.

Run with ``lumen-mcp`` (stdio) after ``pip install -e .``, or register with a client, e.g.
``claude mcp add lumen-mcp -- lumen-mcp``.
"""

from __future__ import annotations

import functools

from fastmcp import FastMCP

from . import sources, viz

mcp = FastMCP(
    "lumen-mcp",
    instructions=(
        "Drive Lumen from any MCP client (keyless mode). You, the host LLM, write the SQL and the "
        "Vega-Lite spec; this server runs them through Lumen: a DuckDB workspace, spec "
        "normalization, rendering, and report export. Workflow: connect_source -> describe_table "
        "-> run_sql (each result becomes a named table) -> render_vegalite(spec, table). Bind "
        "charts to the table names returned by run_sql, and omit 'data' from the spec (the server "
        "injects the table's data)."
    ),
)


def _safe(fn):
    """Return tool errors to the model instead of crashing the server."""

    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except Exception as exc:
            return {"error": f"{type(exc).__name__}: {exc}"}

    return wrapper


# Keyless Phase 0 tools. The functions carry their own docstrings + type hints for the schema.
_TOOLS = [
    sources.connect_source,
    sources.list_tables,
    sources.describe_table,
    sources.run_sql,
    viz.render_vegalite,
]

for _fn in _TOOLS:
    mcp.tool()(_safe(_fn))


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
