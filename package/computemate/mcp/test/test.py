from fastmcp import Client
import os, asyncio

server_a_script = '''from fastmcp import FastMCP
mcp = FastMCP(name="Server A")
@mcp.resource("echoa://{content}")
def echoa(content:str) -> str:
    """Echo content in server A"""
    return content
mcp.run(show_banner=False)'''
with open("server_a.py", "w") as fileObj:
    fileObj.write(server_a_script)

server_b_script = '''from fastmcp import FastMCP
mcp = FastMCP(name="Server B")
@mcp.resource("echob://{content}")
def echob(content:str) -> str:
    """Echo content in server A"""
    return content
mcp.run(show_banner=False)'''
with open("server_b.py", "w") as fileObj:
    fileObj.write(server_b_script)

cwd = os.getcwd()
config = {
    "mcpServers": {
        "servera": {"command": "python", "args": [os.path.join(cwd, "server_a.py")]},
        "serverb": {"command": "python", "args": [os.path.join(cwd, "server_b.py")]},
    }
}
client = Client(config)

async def main_async():
    async with client:
        # check templates
        templates = await client.list_resource_templates()
        print(templates)
        try:
            uri = "echob://serverb/helloB"
            resource_content = await client.read_resource(uri)
            print(resource_content[0].text)
        except Exception as e:
            print(f"Error: {e}\n")


def main():
    asyncio.run(main_async())

if __name__ == "__main__":
    main()