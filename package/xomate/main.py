from xomate.core.systems import *
from xomate.ui.prompts import getInput
from xomate.ui.info import get_banner
from pathlib import Path
import asyncio, re, os
from alive_progress import alive_bar
from fastmcp import Client
from agentmake import agentmake, writeTextFile, getCurrentDateTime, AGENTMAKE_USER_DIR, USER_OS, DEVELOPER_MODE
from rich.console import Console
from rich.markdown import Markdown
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.terminal_theme import MONOKAI
if not USER_OS == "Windows":
    import readline  # for better input experience

# MCP server client example
# testing in progress; not in production yet
client = Client("http://127.0.0.1:8083/mcp/") # !agentmakemcp agentmakemcp/examples/bible_study.py

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

        user_request = ""
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

            if messages:
                console.rule()

            # Original user request
            # note: `python3 -m rich.emoji` for checking emoji
            console.print("Enter your request :smiley: :" if not messages else "Enter a follow-up request :flexed_biceps: :")
            input_suggestions = [".new", ".quit"]+prompt_list
            user_request = await getInput("> ", input_suggestions)
            while not user_request.strip():
                user_request = await getInput("> ", input_suggestions)
            # TODO: auto-prompt engineering based on the user request

            if user_request in (".new", ".quit"):
                # TODO: backup messages
                if user_request == ".new":
                    user_request = ""
                    messages = []
                    console.clear()
                    console.print(get_banner())
                continue

            print(prompt_pattern, user_request)
            if re.search(prompt_pattern, user_request):
                print(111)
                prompt_name = re.search(prompt_pattern, user_request).group(1)
                user_request = user_request[len(prompt_name):]
                # Call the MCP prompt
                result = await client.get_prompt(prompt_name[1:], {"request": user_request})
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
                            tool_result = await client.call_tool(next_tool, {"request": next_step})
                            tool_result = tool_result.content[0].text
                            messages[-1]["content"] += f"\n\n[Using tool `{next_tool}`]"
                            messages.append({"role": "assistant", "content": tool_result})
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
            # Save text
            console.save_text(os.path.join(storagePath, "conversation.md"))
            # Inform users of the backup location
            print(f"Conversation backup saved to {storagePath}")
            print(f"HTML file saved to {html_file}\n")

asyncio.run(main())