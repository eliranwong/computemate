import logging, json, os, pydoc, shutil, re
from fastmcp.server.auth.providers.jwt import StaticTokenVerifier
from fastmcp.server.auth.providers.jwt import JWTVerifier
from fastmcp import FastMCP
from fastmcp.prompts.prompt import PromptMessage, TextContent
from agentmake import agentmake, DEVELOPER_MODE, readTextFile, writeTextFile, extractText
from agentmake.utils.system import getDeviceInfo
from computemate import COMPUTEMATE_VERSION, COMPUTEMATE_PACKAGE_PATH, COMPUTEMATEDATA, AGENTMAKE_CONFIG, config, list_dir_content
from typing import List, Dict, Any, Union

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

def export_text_to_docx_file(docx_file_path:str, text_content:str) -> str:
    if not shutil.which("pandoc"):
        print("Required tool 'pandoc' is not found on your system! Read https://pandoc.org/installing.html for installation.")
        return ""
    if not docx_file_path.endswith(".docx"):
        docx_file_path = f"{docx_file_path}.docx"
    pydoc.pipepager(text_content, cmd=f'''pandoc -f markdown -t docx -o "{docx_file_path}"''')
    return f"File saved: {docx_file_path}"

def export_text_to_pdf_file(pdf_file_path:str, text_content:str) -> str:
    if not shutil.which("pandoc"):
        print("Required tool 'pandoc' is not found on your system! Read https://pandoc.org/installing.html for installation.")
        return ""
    elif not shutil.which("pdflatex"):
        print("Required tool 'pdflatex' is not found on your system! Read https://pandoc.org/installing.html for installation.")
        return ""
    if not pdf_file_path.endswith(".pdf"):
        pdf_file_path = f"{pdf_file_path}.pdf"
    pydoc.pipepager(text_content, cmd=f'''pandoc -f markdown -t pdf -o "{pdf_file_path}"''')
    return f"File saved: {pdf_file_path}"

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

@mcp.resource("content://{directory}")
def content(directory:str) -> str:
    """List content of a directory"""
    return list_dir_content(directory)

# python

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
def install_python_package(request:str) -> str:
    """Install a python pip package or library; a python pip package name is required

Args [required]:
    python_package_name: Python package name
"""
    global agentmake, getResponse
    messages = agentmake(request, **{'tool': 'install_python_package'}, **AGENTMAKE_CONFIG)
    return getResponse(messages)

# screenshot

@mcp.tool
def take_screenshot(request:str) -> str:
    """Take a screenshot and save it in a file

Args [required]:
    filepath_or_filename: The file path or name for saving the screenshot; return "screenshot.png" if it is not given.
"""
    global agentmake, getResponse
    messages = agentmake(request, **{'tool': 'screenshot'}, **AGENTMAKE_CONFIG)
    return getResponse(messages)

# memory

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

# files

@mcp.tool
def read_text_file(text_file_path:str) -> str:
    """Read the text content of a text file; a file path is required

Args [required]:
    text_file_path: the file path of the text file to be read
"""
    return readTextFile(text_file_path)

@mcp.tool
def write_text_file(text_file_path:str, text_content:str) -> str:
    """Write text content into a text file; text content and a file path are required

Args [required]:
    text_file_path: the file path of the text file to be written
    text_content: the text content to be written into the file
"""
    writeTextFile(text_file_path, text_content)
    return f"File saved: {text_file_path}"

@mcp.tool
def extract_file_text(request:str) -> str:
    """Extract the text from a non-plain text file or from a webpage and convert it into Markdown format; a file path or URL is required.

Args [required]:
    filepath_or_url: Either a file path or an url. Return an empty string '' if not given.
"""
    global agentmake, getResponse
    messages = agentmake(request, **{'tool': 'files/extract_text'}, **AGENTMAKE_CONFIG)
    return getResponse(messages)

@mcp.tool
def write_pdf_file(pdf_file_path:str, markdown_content:str) -> str:
    """Write markdown text string into a pdf file; text in markdown format and a file path are required

Args [required]:
    pdf_file_path: the file path of the pdf file to be written
    markdown_content: the markdown text content to be written into the file
"""
    return export_text_to_pdf_file(pdf_file_path, markdown_content)

