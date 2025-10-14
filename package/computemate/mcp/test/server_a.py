from fastmcp import FastMCP
mcp = FastMCP(name="Server A")
@mcp.resource("echoa://{content}")
def echoa(content:str) -> str:
    """Echo content in server A"""
    return content
mcp.run(show_banner=False)