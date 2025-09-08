from xomate.core.systems import *
from xomate.ui.prompts import getInput
from xomate.ui.info import get_banner
from xomate import config
from pathlib import Path
import asyncio, re, os
from alive_progress import alive_bar
from fastmcp import Client
from agentmake import agentmake, getDictionaryOutput, edit_configurations, writeTextFile, getCurrentDateTime, AGENTMAKE_USER_DIR, USER_OS, DEVELOPER_MODE
from rich.console import Console
from rich.markdown import Markdown
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.terminal_theme import MONOKAI
if not USER_OS == "Windows":
    import readline  # for better input experience

# MCP server client example
# testing in progress; not in production yet
client = Client("http://127.0.0.1:8084/mcp/") # !agentmakemcp agentmakemcp/examples/bible_study.py

# TODO: allow overriding default AgentMake config
AGENTMAKE_CONFIG = {
    "backend": None,
    "model": None,
    "model_keep_alive": None,
    "temperature": None,
    "max_tokens": None,
    "context_window": None,
    "batch_size": None,
    "stream": None,
    "print_on_terminal": False,
    "word_wrap": False,
}
# TODO: place in config.py
MAX_STEPS = 50

async def main():

    console = Console(record=True)
    console.clear()
    console.print(get_banner())

    async with client:
        await client.ping()

        #resources = await client.list_resources()
        #print("# Resources\n\n", resources, "\n\n")

        # List available tools, resources, and prompts
        tools_raw = await client.list_tools()
        #print(tools_raw)
        tools = {t.name: t.description for t in tools_raw}
        tools_schema = {}
        for t in tools_raw:
            schema = {
                "name": t.name,
                "description": t.description,
                "parameters": {
                    "type": "object",
                    "properties": t.inputSchema["properties"],
                    "required": t.inputSchema["required"],
                },
            }
            tools_schema[t.name] = schema

        available_tools = list(tools.keys())
        if not "get_direct_text_response" in available_tools:
            available_tools.insert(0, "get_direct_text_response")

        # add tool description for get_direct_text_response if not exists
        if not "get_direct_text_response" in tools:
            tool_descriptions = f"""# TOOL DESCRIPTION: `get_direct_text_response`
Get a static text-based response directly from a text-based AI model without using any other tools. This is useful when you want to provide a simple and direct answer to a question or request, without the need for online latest updates or task execution.\n\n\n"""
        # add tool descriptions
        for tool_name, tool_description in tools.items():
            tool_descriptions += f"""# TOOL DESCRIPTION: `{tool_name}`
{tool_description}\n\n\n"""

        prompts_raw = await client.list_prompts()
        #print("# Prompts\n\n", prompts_raw, "\n\n")
        prompts = {p.name: p.description for p in prompts_raw}
        prompt_list = [f"/{p}" for p in prompts.keys()]
        prompt_pattern = "|".join(prompt_list)
        prompt_pattern = f"""^({prompt_pattern}) """

        prompts_schema = {}
        for p in prompts_raw:
            arg_properties = {}
            arg_required = []
            for a in p.arguments:
                arg_properties[a.name] = {
                    "type": "string",
                    "description": str(a.description) if a.description else "no description available",
                }
                if a.required:
                    arg_required.append(a.name)
            schema = {
                "name": p.name,
                "description": p.description,
                "parameters": {
                    "type": "object",
                    "properties": arg_properties,
                    "required": arg_required,
                },
            }
            prompts_schema[p.name] = schema

        user_request = ""
        master_plan = ""
        messages = []

        while not user_request == ".quit":

            # spinner while thinking
            async def thinking(process):
                with Progress(
                    SpinnerColumn(),
                    TextColumn("[progress.description]{task.description}"),
                    transient=True  # This makes the progress bar disappear after the task is done
                ) as progress:
                    # Add an indefinite task (total=None)
                    task_id = progress.add_task("Thinking ...", total=None)
                    # Create and run the async task concurrently
                    async_task = asyncio.create_task(process())
                    # Loop until the async task is done
                    while not async_task.done():
                        progress.update(task_id)
                        await asyncio.sleep(0.01)
                await async_task
            # progress bar for processing steps
            async def async_alive_bar(task):
                """
                A coroutine that runs a progress bar while awaiting a task.
                """
                with alive_bar(title="Processing...", spinner='dots') as bar:
                    while not task.done():
                        bar() # Update the bar
                        await asyncio.sleep(0.01) # Yield control back to the event loop
                return task.result()
            async def process_step_async(step_number):
                """
                Manages the async task and the progress bar.
                """
                print(f"# Starting Step [{step_number}]...")
                # Create the async task but don't await it yet.
                task = asyncio.create_task(process_step())
                # Await the custom async progress bar that awaits the task.
                await async_alive_bar(task)

            # backup
            def backup():
                nonlocal console, messages, master_plan
                timestamp = getCurrentDateTime()
                storagePath = os.path.join(AGENTMAKE_USER_DIR, "xomate", timestamp)
                Path(storagePath).mkdir(parents=True, exist_ok=True)
                # Save full conversation
                conversation_file = os.path.join(storagePath, "conversation.py")
                writeTextFile(conversation_file, str(messages))
                # Save master plan
                writeTextFile(os.path.join(storagePath, "master_plan.md"), master_plan)
                # Save html
                html_file = os.path.join(storagePath, "conversation.html")
                console.save_html(html_file, inline_styles=True, theme=MONOKAI)
                # Save markdown
                console.save_text(os.path.join(storagePath, "conversation.md"))
                # Inform users of the backup location
                print(f"Conversation backup saved to {storagePath}")
                print(f"Report saved to {html_file}\n")
            def write_config():
                # TODO: support more configs
                config_file = os.path.join(os.path.dirname(os.path.realpath(__file__)), "config.py")
                writeTextFile(config_file, f"agent_mode={config.agent_mode}")

            if messages:
                console.rule()

            # Original user request
            # note: `python3 -m rich.emoji` for checking emoji
            console.print("Enter your request :smiley: :" if not messages else "Enter a follow-up request :flexed_biceps: :")
            action_list = {
                ".new": "new conversation",
                ".quit": "quit",
                ".backend": "change backend",
                ".chat": "enable chat mode",
                ".agent": "enable agent mode",
            }
            input_suggestions = list(action_list.keys())+prompt_list
            user_request = await getInput("> ", input_suggestions)
            while not user_request.strip():
                user_request = await getInput("> ", input_suggestions)

            # TODO: ui - radio list menu
            if user_request in action_list:
                if user_request == ".backend":
                    edit_configurations()
                    console.rule()
                    console.print("Restart to make the changes in the backend effective!", justify="center")
                    console.rule()
                elif user_request == ".chat":
                    config.agent_mode = False
                    write_config()
                    console.rule()
                    console.print("Chat Mode Enabled", justify="center")
                    console.rule()
                elif user_request == ".agent":
                    config.agent_mode = True
                    write_config()
                    console.rule()
                    console.print("Agent Mode Enabled", justify="center")
                    console.rule()
                elif user_request in (".new", ".quit"):
                    backup() # backup
                # reset
                if user_request == ".new":
                    user_request = ""
                    messages = []
                    console.clear()
                    console.print(get_banner())
                continue

            # auto prompt engineering
            user_request = agentmake(user_request, tool="improve_prompt", **AGENTMAKE_CONFIG)[-1].get("content", "").strip()[20:-4]

            # Chat mode
            if not config.agent_mode:
                async def run_chat_mode():
                    nonlocal messages, user_request
                    messages = agentmake(messages if messages else user_request, system="auto", **AGENTMAKE_CONFIG)
                await thinking(run_chat_mode)
                console.print(Markdown(f"# User Request\n\n{messages[-2]['content']}\n\n# AI Response\n\n{messages[-1]['content']}"))
                continue

            if re.search(prompt_pattern, user_request):
                prompt_name = re.search(prompt_pattern, user_request).group(1)
                user_request = user_request[len(prompt_name):]
                # Call the MCP prompt
                prompt_schema = prompts_schema[prompt_name[1:]]
                prompt_properties = prompt_schema["parameters"]["properties"]
                if len(prompt_properties) == 1 and "request" in prompt_properties: # AgentMake MCP Servers or alike
                    result = await client.get_prompt(prompt_name[1:], {"request": user_request})
                else:
                    structured_output = getDictionaryOutput(messages=messages, schema=prompt_schema)
                    result = await client.get_prompt(prompt_name[1:], structured_output)
                #print(result, "\n\n")
                master_plan = result.messages[0].content.text
                # display info
                console.print(Markdown(f"# User Request\n\n{user_request}\n\n# Master plan\n\n{master_plan}"))
            else:
                # display info
                console.print(Markdown(f"# User Request\n\n{user_request}"), "\n")
                # Generate master plan
                master_plan = ""
                async def generate_master_plan():
                    nonlocal master_plan
                    # Create initial prompt to create master plan
                    initial_prompt = f"""Provide me with the `Preliminary Action Plan` and the `Measurable Outcome` for resolving `My Request`.
    
# Available Tools

Available tools are: {available_tools}.

{tool_descriptions}

# My Request

{user_request}"""
                    console.print(Markdown("# Master plan"), "\n")
                    print()
                    master_plan = agentmake(messages+[{"role": "user", "content": initial_prompt}], system="create_action_plan", **AGENTMAKE_CONFIG)[-1].get("content", "").strip()
                await thinking(generate_master_plan)
                # display info
                console.print(Markdown(master_plan), "\n\n")

            system_suggestion = get_system_suggestion(master_plan)

            # Tool selection systemm message
            system_tool_selection = get_system_tool_selection(available_tools, tool_descriptions)

            # Get the first suggestion
            next_suggestion = ""
            async def get_first_suggestion():
                nonlocal next_suggestion
                console.print(Markdown("## Suggestion [1]"), "\n")
                next_suggestion = agentmake(user_request, system=system_suggestion, **AGENTMAKE_CONFIG)[-1].get("content", "").strip()
            await thinking(get_first_suggestion)
            console.print(Markdown(next_suggestion), "\n\n")

            if not messages:
                messages = [
                    {"role": "system", "content": "You are XoMate, an autonomous AI agent."},
                    {"role": "user", "content": user_request},
                ]
            else:
                messages.append({"role": "user", "content": user_request})

            step = 1
            while not ("DONE" in next_suggestion or re.sub("^[^A-Za-z]*?([A-Za-z]+?)[^A-Za-z]*?$", r"\1", next_suggestion).upper() == "DONE"):

                # Get tool suggestion for the next iteration
                suggested_tools = []
                async def get_tool_suggestion():
                    nonlocal suggested_tools, next_suggestion, system_tool_selection
                    if DEVELOPER_MODE:
                        console.print(Markdown(f"## Tool Selection (descending order by relevance) [{step}]"), "\n")
                    else:
                        console.print(Markdown(f"## Tool Selection [{step}]"), "\n")
                    # Extract suggested tools from the step suggestion
                    suggested_tools = agentmake(next_suggestion, system=system_tool_selection, **AGENTMAKE_CONFIG)[-1].get("content", "").strip() # Note: suggested tools are printed on terminal by default, could be hidden by setting `print_on_terminal` to false
                    suggested_tools = re.sub(r"^.*?(\[.*?\]).*?$", r"\1", suggested_tools, flags=re.DOTALL)
                    suggested_tools = eval(suggested_tools) if suggested_tools.startswith("[") and suggested_tools.endswith("]") else ["get_direct_text_response"] # fallback to direct response
                await thinking(get_tool_suggestion)
                if DEVELOPER_MODE:
                    console.print(Markdown(str(suggested_tools)))

                # Use the next suggested tool
                next_tool = suggested_tools[0] if suggested_tools else "get_direct_text_response"
                prefix = f"## Next Tool [{step}]\n\n" if DEVELOPER_MODE else ""
                console.print(Markdown(f"{prefix}`{next_tool}`"))
                print()

                # Get next step instruction
                next_step = ""
                async def get_next_step():
                    nonlocal next_step, next_tool, next_suggestion, tools
                    console.print(Markdown(f"## Next Instruction [{step}]"), "\n")
                    if next_tool == "get_direct_text_response":
                        next_step = agentmake(next_suggestion, system="xomate/direct_instruction", **AGENTMAKE_CONFIG)[-1].get("content", "").strip()
                    else:
                        next_tool_description = tools.get(next_tool, "No description available.")
                        system_tool_instruction = get_system_tool_instruction(next_tool, next_tool_description)
                        next_step = agentmake(next_suggestion, system=system_tool_instruction, **AGENTMAKE_CONFIG)[-1].get("content", "").strip()
                await thinking(get_next_step)
                console.print(Markdown(next_step), "\n\n")

                if messages[-1]["role"] != "assistant": # first iteration
                    messages.append({"role": "assistant", "content": "Please provide me with an initial instruction to begin."})
                messages.append({"role": "user", "content": next_step})

                async def process_step():
                    nonlocal messages, next_tool, next_step
                    if next_tool == "get_direct_text_response":
                        messages = agentmake(messages, system="auto", **AGENTMAKE_CONFIG)
                    else:
                        try:
                            tool_schema = tools_schema[next_tool]
                            tool_properties = tool_schema["parameters"]["properties"]
                            if len(tool_properties) == 1 and "request" in tool_properties: # AgentMake MCP Servers or alike
                                tool_result = await client.call_tool(next_tool, {"request": next_step})
                            else:
                                structured_output = getDictionaryOutput(messages=messages, schema=tool_schema)
                                tool_result = await client.call_tool(next_tool, structured_output)
                            tool_result = tool_result.content[0].text
                            messages[-1]["content"] += f"\n\n[Using tool `{next_tool}`]"
                            messages.append({"role": "assistant", "content": tool_result if tool_result.strip() else "Done!"})
                        except Exception as e:
                            if DEVELOPER_MODE:
                                console.print(f"Error: {e}\nFallback to direct response...\n\n")
                            messages = agentmake(messages, system="auto", **AGENTMAKE_CONFIG)
                await process_step_async(step)

                console.print(Markdown(f"\n## Output [{step}]\n\n{messages[-1]["content"]}"))

                # iteration count
                step += 1
                if step > MAX_STEPS:
                    print("Stopped! Too many steps! `MAX_STEPS` is currently set to ", MAX_STEPS, "!")
                    print("You can increase it in the settings, but be careful not to create an infinite loop!")
                    break

                # Get the next suggestion
                async def get_next_suggestion():
                    nonlocal next_suggestion, messages, system_suggestion
                    console.print(Markdown(f"## Suggestion [{step}]"), "\n")
                    next_suggestion = agentmake(messages, system=system_suggestion, follow_up_prompt="Please provide me with the next suggestion.", **AGENTMAKE_CONFIG)[-1].get("content", "").strip()
                await thinking(get_next_suggestion)
                #print()
                console.print(Markdown(next_suggestion), "\n")

            # Backup
            backup()

asyncio.run(main())