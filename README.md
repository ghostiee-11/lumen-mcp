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
- **Keyed (opt-in, Phase 2).** Lumen's own `SQLAgent` / `VegaLiteAgent` / `Planner` run inside the
  server. You just describe what you want. Requires an LLM key.

Same tools, same DuckDB workspace, same chart/report output. The key just flips the brain.

## The session is a DuckDB workspace

Each SQL result is materialized as a real table (via Lumen's
`DuckDBSource.create_sql_expr_source(materialize=True)`), so results accrete in one connection and
you reference them by **table name**. Charts and reports bind to those tables.

## Keyless tools (Phase 0)

- `connect_source(uri, name?)` - connect a `.db`/`.duckdb`, `.csv`, `.parquet`, `.json`, or `:memory:`.
- `list_tables()` / `describe_table(table)` - schema + a small sample.
- `run_sql(sql, name?)` - execute; the result becomes table `name`; returns columns + sample.
- `render_vegalite(spec, table)` - normalize the spec, render, save PNG + self-contained HTML.
- (next) `refine_chart`, `build_report`.

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
