import os
from agentmake import PACKAGE_PATH, AGENTMAKE_USER_DIR, readTextFile

def get_system_suggestion(master_plan: str) -> str:
    """
    create system prompt for suggestion
    """
    possible_system_file_path_2 = os.path.join(PACKAGE_PATH, "systems", "xomate", "supervisor.md")
    possible_system_file_path_1 = os.path.join(AGENTMAKE_USER_DIR, "systems", "xomate", "supervisor.md")
    return readTextFile(possible_system_file_path_2 if os.path.isfile(possible_system_file_path_2) else possible_system_file_path_1).format(master_plan=master_plan)

def get_system_tool_instruction(tool: str, tool_description: str = "") -> str:
    """
    create system prompt for tool instruction
    """
    possible_system_file_path_2 = os.path.join(PACKAGE_PATH, "systems", "xomate", "tool_instruction.md")
    possible_system_file_path_1 = os.path.join(AGENTMAKE_USER_DIR, "systems", "xomate", "tool_instruction.md")
    return readTextFile(possible_system_file_path_2 if os.path.isfile(possible_system_file_path_2) else possible_system_file_path_1).format(tool=tool, tool_description=tool_description)

def get_system_tool_selection(available_tools: list, tool_descriptions: str) -> str:
    """
    create system prompt for tool selection
    """
    possible_system_file_path_2 = os.path.join(PACKAGE_PATH, "systems", "xomate", "tool_selection.md")
    possible_system_file_path_1 = os.path.join(AGENTMAKE_USER_DIR, "systems", "xomate", "tool_selection.md")
    return readTextFile(possible_system_file_path_2 if os.path.isfile(possible_system_file_path_2) else possible_system_file_path_1).format(available_tools=available_tools, tool_descriptions=tool_descriptions)
