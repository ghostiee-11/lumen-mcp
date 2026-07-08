"""Live MCP round-trip through FastMCP's in-memory client.

Exercises the real protocol path (list_tools + call_tool) rather than the tool functions directly.
Requires ``fastmcp``. Run with:
    python tests/test_roundtrip.py
or under pytest.
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "examples"))

import make_sample_db  # noqa: E402
from fastmcp import Client  # noqa: E402

from lumen_mcp.server import mcp  # noqa: E402

_EXPECTED_TOOLS = {
    "connect_source", "list_tables", "describe_table", "run_sql",
    "render_vegalite", "refine_chart", "list_charts", "build_report",
}


def _data(result):
    """Extract the structured return value from a FastMCP CallToolResult."""
    if getattr(result, "data", None) is not None:
        return result.data
    if getattr(result, "structured_content", None) is not None:
        return result.structured_content
    return json.loads(result.content[0].text)


async def _run() -> None:
    db = os.path.join(tempfile.mkdtemp(), "sample.db")
    make_sample_db.main(db)

    async with Client(mcp) as client:
        tools = {tool.name for tool in await client.list_tools()}
        assert _EXPECTED_TOOLS.issubset(tools), tools
        print("tools:", sorted(tools))

        connected = _data(await client.call_tool("connect_source", {"uri": db}))
        assert "sales" in connected["tables"], connected
        print("connect_source:", connected)

        result = _data(await client.call_tool(
            "run_sql",
            {"sql": "SELECT region, SUM(amount) AS total FROM sales GROUP BY region ORDER BY total DESC",
             "name": "by_region"},
        ))
        assert result["row_count"] == 4, result
        print("run_sql:", {key: result[key] for key in ("table", "row_count", "columns")})

        spec = {
            "mark": "bar",
            "encoding": {
                "x": {"field": "region", "type": "nominal", "sort": "-y"},
                "y": {"field": "total", "type": "quantitative"},
            },
        }
        chart = _data(await client.call_tool("render_vegalite", {"spec": spec, "table": "by_region"}))
        assert chart["html_path"] and os.path.exists(chart["html_path"]), chart
        print("render_vegalite:", {key: chart[key] for key in ("chart_id", "png_path", "html_path")})

        rep = _data(await client.call_tool(
            "build_report",
            {"items": [{"markdown": "# Sales"}, {"chart": chart["chart_id"]}], "title": "Sales"},
        ))
        assert os.path.exists(rep["html_path"]) and os.path.exists(rep["ipynb_path"]), rep
        print("build_report:", {key: rep.get(key) for key in ("html_path", "ipynb_path")})

    print("ROUND-TRIP PASS")


def test_roundtrip() -> None:
    asyncio.run(_run())


if __name__ == "__main__":
    test_roundtrip()
