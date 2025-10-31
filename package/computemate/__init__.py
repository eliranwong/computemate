from agentmake import USER_OS, AGENTMAKE_USER_DIR, DEFAULT_TEXT_EDITOR, readTextFile, writeTextFile
from pathlib import Path
from computemate import config
from computemate.ui.selection_dialog import TerminalModeDialogs
import os, shutil, pprint, subprocess

COMPUTEMATE_USER_DIR = os.path.join(AGENTMAKE_USER_DIR, "computemate")
if not os.path.isdir(COMPUTEMATE_USER_DIR):
    Path(COMPUTEMATE_USER_DIR).mkdir(parents=True, exist_ok=True)
CONFIG_FILE_BACKUP = os.path.join(COMPUTEMATE_USER_DIR, "computemate.config")

# NOTE: When add a config item, update both `default_config` and `write_user_config`

def write_user_config(backup=False):
    """Writes the current configuration to the user's config file."""
    configurations = f"""config.banner_title="{config.banner_title}"
config.agent_mode={config.agent_mode}
config.prompt_engineering={config.prompt_engineering}
config.auto_suggestions={config.auto_suggestions}
config.auto_tool_selection={config.auto_tool_selection}
config.auto_code_correction={config.auto_code_correction}
config.max_steps={config.max_steps}
config.light={config.light}
config.web_browser={config.web_browser}
config.hide_tools_order={config.hide_tools_order}
config.skip_connection_check={config.skip_connection_check}
config.max_semantic_matches={config.max_semantic_matches}
config.max_log_lines={config.max_log_lines}
config.mcp_port={config.mcp_port}
config.mcp_timeout={config.mcp_timeout}
config.color_agent_mode="{config.color_agent_mode}"
config.color_partner_mode="{config.color_partner_mode}"
config.color_info_border="{config.color_info_border}"
config.embedding_model="{config.embedding_model}"
config.custom_input_suggestions={pprint.pformat(config.custom_input_suggestions)}
config.disabled_tools={pprint.pformat(config.disabled_tools)}"""
    writeTextFile(CONFIG_FILE_BACKUP, configurations)

# restore config backup after upgrade
default_config = '''config.banner_title=""
config.agent_mode=None
config.prompt_engineering=False
config.auto_suggestions=True
config.auto_tool_selection=True
config.auto_code_correction=True
config.max_steps=50
config.light=False
config.web_browser=False
config.hide_tools_order=True
config.skip_connection_check=False
config.max_semantic_matches=15
config.max_log_lines=2000
config.mcp_port=33333
config.mcp_timeout=9999999999
config.color_agent_mode="#FF8800"
config.color_partner_mode="#8000AA"
config.color_info_border="bright_blue"
config.embedding_model="paraphrase-multilingual"
config.custom_input_suggestions=[]
config.disabled_tools=[]'''

def load_config():
    """Loads the user's configuration from the config file."""
    if not os.path.isfile(CONFIG_FILE_BACKUP):
        exec(default_config, globals())
        write_user_config()
    else:
        exec(readTextFile(CONFIG_FILE_BACKUP), globals())
    # check if new config items are added
    changed = False
    for config_item in default_config[7:].split("\nconfig."):
        key, _ = config_item.split("=", 1)
        if not hasattr(config, key):
            exec(f"config.{config_item}", globals())
            changed = True
    if changed:
        write_user_config()

# load user config at startup
load_config()

# temporary config
config.current_prompt = ""
config.cancelled = False
config.backup_required = False
config.export_item = ""
config.action_list = {
    # general
    ".ideas": "generate ideas for prompts to try",
    ".exit": "exit current prompt",
    # conversations
    ".new": "new conversation",
    ".trim": "trim conversation",
    ".edit": "edit conversation",
    ".reload": "reload conversation",
    ".import": "import conversation",
    ".export": "export conversation",
    ".backup": "backup conversation",
    ".find": "search conversation",
    # resource information
    ".tools": "list available tools",
    ".plans": "list available plans",
    ".resources": "list available resources",
    # configurations
    ".backend": "configure backend",
    ".mcp": "configure MCP servers",
    ".steps": "configure the maximum number of steps allowed",
    ".matches": "configure the maximum number of semantic matches",
    ".mode": "configure AI mode",
    #".agent": "switch to agent mode",
    #".partner": "switch to partner mode",
    #".chat": "switch to chat mode",
    ".autosuggest": "toggle auto input suggestions",
    ".autoprompt": "toggle auto prompt engineering",
    ".autotool": "toggle auto tool selection in chat mode",
    ".autocorrect": "toggle auto code correction",
    ".light": "toggle light context",
    # file access
    ".content": "show current directory content",
    ".directory": "change directory",
    ".open": "open file or folder",
    #".download": "download data files",
    # help
    ".help": "help page",
}

