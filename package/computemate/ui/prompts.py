from agentmake.main import AGENTMAKE_USER_DIR
from agentmake.utils.system import getCliOutput
from prompt_toolkit.validation import Validator, ValidationError
from computemate import config
from pathlib import Path
import os, shutil, re


class NumberValidator(Validator):
    def validate(self, document):
        text = document.text

        if text and not re.search("^[0-9]+?$", text):
            i = 0

            # Get index of first non numeric character.
            # We want to move the cursor here.
            for i, c in enumerate(text):
                if not c.isdigit():
                    break

            raise ValidationError(message='This entry accepts numbers only!', cursor_position=i)

async def getInput(input_suggestions:list=None, number_validator:bool=False, default_entry=""):
    """
    Prompt for user input
    """
    # place import lines here to work with stdin
    from prompt_toolkit import PromptSession
    from prompt_toolkit.history import FileHistory
    from prompt_toolkit.completion import WordCompleter, FuzzyCompleter
    from prompt_toolkit.key_binding import KeyBindings
    bindings = KeyBindings()
    # launch editor
    @bindings.add("c-p")
    def _(event):
        buffer = event.app.current_buffer
        config.current_prompt = buffer.text
        buffer.text = ".editprompt"
        buffer.validate_and_handle()
    # new chat
    @bindings.add("c-n")
    def _(event):
        buffer = event.app.current_buffer
        buffer.text = ".new"
        buffer.validate_and_handle()
    # quit
    @bindings.add("c-q")
    def _(event):
        buffer = event.app.current_buffer
        buffer.text = ".exit"
        buffer.validate_and_handle()
    # insert new line
    @bindings.add("escape", "enter")
    def _(event):
        event.app.current_buffer.newline()
    # insert four spaces
    @bindings.add("c-i")
    def _(event):
        event.app.current_buffer.insert_text("    ")
    # undo
    @bindings.add("c-z")
    def _(event):
        event.app.current_buffer.undo()
    # reset buffer
    @bindings.add("c-r")
    def _(event):
        event.app.current_buffer.reset()
    # go to the beginning of the text
    @bindings.add("escape", "a")
    def _(event):
        event.app.current_buffer.cursor_position = 0
    # go to the end of the text
    @bindings.add("escape", "z")
    def _(event):
        buffer = event.app.current_buffer
        buffer.cursor_position = len(buffer.text)
    # go to current line starting position
    @bindings.add("home")
    @bindings.add("escape", "b")
    def _(event):
        buffer = event.app.current_buffer
        buffer.cursor_position = buffer.cursor_position - buffer.document.cursor_position_col
    # go to current line ending position
    @bindings.add("end")
    @bindings.add("escape", "e")
    def _(event):
        buffer = event.app.current_buffer
        buffer.cursor_position = buffer.cursor_position + buffer.document.get_end_of_line_position()

    log_file = os.path.join(AGENTMAKE_USER_DIR, "computemate", "logs", "requests")
    session = PromptSession(history=FileHistory(log_file))
    completer = FuzzyCompleter(WordCompleter(input_suggestions, ignore_case=True)) if input_suggestions else None
    instruction = await session.prompt_async(
        "> ",
        bottom_toolbar="[ENTER] submit [Alt+ENTER] linebreak [Ctrl+N] new [Ctrl+Q] quit",
        completer=completer,
        key_bindings=bindings,
        validator=NumberValidator() if number_validator else None,
        default=default_entry if default_entry else "",
    )
    print()
    return instruction.strip() if instruction else ""