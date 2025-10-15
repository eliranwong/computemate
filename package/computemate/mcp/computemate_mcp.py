import logging, json, os
from fastmcp.server.auth.providers.jwt import StaticTokenVerifier
from fastmcp.server.auth.providers.jwt import JWTVerifier
from fastmcp import FastMCP
from fastmcp.prompts.prompt import PromptMessage, TextContent
from agentmake import agentmake, DEVELOPER_MODE, readTextFile
from computemate import COMPUTEMATE_VERSION, COMPUTEMATE_PACKAGE_PATH, COMPUTEMATEDATA, AGENTMAKE_CONFIG, config
from typing import List, Dict, Any, Union
from tabulate import tabulate

# configure backend
AGENTMAKE_CONFIG["backend"] = config.backend

# Configure logging before creating the FastMCP server
logging.basicConfig(format="[%(levelname)s]: %(message)s", level=logging.ERROR)

COMPUTEMATE_STATIC_TOKEN = os.getenv("COMPUTEMATE_STATIC_TOKEN")
COMPUTEMATE_MCP_PUBLIC_KEY = os.getenv("COMPUTEMATE_MCP_PUBLIC_KEY")

verifier = StaticTokenVerifier(
    tokens={
        COMPUTEMATE_STATIC_TOKEN: {
            "client_id": "computemate-ai",
            "scopes": ["read:data", "write:data", "admin:users"]
        },
    },
    required_scopes=["read:data"]
) if COMPUTEMATE_STATIC_TOKEN else JWTVerifier(
    public_key=COMPUTEMATE_MCP_PUBLIC_KEY,
    issuer=os.getenv("COMPUTEMATE_MCP_ISSUER"),
    audience=os.getenv("COMPUTEMATE_MCP_AUDIENCE")
) if COMPUTEMATE_MCP_PUBLIC_KEY else None

mcp = FastMCP(name="ComputeMate AI", auth=verifier)

def getResponse(messages:list) -> str:
    return messages[-1].get("content") if messages and "content" in messages[-1] else "Error!"

@mcp.resource("resource://info")
def info() -> str:
    """Display ComputeMate AI information"""
    info = "ComputeMate AI " + COMPUTEMATE_VERSION
    info += "\n\nSource: https://github.com/eliranwong/computemate\n\nDeveloper: Eliran Wong"
    return info

@mcp.resource("ls://{directory}")
def ls(directory:str) -> str:
    """List content of a directory"""
    directory = os.path.expanduser(directory.replace("%2F", "/"))
    if os.path.isdir(directory):
        folders = []
        files = []
        for item in sorted(os.listdir(directory)):
            if os.path.isdir(os.path.join(directory, item)):
                folders.append(f"📁 {item}")
            else:
                files.append(f"📄 {item}")
        return " ".join(folders) + "\n\n" + " ".join(files)
    return "Invalid path!"

@mcp.tool
def execute_task(request:str) -> str:
    """execute computing tasks or retrieve computer information"""
    global agentmake, getResponse
    messages = agentmake(request, **{'tool': 'execute_task'}, **AGENTMAKE_CONFIG)
    return getResponse(messages)

mcp.run(show_banner=False)