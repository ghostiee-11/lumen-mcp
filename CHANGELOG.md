# Changelog

All notable changes to lumen-mcp are documented here. Format loosely based on Keep a Changelog.

## [Unreleased]

### Upstream Lumen (Track 2, separate repo)
- Lumen PR #1 (expose `normalize_vegalite_spec` as a reusable function) done.
- Lumen PR #2 (`Report.from_views` keyless export) done.
- Context and drafts live in [UPSTREAM_LUMEN.md](UPSTREAM_LUMEN.md). lumen-mcp calls the private
  methods via `_shims.py` until these land in the installed Lumen, then picks up the public API
  automatically.

### Added
- Repo scaffold: `pyproject.toml`, package skeleton under `src/lumen_mcp/`, git init as ghostiee-11.
- Keyless Phase 0 core loop, verified end-to-end against local Lumen 1.2.0:
  - `session.py` - DuckDB workspace: one in-memory `DuckDBSource`; every SQL result is materialized
    as a named table via `create_sql_expr_source(materialize=True)` and referenced by name.
  - Tools: `connect_source`, `list_tables`, `describe_table`, `run_sql`, `render_vegalite`.
  - `rendering.py` - PNG via vl-convert and self-contained HTML via Panel `.save(embed=True)` (no
    server, no browser).
  - `_shims.py` - spec normalization bridge (public `normalize_vegalite_spec` when present, else
    `VegaLiteAgent._extract_spec`).
  - `server.py` FastMCP wiring; `examples/make_sample_db.py`; `tests/test_slice.py` (renders a
    correct sorted bar chart to PNG + offline HTML). ruff clean.
- Keyless loop completed:
  - `refine_chart` - deep-merge a spec patch into an existing chart and re-render under the same id.
  - `list_charts` - list the rendered-chart registry.
  - `build_report` - assemble charts + markdown into a self-contained HTML and a reproducible
    `.ipynb`, reusing Panel `.save` and `lumen.ai.export`.
- Live protocol verification: `tests/test_roundtrip.py` drives the tools through FastMCP's
  in-memory client (fastmcp 3.4.3). Installed into a runnable env (fastmcp + lumen-mcp editable) and
  registered with Claude Code (`claude mcp add`, health check Connected).
- Phase 1 (delivery hardening):
  - Chart tools return the rendered PNG as an inline MCP `Image` (displays in-chat, the model can
    see it) alongside structured data; hosts without inline images still get the saved paths.
  - `ui://lumen/chart/{id}` MCP-App resource serves each chart's interactive self-contained HTML
    (for Apps-capable hosts like Claude Desktop/web); render results carry the `ui_uri`.
  - `get_chart` re-fetches a chart by id.
  - `save_session` / `load_session` persist the workspace (DuckDB file + chart-spec sidecar) and
    restore it by reloading and re-rendering.
- Live dashboard server (self-contained, no second MCP):
  - `launch_dashboard` / `stop_dashboard` run a background `panel serve` process (the
    panel-live-server subprocess pattern, embedded here) that serves the session's charts
    (interactive Vega) and workspace tables (sortable Tabulator) as a live Lumen dashboard at a
    localhost URL, with direct DuckDB-workspace access. `launch_dashboard` also returns the charts as
    inline PNG previews (open the URL for the interactive version). Verified end-to-end (headless
    screenshot). 13 tools total.
- Keyed agentic mode (opt-in, requires an LLM key):
  - `lumen_ask(prompt)` runs Lumen's own Planner + SQLAgent + VegaLiteAgent headless over the
    workspace - Lumen writes and runs the SQL and builds the chart itself - returning the chart
    inline plus the generated SQL and a summary. Registered only when `OPENAI_API_KEY` or
    `ANTHROPIC_API_KEY` is set (13 tools keyless, 14 keyed). Runs headless with no Lumen change
    needed (`interface=None` + source pre-set in context). Verified end-to-end with gpt-4o.

### Notes
- Sources are loaded fully into the in-memory workspace; large on-disk sources via DuckDB `ATTACH`
  is a later enhancement.
- Running `server.py` needs an environment with `fastmcp` (a lumen-mcp dependency); the tool logic
  is verified in Lumen's environment.
