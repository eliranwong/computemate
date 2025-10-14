from fastmcp import FastMCP
mcp = FastMCP(name="Server B")
@mcp.resource("echob://{content}")
def echob(content:str) -> str:
    """Echo content in server A"""
    return content
mcp.run(show_banner=False)