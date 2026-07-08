# lumen-mcp

Drive [Lumen](https://github.com/holoviz/lumen)'s data to SQL to chart to report loop from any
MCP client (Claude Code, Claude Desktop, Cursor, VS Code, Goose, ...).

lumen-mcp is a standalone MCP server. It imports Lumen as a dependency and reuses Lumen's own
engine; it does not modify Lumen. See [UPSTREAM_LUMEN.md](UPSTREAM_LUMEN.md) for the two small,
additive, behavior-preserving Lumen changes that let the reuse be clean (the server works today
either way via `_shims.py`).

## Two modes

- **Keyless (default, no API key).** The host LLM you are already talking to writes the SQL and the
  Vega-Lite spec; lumen-mcp runs them through Lumen (DuckDB workspace, spec normalization,
  rendering, report export). The host is the agent.
- **Keyed (opt-in).** Lumen's own `SQLAgent` / `VegaLiteAgent` / `Planner` run inside the server.
  You just describe what you want. Requires an LLM key (see below).

Same tools, same DuckDB workspace, same chart/report output. The key just flips the brain.

## The session is a DuckDB workspace

Each SQL result is materialized as a real table (via Lumen's
`DuckDBSource.create_sql_expr_source(materialize=True)`), so results accrete in one connection and
you reference them by **table name**. Charts and reports bind to those tables.

## Keyless tools

- `connect_source(uri, name?)` - connect a `.db`/`.duckdb`, `.csv`, `.parquet`, `.json`, or `:memory:`.
- `list_tables()` / `describe_table(table)` - schema + a small sample.
- `run_sql(sql, name?)` - execute; the result becomes table `name`; returns columns + sample.
- `render_vegalite(spec, table)` - normalize the spec, render; returns an inline PNG plus saved
  PNG/HTML paths and a `ui_uri`.
- `refine_chart(chart_id, spec_patch)` - deep-merge a patch and re-render under the same id.
- `get_chart(chart_id)` / `list_charts()` - fetch or list rendered charts.
- `build_report(items, title, formats?)` - assemble charts + markdown into a self-contained HTML and
  a reproducible `.ipynb`.
- `save_session(path)` / `load_session(path)` - persist and restore the workspace and its charts.
- `launch_dashboard()` / `stop_dashboard()` - serve the session's charts + tables as a live,
  interactive Lumen dashboard (a background `panel serve` process) at a localhost URL.

Charts are also served as `ui://lumen/chart/{id}` MCP-App resources (interactive HTML) for
Apps-capable hosts (Claude Desktop/web).

## Keyed mode (Lumen's own agents)

Start the server with an LLM key in the environment and one extra tool appears:

```bash
OPENAI_API_KEY=...   lumen-mcp     # or ANTHROPIC_API_KEY=...
```

- `lumen_ask(prompt)` - Lumen's own Planner + SQLAgent + VegaLiteAgent run headless over the
  workspace: Lumen writes and runs the SQL and builds the chart itself. Returns the chart inline plus
  the generated SQL and a summary.

Set `LUMEN_MCP_LLM_MODEL` to override the default model (`gpt-4o` / `claude-sonnet-4-5`). Without a
key, `lumen_ask` is not registered and the server runs keyless.

## Live dashboard

`launch_dashboard()` runs a Panel server (inside lumen-mcp, reusing the panel-live-server pattern)
that reconstructs the session's charts and tables into a live, interactive dashboard and returns a
`http://localhost:PORT/...` URL. Unlike the static HTML export, its widgets and tables re-query the
DuckDB workspace live. `stop_dashboard()` shuts it down. Requires a local browser (localhost).

## Quick start

```bash
pip install -e .
python examples/make_sample_db.py          # writes sample.db
# register with your client, e.g.:
#   claude mcp add lumen-mcp -- lumen-mcp
```

Then, in the client: connect to `sample.db`, run a `GROUP BY` query, and render a bar chart.

## Status

Phase 0 (keyless core loop) in progress. See [CHANGELOG.md](CHANGELOG.md).
