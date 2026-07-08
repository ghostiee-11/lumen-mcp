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
- (build entries appended after the keyless slice is verified)
