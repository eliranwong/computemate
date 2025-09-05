from .core.systems import *
from pathlib import Path
import asyncio, re, os
from fastmcp import Client
from agentmake import agentmake, writeTextFile, getCurrentDateTime, AGENTMAKE_USER_DIR

# MCP server client example
# testing in progress; not in production yet
client = Client("http://127.0.0.1:8084/mcp/") # !agentmakemcp agentmake_mcp/examples/bible_study.py

async def main():

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
        original_request = input("Enter your request: ").strip()
        if not original_request:
            print("Exit: No request provided.")
            exit(0)

        # Create initial prompt to create master plan
        initial_prompt = f"""Provide me with the `Preliminary Action Plan` and the `Measurable Outcome` for resolving `My Request`.
    
# Available Tools

Available tools are: {available_tools}.

{tool_descriptions}

# My Request

{original_request}"""

        master_plan = agentmake(
            messages=initial_prompt,
            system="create_action_plan",
        )[-1].get("content", "").strip()
        
        # TODO: ui
        print("# Master plan\n\n", master_plan, "\n\n")

        system_suggestion = get_system_suggestion(master_plan)

        # Tool selection systemm message
        system_tool_selection = get_system_tool_selection(available_tools, tool_descriptions)

        messages_init = agentmake(original_request, system=system_suggestion)

        # Extract the first suggestion
        next_suggestion = messages_init[-1].get("content", "").strip()

        messages = [
            {"role": "system", "content": "You are XoMate, an autonomous AI agent."},
            {"role": "user", "content": original_request},
        ]

        n = 0

        while not "DONE" in next_suggestion:

            ## TODO: ui
            print(f"## Next suggestion {n}\n\n", next_suggestion, "\n\n", f"## Suggested tools (descending order by relevance) {n}\n\n")

            # Extract suggested tools from the next suggestion
            suggested_tools = agentmake(next_suggestion, system=system_tool_selection)[-1].get("content", "").strip() # Note: suggested tools are printed on terminal by default, could be hidden by setting `print_on_terminal` to false
            suggested_tools = re.sub(r"^.*?(\[.*?\]).*?$", r"\1", suggested_tools, flags=re.DOTALL)
            suggested_tools = eval(suggested_tools) if suggested_tools.startswith("[") and suggested_tools.endswith("]") else ["get_direct_text_response"] # fallback to direct response

            # TODO: check if the suggested tools are in available_tools
            # Use the next suggested tool
            next_tool = suggested_tools[0] if suggested_tools else "get_direct_text_response"

            ## TODO: ui
            print(f"\n\n## Next tool {n}\n\n", next_tool, "\n\n")

            if next_tool == "get_direct_text_response":
                next_step = agentmake(next_suggestion, system="xomate/direct_instruction")[-1].get("content", "").strip()
            else:
                next_tool_description = tools.get(next_tool, "No description available.")
                system_tool_instruction = get_system_tool_instruction(next_tool, next_tool_description)
                next_step = agentmake(next_suggestion, system=system_tool_instruction)[-1].get("content", "").strip()

            ## TODO: ui
            print(f"## Next Step {n}\n\n", next_step, "\n\n")

            if messages[-1]["role"] != "assistant": # first iteration
                messages.append({"role": "assistant", "content": "Please provide me with an initial instruction to begin."})
            messages.append({"role": "user", "content": next_step})

            if next_tool == "get_direct_text_response":
                messages = agentmake(messages, system="auto")
            else:
                try:
                    tool_result = await client.call_tool(next_tool, {"request": next_step})
                    tool_result = tool_result.content[0].text
                    messages[-1]["content"] += f"\n\n[Using tool `{next_tool}`]"
                    messages.append({"role": "assistant", "content": tool_result})
                except Exception as e:
                    messages = agentmake(messages, system="auto")

            ## TODO: ui
            print(f"## AI Response {n}\n\n", messages[-1]["content"], "\n\n")

            next_suggestion = agentmake(messages, system=system_suggestion, follow_up_prompt="Please provide me with the next suggestion.")[-1].get("content", "").strip()
            
            n += 1
            if n > 20:
                print("Error! Too many iterations!")
                break

        # Backup
        timestamp = getCurrentDateTime()
        storagePath = os.path.join(AGENTMAKE_USER_DIR, "xomate", timestamp)
        Path(storagePath).mkdir(parents=True, exist_ok=True)
        # Save full conversation
        conversation_file = os.path.join(storagePath, "conversation.py")
        writeTextFile(conversation_file, str(messages))

asyncio.run(main())
