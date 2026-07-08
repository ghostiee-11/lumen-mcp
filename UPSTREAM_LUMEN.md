# Upstream Lumen changes for lumen-mcp

**Handoff doc.** This is written so a *fresh* session (with no prior chat context) can pick it up and
open the PRs. It documents small, **purely additive, behavior-preserving** changes to the **Lumen**
repo ([holoviz/lumen](https://github.com/holoviz/lumen)) that help a separate project, `lumen-mcp`,
reuse Lumen's own code.

## What lumen-mcp is (context)

`lumen-mcp` is a standalone MCP server (its own repo — **not** part of Lumen) that lets any MCP client
(Claude Code, Claude Desktop, Cursor, …) drive a data → SQL → chart → downloadable-report loop using
Lumen's engine. In its default "keyless" mode the **host LLM writes the SQL and the Vega-Lite spec**,
and lumen-mcp runs them through Lumen's execution / normalization / rendering / export code. It imports
Lumen as a dependency and never edits Lumen's source. These upstream changes just expose a couple of
pieces cleanly so lumen-mcp calls a public API instead of a private method.

## Hard constraint (from the project owner)

> **Do not change or break any existing Lumen behavior. These are additive-only. Just add what the MCP
> needs.**

Every item below is either a *new* function/method, or a behavior-preserving delegation whose output is
byte-for-byte identical to today. If any item can't be done without altering existing behavior, stop and
flag it rather than shipping it.

## Implementer ground rules

- **Additive only.** New functions/classmethods, or a pure extract-and-delegate. Existing call sites and
  outputs must be unchanged. Run the existing test suite and confirm green before and after.
- **Two separate small PRs** for #1 and #2 (different files/concerns). #3–#5 are separate and later.
- **Git identity:** commit as `ghostiee-11` / `aman0611kumar@gmail.com`. Conventional commit messages
  (`feat:`, `fix:`, `refactor:`). No "Claude" co-author trailer. No em dashes in messages or PR text.
- **No GitHub issue numbers in docstrings/comments/tests.** Issue refs go only in the PR body / commit.
- **Do not tag maintainers.** Draft the PR text; the project owner reviews and posts it (do not post).
- Follow HoloViz AI-contribution rules: keep the number of open AI-assisted PRs small (~2), no large
  generated dumps, self-audit the diff before requesting review.

## Validation status (2026-07-08, local Lumen `1.2.0`, pixi env)

All claims below were checked with throwaway scripts before writing this doc:
- **#1 confirmed feasible & needed.** `VegaLiteAgent()._extract_spec({}, {"yaml_spec": ...})` runs with
  **no LLM and no server**, normalizing a bare spec. The logic is pure and cleanly extractable.
- **Rendering depends on it.** `pn.pane.Vega` **rejects a spec dict without `$schema`** ("Vega pane does
  not support objects of type 'dict'"). `_extract_spec` is what injects `$schema`, so normalization is a
  **hard prerequisite for rendering**, not optional polish. Order is fixed: *normalize → render → export.*
- **#2 confirmed OPTIONAL.** From pre-built views (no agent execution), lumen-mcp can already produce the
  downloadable **HTML** via `pn.Column(...).save(embed=True)` and the **notebook** via the public
  `lumen.ai.export` utilities (`format_output`, `make_preamble`, `write_notebook`, `make_md_cell`) — with
  **zero Lumen changes**. PNG works via `VegaLiteEditor.export("png")` (vl-convert, already a Lumen dep).
  So #2 is a *nice-to-have* API, not a blocker.

## Priority

| # | Change | Needed for MVP? | Effort | File |
|---|---|---|---|---|
| 1 | Expose Vega-Lite spec normalization as a public function | **Yes** (only real one) | S | `lumen/ai/agents/vega_lite.py` |
| 2 | `Report.from_views()` for prebuilt-view reports | No (existing exports suffice) | S | `lumen/ai/report.py` |
| 3 | Headless interface sink for `Coordinator` | Later (keyed layer) | M | `lumen/ai/coordinator/base.py` |
| 4 | Non-interactive execution mode | Later (keyed layer) | M | multiple agents/tools |
| 5 | `lumen mcp serve` CLI + `[mcp-server]` extra | Optional | M | Lumen CLI / `pyproject.toml` |

---

## Fix 1 — Expose Vega-Lite spec normalization as a public function  · MVP-relevant · PR #1

**Problem.** The non-LLM spec hardening lives inside an *instance method* on `VegaLiteAgent`:
`_extract_spec` (`lumen/ai/agents/vega_lite.py`, ~line 537). After parsing YAML/JSON it: injects
`$schema`, defaults `width`/`height` to `"container"` (skipping compound charts
`hconcat`/`vconcat`/`concat`/`facet`/`repeat`), calls `self._editor_type.validate_spec(vega_spec)`, and
adds geographic pan/zoom via `self._add_geographic_items`. To reuse this, an external caller must
instantiate a full `VegaLiteAgent` (which is designed around an LLM + context) just to normalize a dict.

**Additive change (behavior-preserving).** Add a module-level function holding the post-parse logic; the
method delegates to it. Output is identical.

```python
# NEW, module level in vega_lite.py
def normalize_vegalite_spec(vega_spec: dict, *, editor_type=VegaLiteEditor) -> dict:
    """Normalize + validate a Vega-Lite spec: $schema, sizing, compound charts, geo interactivity.
    Pure function: no LLM, no UI, no agent instance required."""
    ...  # exactly the current post-parse body of _extract_spec
    return {"spec": vega_spec, "sizing_mode": "stretch_both", "min_height": 200}


class VegaLiteAgent(BaseCodeAgent):
    async def _extract_spec(self, context, spec):
        vega_spec = load_yaml(spec["yaml_spec"]) if "yaml_spec" in spec else load_json(spec["json_spec"])
        return normalize_vegalite_spec(vega_spec, editor_type=self._editor_type)
```

**Check while implementing:** whether `_add_geographic_items` uses instance state (`self`). If it is pure,
lift it to a module function too and call it from `normalize_vegalite_spec`. If it genuinely needs `self`,
keep it on the class and have the function accept a callable / re-implement only the pure part — do NOT
change its behavior.

**Why it's non-breaking.** Pure `dict` in / `dict` out; `_extract_spec` returns exactly what it did (it
just calls the extracted function). No existing call site changes.

**Zero-touch alternative** (if maintainers prefer not to touch `_extract_spec` at all): add
`normalize_vegalite_spec` as a standalone function and leave `_extract_spec` as-is. Slight duplication,
but literally zero risk to existing behavior. (Recommended primary is the delegate above — DRY and still
non-breaking.)

**How lumen-mcp consumes it.**
- *Before this PR merges:* a shim in lumen-mcp calls the private method — `VegaLiteAgent()._extract_spec({}, {"yaml_spec": dump_yaml(host_spec)})["spec"]` (validated to run with no key/server).
- *After merge:* `from lumen.ai.agents.vega_lite import normalize_vegalite_spec`.

**Tests.** Existing `VegaLiteAgent` tests must stay green. Add a unit test: `normalize_vegalite_spec`
on a bare `{"mark": "bar", "encoding": {...}}` returns a spec with `$schema`, `width`/`height` set, and
`VegaLiteEditor.validate_spec` passing.

**PR draft (title/body — owner posts):**
- Title: `refactor: expose vega-lite spec normalization as a reusable function`
- Body (why, in first person, no em dashes): normalization currently lives on `VegaLiteAgent._extract_spec`
  and can only be reached by instantiating an agent. Extracting the pure part into
  `normalize_vegalite_spec()` lets it be reused for rendering embedded specs headlessly. Behavior of
  `_extract_spec` is unchanged; it now delegates. Adds a unit test. Before/after: none needed (no UI change).

---

## Fix 2 — `Report.from_views()` for prebuilt-view reports  · optional · PR #2

**Status: not required.** lumen-mcp already produces the downloadable report with **zero Lumen changes**:
- HTML: `pn.Column(<markdown>, <view>.get_panel(), ...).save(buf, embed=True)` (self-contained, offline).
- Notebook: `lumen.ai.export.format_output(editor)` + `make_preamble(...)` + `write_notebook(...)` (public).

Pursue this PR only if we want a tidier, first-class API. It is a clean additive convenience.

**Problem it solves.** `Report.to_html()` / `to_notebook()` (`lumen/ai/report.py`, ~lines 671 / 628)
assume an *executed* report. There is no one-liner to assemble a `Report` from already-built views.

**Additive change.** A classmethod (proven recipe below):
```python
@classmethod
def from_views(cls, views, title=None):
    """Build an exportable Report from prebuilt views (no agent execution)."""
    report = cls(title=title)                                   # zero tasks
    report._view[:] = [(getattr(v, "title", "") or "", v) for v in views]  # _view is an Accordion
    report.views = list(views)                                  # used by to_notebook
    report.status = "success"
    return report
```
Validated: with a zero-task Report, `to_html()` and `to_notebook()` both work and contain the chart (the
`status`/`len` guard short-circuits for zero tasks, so no existing guard needs relaxing).

**Why it's non-breaking.** New classmethod only. The execute → export path and the existing guards are
untouched. Do **not** relax the `status == "success"` guard (that would change existing behavior).

**Tests.** Build from `[Markdown("# T"), VegaLiteEditor(component=view)]`; assert `to_html()` returns
offline HTML containing the chart and `to_notebook()` returns valid `nbformat` JSON.

**PR draft:** Title `feat: add Report.from_views for assembling reports from prebuilt views`. Body: note
it is additive, existing paths unchanged, includes a test.

---

## Fix 3 — Headless interface sink for `Coordinator`  · keyed layer · NEEDS SPIKE

**Only needed for the later "keyed" mode**, where Lumen's real `SQLAgent`/`VegaLiteAgent`/`Planner` run
server-side. `Coordinator.__init__` fabricates a Panel `ChatInterface` when `interface=None`
(`lumen/ai/coordinator/base.py`, ~line 354), so there is no true headless mode — steps/clarifications
render to an interface nobody sees.

**Additive direction.** Support a no-op `ChatFeed` sink (e.g. `interface=False`, or a `HeadlessInterface`
that captures steps/messages as text and renders nothing). Passing a real interface stays unchanged.

**Before PR:** run a feasibility spike (like the #1/#2 validations) — instantiate a `Planner` with a real
LLM + the headless sink against a sample DuckDB db, run one query, and confirm the full plan executes
without touching a live UI. Only then size and open the PR. Not validated yet.

---

## Fix 4 — Non-interactive execution mode  · keyed layer · NEEDS SPIKE (largest)

**Only for keyed mode.** Some agents block on human input when headless: `VegaLiteAgent` code mode can
raise `UserCancelledError` (`lumen/ai/agents/vega_lite.py`, ~line 528); `SourceAgent` and the clarification
tools expect user answers.

**Additive direction.** An `interactive=False` config that (a) forces declarative Vega (no code-execution
confirmation gate), (b) relies on pre-registered sources, and (c) auto-resolves or surfaces clarifications
instead of blocking. This touches multiple agents/tools, so it is the largest item and the most likely to
risk behavior change — scope it carefully and keep the default (`interactive=True`) identical to today.
Spike first; likely split into sub-PRs.

---

## Fix 5 — `lumen mcp serve` CLI + `[mcp-server]` extra  · optional

If maintainers want the server upstream, add a `lumen mcp serve` subcommand and a `[mcp-server]` extra,
complementing the existing `lumen[mcp]` *client* extra. Purely additive. Pursue only if the maintainer
discussion is positive; not required for the standalone product.

---

## Reproducing the validation

The feasibility checks that back this doc (spec normalization with no LLM; keyless HTML/PNG/ipynb export;
the `Report.from_views` recipe) were run against the local Lumen checkout in its pixi env:

```
~/.pixi/bin/pixi run --manifest-path <lumen>/pixi.toml python <script>
```

Minimal shape of the proof (see project owner for the exact scripts):
1. `DuckDBSource.from_df({"sales": df}).create_sql_expr_source({"q": sql}, materialize=True)` → real table.
2. `Pipeline(source, table="q")`.
3. `normalized = (await VegaLiteAgent()._extract_spec({}, {"yaml_spec": dump_yaml(raw_spec)}))["spec"]`.
4. `VegaLiteView(pipeline, spec=normalized).get_panel()` → `pn.pane.Vega` (renders only because step 3 added `$schema`).
5. `VegaLiteEditor(component=view).export("png")` → PNG bytes; `pn.Column(...).save(embed=True)` → offline HTML;
   `lumen.ai.export` utils → valid `.ipynb`.
