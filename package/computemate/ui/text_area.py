from computemate import config, DIALOGS, AGENTMAKE_CONFIG, COMPUTEMATE_USER_DIR
from prompt_toolkit.input import create_input
from prompt_toolkit.layout import Layout, HSplit
from prompt_toolkit.widgets import Frame, Label
from prompt_toolkit.styles import Style, merge_styles
from prompt_toolkit.application import Application
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.completion import WordCompleter, FuzzyCompleter
from prompt_toolkit.widgets import Frame, TextArea
from prompt_toolkit.layout.menus import CompletionsMenu
from prompt_toolkit.layout import WindowAlign
from prompt_toolkit.lexers import PygmentsLexer
from pygments.lexers.markup import MarkdownLexer
from prompt_toolkit.styles import style_from_pygments_cls
from pygments.styles import get_style_by_name
from agentmake import agentmake, DEFAULT_TEXT_EDITOR, edit_file, readTextFile, writeTextFile
from agentmake.etextedit import launch_async
from agentmake.utils.files import searchFolder
from typing import Any, Optional
from pathlib import Path
import os, re, glob


async def getTextArea(input_suggestions:list=None, default_entry="", title="", multiline:bool=True, completion:Optional[Any]=None, scrollbar:bool=True, read_only:bool=False):
    """Get text area input with a border frame"""

    if config.current_prompt and not default_entry:
        default_entry = config.current_prompt
    config.current_prompt = "" # reset config.current_prompt
    completer = FuzzyCompleter(WordCompleter(input_suggestions, ignore_case=True)) if input_suggestions else None
    
    # Markdown
    pygments_style = get_style_by_name('github-dark')
    markdown_style = style_from_pygments_cls(pygments_style)
    # Define custom style
    custom_style = Style.from_dict({
        #'frame.border': '#00ff00',  # Green border
        #'frame.label': '#ffaa00 bold',  # Orange label
        #'completion-menu': 'bg:#008888 #ffffff',
        #'completion-menu.completion': 'bg:#008888 #ffffff',
        #'completion-menu.completion.current': 'bg:#00aaaa #000000',
        #"status": "reverse",
        "textarea": "bg:#1E1E1E",
    })

    style = merge_styles([markdown_style, custom_style])

    # TextArea with a completer
    text_area = TextArea(
        text=default_entry,
        style="class:textarea",
        lexer=PygmentsLexer(MarkdownLexer),
        multiline=multiline,
        scrollbar=scrollbar,
        read_only=read_only,
        completer=completer,
        complete_while_typing=config.auto_suggestions,
        focus_on_click=True,
        wrap_lines=True,
    )
    text_area.buffer.cursor_position = len(text_area.text)

    def unpack_text_chunks(_):
        openai_style = True if config.backend in ("azure", "azure_any", "custom", "deepseek", "github", "github_any", "googleai", "groq", "llamacpp", "mistral", "openai", "xai") else False
        first_event = True
        chat_response = ""
        for event in completion:
            # RETRIEVE THE TEXT FROM THE RESPONSE
            if event is None:
                continue
            elif openai_style:
                # openai
                # when open api key is invalid for some reasons, event response in string
                if isinstance(event, str):
                    answer = event
                elif hasattr(event, "data") and hasattr(event.data, "choices"): # mistralai
                    try:
                        answer = event.data.choices[0].delta.content
                    except:
                        answer = None
                elif hasattr(event, "choices") and not event.choices: # in case of the 1st event of azure's completion
                    continue
                else:
                    answer = event.choices[0].delta.content or ""
            elif hasattr(event, "type") and event.type == "content-delta" and hasattr(event, "delta"): # cohere
                answer = event.delta.message.content.text
            elif hasattr(event, "delta") and hasattr(event.delta, "text"): # anthropic
                answer = event.delta.text
            elif hasattr(event, "content_block") and hasattr(event.content_block, "text"):
                answer = event.content_block.text
            elif str(type(event)).startswith("<class 'anthropic.types"): # anthropic
                continue
            elif hasattr(event, "message"): # newer ollama python package
                answer = event.message.content
            elif isinstance(event, dict):
                if "message" in event:
                    # ollama chat
                    answer = event["message"].get("content", "")
                else:
                    # llama.cpp chat
                    answer = event["choices"][0]["delta"].get("content", "")
            elif hasattr(event, "text"):
                # vertex ai, genai
                answer = event.text
            else:
                #print(event)
                answer = None
            # STREAM THE ANSWER
            if answer is not None:
                if first_event:
                    first_event = False
                    answer = answer.lstrip()
                # update the chat response
                chat_response += answer
                # display the chunk in the text area
                text_area.buffer.insert_text(answer)
                text_area.buffer.cursor_position = len(text_area.text)

    def edit_temp_file(initial_content: str) -> str:
        config.current_prompt = ""
        temp_file = os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))), "temp", "edit.md")
        writeTextFile(temp_file, initial_content)
        edit_file(temp_file)
        return readTextFile(temp_file).strip()

    # Layout: include a CompletionsMenu
    root_container = HSplit(
        [
            Frame(
                text_area,
                title=title,
            ),
            Label(
                "[Ctrl+S] Send [Ctrl+Q] Exit" if title else "[Ctrl+S] Send [Ctrl+Y] Help",
                align=WindowAlign.RIGHT,
                style="fg:grey",
            ),
            CompletionsMenu(
                max_height=8,
                scroll_offset=1,
            ),
        ]
    )
    
    # Create key bindings
    bindings = KeyBindings()
    config.cursor_position = 0
    
    if not title: # for the main prompt only; these shortcuts are irrelevant for review or configuration prompts
        # help
        @bindings.add("c-y")
        def _(event):
            config.current_prompt = text_area.text
            event.app.exit(result=".help")
        # change AI mode
        @bindings.add("c-j")
        def _(event):
            config.current_prompt = text_area.text
            event.app.exit(result=".mode")
        # new chat
        @bindings.add("c-n")
        def _(event):
            config.current_prompt = text_area.text
            event.app.exit(result=".new")
        # edit conversation
        @bindings.add("escape", "i")
        def _(event):
            config.current_prompt = text_area.text
            event.app.exit(result=".import")
        # edit conversation
        @bindings.add("escape", "o")
        def _(event):
            config.current_prompt = text_area.text
            event.app.exit(result=".edit")
        # generate ideas
        @bindings.add("escape", "g")
        def _(event):
            config.current_prompt = text_area.text
            event.app.exit(result=".ideas")
        # toggle auto input suggestions
        @bindings.add("c-g")
        def _(event):
            config.current_prompt = text_area.text
            event.app.exit(result=".autosuggest")
        # improve prompt
        @bindings.add("escape", "p")
        def _(event):
            buffer = event.app.current_buffer if event is not None else text_area.buffer
            user_request = text_area.text
            try:
                user_request = agentmake(user_request, tool="improve_prompt", **AGENTMAKE_CONFIG)[-1].get("content", "").strip()
                if "```" in user_request:
                    user_request = re.sub(r"^.*?(```improved_version|```)(.+?)```.*?$", r"\2", user_request, flags=re.DOTALL).strip()
            except:
                user_request = agentmake(user_request, system="improve_prompt_2", **AGENTMAKE_CONFIG)[-1].get("content", "").strip()
                user_request = re.sub(r"^.*?(```improved_prompt|```)(.+?)```.*?$", r"\2", user_request, flags=re.DOTALL).strip()
            text_area.text = user_request
            config.cursor_position = len(text_area.text)
        # toggle prompt engineering
        @bindings.add("c-p")
        def _(event):
            config.current_prompt = text_area.text
            event.app.exit(result=".autoprompt")
        # show directory content
        @bindings.add("escape", "c")
        def _(event):
            config.current_prompt = text_area.text
            event.app.exit(result=".content")
        # toggle auto tool selection in chat mode
        @bindings.add("escape", "t")
        def _(event):
            config.current_prompt = text_area.text
            event.app.exit(result=".autotool")
        # change directory
        @bindings.add("c-c")
        def _(event):
            config.current_prompt = text_area.text
            event.app.exit(result=".directory")
        # write prompts or plans
        @bindings.add("c-w")
        def _(event):
            config.current_prompt = text_area.text
            event.app.exit(result="[SAVEPROMPT]")
        # delete prompts or plans
        @bindings.add("escape", "w")
        def _(event):
            config.current_prompt = text_area.text
            event.app.exit(result="[DELETEPROMPT]")
        # open prompts or plans
        @bindings.add("c-l")
        def _(event):
            config.current_prompt = text_area.text
            event.app.exit(result="[LOADPROMPT]")
        # open prompts or plans
        @bindings.add("escape", "l")
        def _(event):
            config.current_prompt = text_area.text
            event.app.exit(result="[SEARCHPROMPT]")
        # open search features
        @bindings.add("c-f")
        def _(event):
            config.current_prompt = text_area.text
            event.app.exit(result=".find")

    # open editor
    @bindings.add("c-o")
    def _(event):
        config.cursor_position = text_area.buffer.cursor_position
        config.current_prompt = text_area.text
        event.app.exit(result=".editprompt")
    # exit
    @bindings.add("c-q")
    def _(event):
        event.app.exit(result=".exit")
    # submit
    @bindings.add("escape", "enter")
    @bindings.add("c-s")
    def _(event):
        if not text_area.text.strip():
            text_area.text = entry = "."
        event.app.exit(result=text_area.text.strip())
    # submit or new line
    @bindings.add("enter")
    @bindings.add("c-m")
    def _(event):
        entry = text_area.text.strip()
        if not multiline or (not title and ((entry.strip() == "." or entry.startswith(".") and entry in input_suggestions) or entry.startswith(".open ") or entry.startswith(".import "))):
            event.app.exit(result=text_area.text.strip())
        else:
            text_area.buffer.newline()
    # insert four spaces
    @bindings.add("s-tab")
    def _(event):
        buffer = event.app.current_buffer if event is not None else text_area.buffer
        buffer.insert_text("    ")
    # trigger completion
    @bindings.add("tab")
    @bindings.add("c-i")
    def _(event):
        buffer = event.app.current_buffer if event is not None else text_area.buffer
        buffer.start_completion()
    # close completion menu
    @bindings.add("escape")
    def _(event):
        buffer = event.app.current_buffer if event is not None else text_area.buffer
        buffer.cancel_completion()
    # undo
    @bindings.add("c-z")
    def _(event):
        buffer = event.app.current_buffer if event is not None else text_area.buffer
        buffer.undo()
    # reset buffer
    @bindings.add("c-r")
    def _(event):
        buffer = event.app.current_buffer if event is not None else text_area.buffer
        buffer.reset()
    # Create application
    app = Application(
        layout=Layout(root_container, focused_element=text_area),
        key_bindings=bindings,
        enable_page_navigation_bindings=True,
        style=style,
        #clipboard=PyperclipClipboard(), # not useful if mouse_support is not enabled
        #mouse_support=True, # If enabled; content outside the app becomes unscrollable
        input=create_input(always_prefer_tty=True),
        full_screen=False,
        after_render=unpack_text_chunks if completion is not None else None,
    )
    
    # Run the app
    result = await app.run_async()
    print()
    # edit in full editor
    while result == ".editprompt":
        if DEFAULT_TEXT_EDITOR == "etextedit":
            text_area.text = await launch_async(input_text=config.current_prompt, exitWithoutSaving=True, customTitle=f"ComputeMate AI", startAt=config.cursor_position)
        else:
            text_area.text = edit_temp_file(config.current_prompt)
        text_area.buffer.cursor_position = len(text_area.text)
        config.current_prompt = ""
        # Run the non-full-screen text area again
        result = await app.run_async()
        print()
    if not title and result in ("[DELETEPROMPT]", "[SAVEPROMPT]", "[LOADPROMPT]", "[SEARCHPROMPT]"):
        '''if result == "[CONVERSATION]":
            options = [".new", ".reload", ".backup", ".edit", ".trim", ".import", ".export", ".find"]
            descriptions = [config.action_list[i] for i in options]
            select = await DIALOGS.getValidOptions(options=options, descriptions=descriptions, title="Commentaries", text="Select an option to continue:")
            return select if select else ""'''
        if result == "[SAVEPROMPT]":
            user_input = await DIALOGS.getInputDialog(title="Save Prompt", text="Enter a name:")
            if user_input:
                prompt_dir = os.path.join(COMPUTEMATE_USER_DIR, "prompts")
                plan_dir = os.path.join(COMPUTEMATE_USER_DIR, "plans")
                storage_path = plan_dir if text_area.text.startswith("@@") else prompt_dir
                if not os.path.isdir(os.path.join(storage_path, os.path.dirname(user_input))):
                    Path(storage_path).mkdir(parents=True, exist_ok=True)
                save_path = os.path.join(storage_path, user_input+(".plan" if text_area.text.startswith("@@") else ".prompt"))
                if text_area.text.strip():
                    writeTextFile(save_path, text_area.text)
                elif os.path.isfile(save_path):
                    os.remove(save_path)
            return ""
        elif result == "[DELETEPROMPT]":
            options = [".deleteprompt", ".deleteplan"]
            descriptions = ["Delete a prompt", "Delete a plan"]
            select = await DIALOGS.getValidOptions(options=options, descriptions=descriptions, title="Open Prompt / Plan", text="Select an option to continue:")
            if not select:
                return ""
            prompts_path = os.path.join(COMPUTEMATE_USER_DIR, "prompts")
            prompts = os.path.join(prompts_path, "**", "*.prompt")
            plans_path = os.path.join(COMPUTEMATE_USER_DIR, "plans")
            plans = os.path.join(plans_path, "**", "*.plan")
            found = glob.glob(plans if select == ".deleteplan" else prompts, recursive=True)
            if found:
                prefix = plans_path if select == ".deleteplan" else prompts_path
                suffix = ".plan" if select == ".deleteplan" else ".prompt"
                options = [i[len(prefix)+1:-(len(suffix))] for i in found]
                select = await DIALOGS.getValidOptions(options=options, title="Open Plan" if select == ".deleteplan" else "Open Prompt", text="Select a plan:" if select == ".deleteplan" else "Select a prompt:")
                if select:
                    os.remove(os.path.join(prefix, select+suffix))
            return ""
        elif result == "[LOADPROMPT]":
            options = [".openprompt", ".openplan"]
            descriptions = ["Open a prompt", "Open a plan"]
            select = await DIALOGS.getValidOptions(options=options, descriptions=descriptions, title="Open Prompt / Plan", text="Select an option to continue:")
            if not select:
                return ""
            prompts_path = os.path.join(COMPUTEMATE_USER_DIR, "prompts")
            prompts = os.path.join(prompts_path, "**", "*.prompt")
            plans_path = os.path.join(COMPUTEMATE_USER_DIR, "plans")
            plans = os.path.join(plans_path, "**", "*.plan")
            found = glob.glob(plans if select == ".openplan" else prompts, recursive=True)
            if found:
                prefix = plans_path if select == ".openplan" else prompts_path
                suffix = ".plan" if select == ".openplan" else ".prompt"
                options = [i[len(prefix)+1:-(len(suffix))] for i in found]
                select = await DIALOGS.getValidOptions(options=options, title="Open Plan" if select == ".openplan" else "Open Prompt", text="Select a plan:" if select == ".openplan" else "Select a prompt:")
                if select:
                    config.current_prompt = readTextFile(os.path.join(prefix, select+suffix))
            return ""
        elif result == "[SEARCHPROMPT]":
            options = [".searchprompt", ".searchplan"]
            descriptions = ["Search prompts", "Search plans"]
            select = await DIALOGS.getValidOptions(options=options, descriptions=descriptions, title="Search Prompts / Plans", text="Select an option to continue:")
            if not select:
                return ""
            prompts_path = os.path.join(COMPUTEMATE_USER_DIR, "prompts")
            prompts = os.path.join(prompts_path, "**", "*.prompt")
            plans_path = os.path.join(COMPUTEMATE_USER_DIR, "plans")
            plans = os.path.join(plans_path, "**", "*.plan")
            found = glob.glob(plans if select == ".searchplan" else prompts, recursive=True)
            if found:
                prefix = plans_path if select == ".searchplan" else prompts_path
                suffix = ".plan" if select == ".searchplan" else ".prompt"
                query = await DIALOGS.getInputDialog(title="Search Plans" if select == ".searchplan" else "Search Prompts", text="Enter a search query:")
                if query:
                    searchFolder(prefix, query=query, filter="*"+suffix)
                    print()
            return ""
    # return the text content
    return result