# copy etextedit plugins
ETEXTEDIT_USER_PULGIN_DIR = os.path.join(os.path.expanduser("~"), "etextedit", "plugins")
if not os.path.isdir(ETEXTEDIT_USER_PULGIN_DIR):
    Path(ETEXTEDIT_USER_PULGIN_DIR).mkdir(parents=True, exist_ok=True)
COMPUTEMATE_ETEXTEDIT_PLUGINS = os.path.join(os.path.dirname(os.path.realpath(__file__)), "etextedit", "plugins")
for file_name in os.listdir(COMPUTEMATE_ETEXTEDIT_PLUGINS):
    full_file_name = os.path.join(COMPUTEMATE_ETEXTEDIT_PLUGINS, file_name)
    if file_name.endswith(".py") and os.path.isfile(full_file_name) and not os.path.isfile(os.path.join(ETEXTEDIT_USER_PULGIN_DIR, file_name)):
        shutil.copy(full_file_name, ETEXTEDIT_USER_PULGIN_DIR)

# constants
AGENTMAKE_CONFIG = {
    "print_on_terminal": False,
    "word_wrap": False,
}
COMPUTEMATE_VERSION = readTextFile(os.path.join(os.path.dirname(os.path.realpath(__file__)), "version.txt"))
COMPUTEMATE_PACKAGE_PATH = os.path.dirname(os.path.realpath(__file__))
COMPUTEMATEDATA = os.path.join(AGENTMAKE_USER_DIR, "computemate", "data")
if not os.path.isdir(COMPUTEMATEDATA):
    Path(COMPUTEMATEDATA).mkdir(parents=True, exist_ok=True)
DIALOGS = TerminalModeDialogs()

def fix_string(content):
    return content.replace(" ", " ").replace("‑", "-")

def get_mcp_config_file():
    user_mcp_config = os.path.join(COMPUTEMATE_USER_DIR, "mcp_configurations.py")
    return user_mcp_config if os.path.isfile(user_mcp_config) else os.path.join(COMPUTEMATE_PACKAGE_PATH, "mcp_configurations.py")

def edit_mcp_config_file(mcp_config_file=""):
    if not mcp_config_file:
        mcp_config_file = os.path.join(COMPUTEMATE_USER_DIR, "mcp_configurations.py")
        if not os.path.isfile(mcp_config_file):
            shutil.copy(os.path.join(COMPUTEMATE_PACKAGE_PATH, "mcp_configurations.py"), mcp_config_file)
    os.system(f'''{DEFAULT_TEXT_EDITOR} "{mcp_config_file}"''')

def run_system_command(cmd: str):
    cmd += " && cd" if USER_OS == "Windows" else " && pwd"
    result = subprocess.run(
        cmd,
        shell=True,
        capture_output=True,
        text=True,
    )
    text_output = result.stdout.strip()
    text_error = result.stderr.strip()
    lines = text_output.split("\n")
    if len(lines) == 1:
        return text_error if text_error else"Done!", lines[0]
    return "\n".join(lines[:-1]), lines[-1]

def list_dir_content(directory:str="."):
    directory = os.path.expanduser(directory.replace("%2F", "/"))
    if os.path.isdir(directory):
        folders = []
        files = []
        for item in sorted(os.listdir(directory)):
            if os.path.isdir(os.path.join(directory, item)):
                folders.append(f"📁 {item}")
            else:
                files.append(f"📄 {item}")
        return " ".join(folders) + ("\n\n" if folders and files else "") + " ".join(files)
    return "Invalid path!"