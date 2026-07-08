"""Visualization tools: render a host-authored Vega-Lite spec against a workspace table.

Flow (all reuse, no LLM): normalize the spec (adds ``$schema`` etc.) -> bind the table via a Lumen
``Pipeline`` -> ``VegaLiteView`` -> PNG + self-contained HTML.
"""

from __future__ import annotations

from typing import Optional

from lumen.pipeline import Pipeline
from lumen.views import VegaLiteView

from . import rendering
from ._shims import normalize_spec
from .session import session


def render_vegalite(spec: dict, table: str, chart_id: Optional[str] = None) -> dict:
    """Render a Vega-Lite ``spec`` bound to workspace ``table``.

    The spec should reference field names but omit ``data`` (the server injects the table's data).
    Returns the normalized spec, a ``chart_id``, and paths to a PNG preview and a self-contained
    HTML file.
    """
    source = session.require_source()
    rendering._ensure_panel()

    normalized = normalize_spec(spec)["spec"]
    view = VegaLiteView(pipeline=Pipeline(source=source, table=table), spec=normalized)

    cid = chart_id or session.next_chart_id()
    session.charts[cid] = {"view": view, "spec": normalized, "table": table}

    return {
        "chart_id": cid,
        "table": table,
        "spec": normalized,
        "png_path": rendering.save_png(view, cid),
        "html_path": rendering.save_html(view, cid),
    }
