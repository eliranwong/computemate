from .core.systems import *
from pathlib import Path
import asyncio, re, os
from alive_progress import alive_bar
from fastmcp import Client
from agentmake import agentmake, writeTextFile, getCurrentDateTime, getOpenCommand, AGENTMAKE_USER_DIR, USER_OS
from rich.console import Console
from rich.markdown import Markdown
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.panel import Panel
from rich.text import Text
from rich.align import Align
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
MAX_STEPS = 50

async def main():

    console = Console(record=True)
    console.clear()

    # Project title styling
    title = Text("XoMate AI", style="bold magenta", justify="center")
    title.stylize("bold magenta underline", 0, len("XoMate AI"))

    # Tagline styling
    tagline = Text("Execute. Orchestrate. Automate.", style="bold cyan", justify="center")

    # Combine into a panel
    banner_content = Align.center(
        Text("\n") + title + Text("\n") + tagline + Text("\n"),
        vertical="middle"
    )

    banner = Panel(
        banner_content,
        border_style="bright_blue",
        title="🚀 Project Launch",
        title_align="left",
        subtitle="AI Automation Suite",
        subtitle_align="right",
        padding=(1, 4)
    )

    console.print(banner)

    async with client:
        await client.ping()
        
        # List available tools, resources, and prompts
        tools = await client.list_tools()
        tools = {t.name: t.description for t in tools}
        #print("# Tools\n\n", tools, "\n\n")

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

        #resources = await client.list_resources()
        #print("# Resources\n\n", resources, "\n\n")
        # TODO: input suggestions
        #prompts = await client.list_prompts()
        #print("# Prompts\n\n", prompts, "\n\n")

        # Call a MCP prompt
        #result = await client.get_prompt("ask_multiple_models", {"request": "What is AI?"})
        #print(result, "\n\n")
        #master_plan = result.messages[0].content.text

        # Original user request
        original_request = console.input("Enter your request :smiley: : ")
        if not original_request:
            print("Exit: No request provided.")
            exit(0)

        # TODO: auto-prompt engineering based on the user request

        console.print(Markdown(f"# User Request\n\n{original_request}"), "\n")

        # Create initial prompt to create master plan
        initial_prompt = f"""Provide me with the `Preliminary Action Plan` and the `Measurable Outcome` for resolving `My Request`.
    
# Available Tools

Available tools are: {available_tools}.

{tool_descriptions}

# My Request

{original_request}"""
        
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

        # Generate master plan
        master_plan = ""
        async def generate_master_plan():
            nonlocal master_plan, initial_prompt
            console.print(Markdown("# Master plan"), "\n")
            print()
            master_plan = agentmake(initial_prompt, system="create_action_plan", **AGENTMAKE_CONFIG)[-1].get("content", "").strip()
        await thinking(generate_master_plan)
        console.print(Markdown(master_plan), "\n\n")

        system_suggestion = get_system_suggestion(master_plan)

        # Tool selection systemm message
        system_tool_selection = get_system_tool_selection(available_tools, tool_descriptions)

        # Get the first suggestion
        next_suggestion = ""
        async def get_first_suggestion():
            nonlocal next_suggestion
            console.print(Markdown("## Suggestion [1]"), "\n")
            next_suggestion = agentmake(original_request, system=system_suggestion, **AGENTMAKE_CONFIG)[-1].get("content", "").strip()
        await thinking(get_first_suggestion)
        #print()
        console.print(Markdown(next_suggestion), "\n\n")

        messages = [
            {"role": "system", "content": "You are XoMate, an autonomous AI agent."},
            {"role": "user", "content": original_request},
        ]

        n = 1

        while not "DONE" in next_suggestion:

            ## TODO: ui
            print(next_suggestion, "\n")

            # Get tool suggestion for the next iteration
            suggested_tools = []
            async def get_tool_suggestion():
                nonlocal suggested_tools, next_suggestion, system_tool_selection
                console.print(Markdown(f"## Tool Selection (descending order by relevance) [{n}]"), "\n")
                # Extract suggested tools from the step suggestion
                suggested_tools = agentmake(next_suggestion, system=system_tool_selection, **AGENTMAKE_CONFIG)[-1].get("content", "").strip() # Note: suggested tools are printed on terminal by default, could be hidden by setting `print_on_terminal` to false
                suggested_tools = re.sub(r"^.*?(\[.*?\]).*?$", r"\1", suggested_tools, flags=re.DOTALL)
                suggested_tools = eval(suggested_tools) if suggested_tools.startswith("[") and suggested_tools.endswith("]") else ["get_direct_text_response"] # fallback to direct response
            await thinking(get_tool_suggestion)
            # TODO: display for developer; hide for general users
            print()
            console.print(Markdown(str(suggested_tools)))

            # TODO: check if the suggested tools are in available_tools
            # Use the next suggested tool
            next_tool = suggested_tools[0] if suggested_tools else "get_direct_text_response"

            console.print(Markdown(f"## Next Tool [{n}]\n\n`{next_tool}`"))
            print()

            # Get next step instruction
            next_step = ""
            async def get_next_step():
                nonlocal next_step, next_tool, next_suggestion, tools
                console.print(Markdown(f"## Next Instruction [{n}]"), "\n")
                if next_tool == "get_direct_text_response":
                    next_step = agentmake(next_suggestion, system="xomate/direct_instruction", **AGENTMAKE_CONFIG)[-1].get("content", "").strip()
                else:
                    next_tool_description = tools.get(next_tool, "No description available.")
                    system_tool_instruction = get_system_tool_instruction(next_tool, next_tool_description)
                    next_step = agentmake(next_suggestion, system=system_tool_instruction, **AGENTMAKE_CONFIG)[-1].get("content", "").strip()
            await thinking(get_next_step)
            #print()
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
                        # TODO: Fallback to direct response
                        messages = agentmake(messages, system="auto", **AGENTMAKE_CONFIG)
            await process_step_async(n)

            console.print(Markdown(f"\n## Output [{n}]\n\n{messages[-1]["content"]}"))

            # iteration count
            n += 1
            if n > MAX_STEPS:
                print("Stopped! Too many steps! `MAX_STEPS` is currently set to ", MAX_STEPS, "!")
                print("You can increase it in the settings, but be careful not to create an infinite loop!")
                break

            # Get the next suggestion
            async def get_first_suggestion():
                nonlocal next_suggestion, messages, system_suggestion
                console.print(Markdown(f"## Suggestion [{n}]"), "\n")
                next_suggestion = agentmake(messages, system=system_suggestion, follow_up_prompt="Please provide me with the next suggestion.", **AGENTMAKE_CONFIG)[-1].get("content", "").strip()
            await thinking(get_first_suggestion)
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
        console.save_html(html_file, inline_styles=True)
        # Save text
        console.save_text(os.path.join(storagePath, "conversation.md"))
        # Inform users of the backup location
        print(f"Backup saved to {storagePath}")

        os.system(f'{getOpenCommand()} "{html_file}"')


asyncio.run(main())
