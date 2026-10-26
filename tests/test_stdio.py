"""Exercise the installed entry point with the official MCP stdio client."""

import asyncio
import sys
import unittest

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


class StdioTests(unittest.IsolatedAsyncioTestCase):
    async def test_handshake_ping_schema_and_tool_errors(self):
        async with asyncio.timeout(30):
            server = StdioServerParameters(
                command=sys.executable, args=["-m", "codex_deepseek"],
                # Explicit empty env value prevents touching real Keychain or API.
                env={"DEEPSEEK_API_KEY": ""},
            )
            async with stdio_client(server) as (reader, writer):
                async with ClientSession(reader, writer) as session:
                    initialized = await session.initialize()
                    self.assertEqual(initialized.serverInfo.name, "deepseek-discuss")
                    await session.send_ping()
                    listed = await session.list_tools()
                    self.assertEqual([tool.name for tool in listed.tools], ["ask_deepseek"])
                    tool = listed.tools[0]
                    self.assertTrue(tool.annotations.readOnlyHint)
                    self.assertIn("prompt", tool.inputSchema["required"])
                    invalid = await session.call_tool("ask_deepseek", {"prompt": ""})
                    self.assertTrue(invalid.isError)
                    missing = await session.call_tool("ask_deepseek", {"prompt": "test"})
                    self.assertTrue(missing.isError)
                    unknown = await session.call_tool("does_not_exist", {})
                    self.assertTrue(unknown.isError)


if __name__ == "__main__":
    unittest.main()
