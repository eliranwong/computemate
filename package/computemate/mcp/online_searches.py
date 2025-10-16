from fastmcp import FastMCP
from agentmake import agentmake
from computemate import config, AGENTMAKE_CONFIG
import logging, os

# configure backend
AGENTMAKE_CONFIG["backend"] = config.backend

# Configure logging before creating the FastMCP server
logging.basicConfig(format="[%(levelname)s]: %(message)s", level=logging.ERROR)

mcp = FastMCP(name="Online Search Utilities")

def getResponse(messages:list) -> str:
    return messages[-1].get("content") if messages and "content" in messages[-1] else "Error!"

@mcp.tool
def conduct_research(request:str) -> str:
    """Conduct an online research on a topic or question; research query is required"""
    global agentmake, getResponse
    messages = agentmake(request, **{'tool': 'perplexica/googleai'}, **AGENTMAKE_CONFIG)
    return getResponse(messages)

@mcp.tool
def search_news(request:str) -> str:
    """Perform online searches for up-to-date and real-time news information; keyword(s) for searching are required

Args [required]:
    keywords: Keywords for online news searches
"""
    global agentmake, getResponse
    messages = agentmake(request, **{'tool': 'search/searxng_news'}, **AGENTMAKE_CONFIG)
    return getResponse(messages)

@mcp.tool
def search_web(request:str) -> str:
    """Perform online searches to obtain the latest and most up-to-date, real-time information; keyword(s) for searching are required

Args [required]:
    keywords: Keywords for online searches

Args [optional]:
    category: choose the most relevant category from ["general", "translate", "web", "wikimedia", "images", "videos", "news", "map", "music", "lyrics", "radio", "it", "packages", "repos", "software_wikis", "science", "scientific_publications", "files", "apps", "social_media"]
"""
    global agentmake, getResponse
    messages = agentmake(request, **{'tool': 'search/searxng'}, **AGENTMAKE_CONFIG)
    return getResponse(messages)

mcp.run(show_banner=False)