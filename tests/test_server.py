import json

import pytest

from asalbanoo_mcp.server import compact


@pytest.mark.anyio
async def test_compact_is_single_minified_utf8_json():
    async def tool():
        return {"title": "عسل", "n": [1, 2]}

    assert await compact(tool)() == '{"title":"عسل","n":[1,2]}'


@pytest.mark.anyio
async def test_client_gets_one_text_block_and_no_output_schema(api):
    from mcp import Client
    from mcp.types import TextContent

    from asalbanoo_mcp.server import mcp

    api["/wp-json/wp/v2/product_cat"] = []
    async with Client(mcp) as c:
        result = await c.call_tool("ab_categories", {})
        tools = (await c.list_tools()).tools
    assert len(result.content) == 1 and isinstance(result.content[0], TextContent)
    assert result.structured_content is None
    assert all(t.output_schema is None for t in tools)
    assert '"title":"' not in json.dumps(tools[0].input_schema)  # pydantic title noise stripped
