import asyncio
import sys
from mcp.client.stdio import stdio_client, StdioServerParameters
from mcp import ClientSession

async def main():
    params = StdioServerParameters(command=sys.executable, args=['mcp_server/server.py'])
    async with stdio_client(params) as streams:
        async with ClientSession(*streams) as session:
            await session.initialize()
            resp = await session.list_tools()
            print("Tool object dir:")
            print(dir(resp.tools[0]))
            print("Tool name:", resp.tools[0].name)
            if hasattr(resp.tools[0], 'inputSchema'):
                print("inputSchema:", resp.tools[0].inputSchema)
            else:
                print("No inputSchema!")
            if hasattr(resp.tools[0], 'input_schema'):
                print("input_schema:", resp.tools[0].input_schema)
            else:
                print("No input_schema!")

if __name__ == "__main__":
    asyncio.run(main())
