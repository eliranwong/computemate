import logging, json, os
from fastmcp.server.auth.providers.jwt import StaticTokenVerifier
from fastmcp.server.auth.providers.jwt import JWTVerifier
from fastmcp import FastMCP
from fastmcp.prompts.prompt import PromptMessage, TextContent
from agentmake import agentmake, DEVELOPER_MODE, readTextFile
from agentmake.utils.system import getDeviceInfo
from computemate import COMPUTEMATE_VERSION, COMPUTEMATE_PACKAGE_PATH, COMPUTEMATEDATA, AGENTMAKE_CONFIG, config, list_dir_content
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
    """Show ComputeMate AI information"""
    info = "ComputeMate AI " + COMPUTEMATE_VERSION
    info += "\n\nSource: https://github.com/eliranwong/computemate\n\nDeveloper: Eliran Wong"
    return info

@mcp.resource("resource://device")
def device() -> str:
    """Show Device Information"""
    return "- "+getDeviceInfo().replace("\n", "\n- ")

@mcp.resource("ls://{directory}")
def ls(directory:str) -> str:
    """List content of a directory"""
    return list_dir_content(directory)

@mcp.tool
def execute_task(request:str) -> str:
    """Execute any computing tasks or retrieve computer information

Args [required]:
    code: Generate Python code that integrates any relevant packages to resolve my request
    title: Title for the task

Args [optional]:
    risk: Assess the risk level of damaging my device upon executing the task. e.g. file deletions or similar significant impacts are regarded as 'high' level.
"""
    return ""

@mcp.tool
def ask_files(request:str) -> str:
    """ask questions about files content; a file list is required

Args [required]:
    question: The original question about the files
    list_of_files_or_folders: Return a list of file or folder paths, e.g. ['/path/folder1', '/path/folder2', '/path/file1', '/path/file2']. Return an empty string '' if there is no file or folder specified.
"""
    global agentmake, getResponse
    messages = agentmake(request, **{'tool': 'rag/files'}, **AGENTMAKE_CONFIG)
    return getResponse(messages)

@mcp.tool
def extract_text(request:str) -> str:
    """extract text from a single file or url; a file path or an url is required

Args [required]:
    filepath_or_url: Either a file path or an url. Return an empty string '' if not given.
"""
    global agentmake, getResponse
    messages = agentmake(request, **{'tool': 'files/extract_text'}, **AGENTMAKE_CONFIG)
    return getResponse(messages)

@mcp.tool
def memory_in(request:str) -> str:
    """Use this tool if I mention something which you think would be useful in the future and should be saved as a memory. Saved memories will allow you to retrieve snippets of past conversations when needed.

Args [required]:
    content: Detailed description of the memory content. I would like you to help me with converting relative dates and times, if any, into exact dates and times, based on the reference that the current datetime is 2025-10-15 19:05:25 (Wednesday).
    title: Generate a title for this memory
    category: Select a category that is the most relevant to this memory: ['general', 'instruction', 'fact', 'event', 'concept']
"""
    global agentmake, getResponse
    messages = agentmake(request, **{'input_content_plugin': 'convert_relative_datetime', 'tool': 'memory/in'}, **AGENTMAKE_CONFIG)
    return getResponse(messages)

@mcp.tool
def memory_out(request:str) -> str:
    """Recall memories of important conversation snippets that we had in the past.

Args [required]:
    query: The query to be used for searching memories from a vector database. I would like you to help me with converting relative dates and times, if any, into exact dates and times, based on the reference that the current datetime is 2025-10-15 19:05:25 (Wednesday).
"""
    global agentmake, getResponse
    messages = agentmake(request, **{'input_content_plugin': 'convert_relative_datetime', 'tool': 'memory/out'}, **AGENTMAKE_CONFIG)
    return getResponse(messages)

mcp.run(show_banner=False)