@mcp.tool
def write_docx_file(docx_file_path:str, markdown_content:str) -> str:
    """Write markdown text string into a word document docx file; text in markdown format and a file path are required

Args [required]:
    docx_file_path: the file path of the word document docx file to be written
    markdown_content: the markdown text content to be written into the file
"""
    return export_text_to_docx_file(docx_file_path, markdown_content)

@mcp.tool
def convert_file_to_pdf_format(input_file_path:str) -> str:
    """Convert a given file into a pdf file format; a file path is required

Args [required]:
    input_file_path: the file path of the input file to be converted
"""
    markdown_content = readTextFile(input_file_path) if re.search(r"\.(txt|md|markdown)$", input_file_path.lower()) else extractText(input_file_path)
    input_file_path = re.sub(r"\.[a-z]+?$", "", input_file_path)
    pdf_file_path = input_file_path+".pdf"
    return export_text_to_pdf_file(pdf_file_path, markdown_content)

@mcp.tool
def convert_file_to_docx_format(input_file_path:str) -> str:
    """Convert a given file into a docx word document format; a file path is required

Args [required]:
    input_file_path: the file path of the input file to be converted
"""
    markdown_content = readTextFile(input_file_path) if re.search(r"\.(txt|md|markdown)$", input_file_path.lower()) else extractText(input_file_path)
    input_file_path = re.sub(r"\.[a-z]+?$", "", input_file_path)
    docx_file_path = input_file_path+".docx"
    return export_text_to_docx_file(docx_file_path, markdown_content)

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

# emails and calendars

@mcp.tool
def email_gmail(request:str) -> str:
    """Send Gmail

Args [required]:
    email_title: Give a title to the email.
    email_content: The body or content of the email.

Args [optional]:
    email_address: The recipient of the email.
"""
    return ""

@mcp.tool
def email_outlook(request:str) -> str:
    """Send Gmail

Args [required]:
    email_title: Give a title to the email.
    email_content: The body or content of the email.

Args [optional]:
    email_address: The recipient of the email.
"""
    return ""

@mcp.tool
def calendar_google(request:str) -> str:
    """Add a Google calendar event

Args [required]:
    title: The title of the event.
    description: The detailed description of the event, including the people involved and their roles, if any.

Args [optional]:
    url: Event url
    start_time: The start date and time of the event in the format `YYYYMMDDTHHmmss`. For example, `20220101T100000` represents January 1, 2022, at 10:00 AM. Calculate the exact dates and times from the relative ones, if any, based on the reference that the current datetime is 2025-10-16 16:39:29 (Thursday).
    end_time: The end date and time of the event in the format `YYYYMMDDTHHmmss`. For example, `20220101T100000` represents January 1, 2022, at 10:00 AM. Calculate the exact dates and times from the relative ones, if any, based on the reference that the current datetime is 2025-10-16 16:39:29 (Thursday). If not given, return 1 hour later than the start_time
    location: The location or venue of the event.
"""
    return ""

@mcp.tool
def calendar_outlook(request:str) -> str:
    """Add a Google calendar event

Args [required]:
    title: The title of the event.
    description: The detailed description of the event, including the people involved and their roles, if any.

Args [optional]:
    url: Event url
    start_time: The start date and time of the event in the format `YYYYMMDDTHHmmss`. For example, `20220101T100000` represents January 1, 2022, at 10:00 AM. Calculate the exact dates and times from the relative ones, if any, based on the reference that the current datetime is 2025-10-16 16:39:29 (Thursday).
    end_time: The end date and time of the event in the format `YYYYMMDDTHHmmss`. For example, `20220101T100000` represents January 1, 2022, at 10:00 AM. Calculate the exact dates and times from the relative ones, if any, based on the reference that the current datetime is 2025-10-16 16:39:29 (Thursday). If not given, return 1 hour later than the start_time
    location: The location or venue of the event.
"""
    return ""

@mcp.tool
def teamwork(request:str) -> str:
    """Assemble a team of AI agents to collaborate, with each contributing their specialized expertise to effectively fulfill the user's request and deliver a comprehensive text-based solution."""
    return ""

@mcp.tool
def reflection_agent(request:str) -> str:
    """Carefully consider the user’s query and thoroughly review the solution before providing an answer."""
    return ""

@mcp.tool
def reasoning_agent(request:str) -> str:
    """Analyze the user's query with reasoning, develop a well-reasoned solution, and refine it before providing an answer."""
    return ""

mcp.run(show_banner=False)