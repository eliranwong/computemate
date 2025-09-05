import asyncio, pprint, re, os
from fastmcp import Client
from agentmake import agentmake, PACKAGE_PATH, AGENTMAKE_USER_DIR, readTextFile

# MCP server client example
client = Client("http://127.0.0.1:8080/mcp/") # !agentmakemcp agentmake_mcp/examples/ask_multiple_models.py

async def main():

    def get_system_suggestion(master_plan: str) -> str:
        # Agent assignment
        possible_system_file_path_2 = os.path.join(PACKAGE_PATH, "systems", "xomate", "supervisor.md")
        possible_system_file_path_1 = os.path.join(AGENTMAKE_USER_DIR, "systems", "xomate", "supervisor.md")
        return readTextFile(possible_system_file_path_2 if os.path.isfile(possible_system_file_path_2) else possible_system_file_path_1).format(master_plan)

    def get_system_tool_selection(available_tools: list, tools: dict) -> str:
        system_tool_selection = f"""You are an expert in selecting the most appropriate AI tools to address a given suggestion. Your task is to analyze the suggestion and choose the best-suited tool from a list of available tools, i.e. {available_tools}. You will be provided with the `TOOL DESCRIPTION` of each tool below. Consider the strengths and capabilities of each tool in relation to the suggestion at hand. Ensure your choice aligns with the goal of effectively addressing the suggestion. After your analysis, reoder the list of available tools from the most relevant to the least relevant, and provide your response in the python list format, without any additional commentary or explanation. Refer to the `OUTPUT FORMAT` section below for the expected format of your response.
        

        """
        if not "get_direct_text_response" in tools:
            system_tool_selection += f"""# TOOL DESCRIPTION: `get_direct_text_response`
Get a static text-based response directly from a text-based AI model without using any other tools. This is useful when you want to provide a simple and direct answer to a question or request, without the need for online latest updates or task execution.


"""
        for tool_name, tool_description in tools.items():
            system_tool_selection += f"""# TOOL DESCRIPTION: `{tool_name}`
{tool_description}


"""
        system_tool_selection += """# OUTPUT FORMAT
Your response should be in the following python list format:
["most_relevant_tool", "second_most_relevant_tool", "third_most_relevant_tool", "...", "least_relevant_tool"]

Remember to only provide the python list as your response, without any additional commentary or explanation."""
        return system_tool_selection

    def get_system_tool_instruction(selected_tool: str, tool_description: str = "") -> str:
        return f"""You are an expert in converting suggestions into clear and concise instructions for an AI assistant to follow. You will be provided with the suggestion from the supervisor, and you need to convert it into clear and concise instructions for the AI assistant to follow, using the specified tool `{selected_tool}`. 
        
        Formate your response as a direct request to the AI assistant, specifying information that the tool `{selected_tool}` requires to complete the task, according to the tool's description: 
        
        ```tool description
        {tool_description}
        ```

        Remember:
        * Do not mention the tool name in your instruction.
        * Do not mention further steps or tools to be used after this instruction.
        * Only provide the instruction for the specified tool `{selected_tool}`.

        You provide the converted instruction directly, without any additional commentary or explanation."""

    async with client:
        # Basic server interaction
        await client.ping()
        
        # List available tools, resources, and prompts
        tools = await client.list_tools()
        tools = {t.name: t.description for t in tools}
        print("# Tools\n\n", tools, "\n\n")
        resources = await client.list_resources()
        print("# Resources\n\n", resources, "\n\n")
        prompts = await client.list_prompts()
        print("# Prompts\n\n", prompts, "\n\n")

        # Call a MCP prompt
        result = await client.get_prompt("ask_multiple_models", {"request": "What is AI?"})
        #print(result, "\n\n")
        mcp_prompt = result.messages[0].content.text
        print(mcp_prompt)

        system_suggestion = get_system_suggestion(mcp_prompt)
        
        available_tools = list(tools.keys())
        if not "get_direct_text_response" in available_tools:
            available_tools.insert(0, "get_direct_text_response")

        # Tool selection systemm message
        system_tool_selection = get_system_tool_selection(available_tools, tools)

        original_request = "What is AI?"
        messages_init = agentmake(original_request, system=system_suggestion)

        # Extract the first suggestion
        next_suggestion = messages_init[-1].get("content", "").strip()

        messages = [
            {"role": "system", "content": "You are XoMate, an autonomous AI agent."},
            {"role": "user", "content": original_request},
        ]

        n = 0

        while not "DONE" in next_suggestion:

            # Extract suggested tools from the next suggestion
            suggested_tools = agentmake(next_suggestion, system=system_tool_selection)[-1].get("content", "").strip()
            suggested_tools = re.sub(r"^.*?(\[.*?\]).*?$", r"\1", suggested_tools, flags=re.DOTALL)
            suggested_tools = eval(suggested_tools) if suggested_tools.startswith("[") and suggested_tools.endswith("]") else ["get_direct_text_response"] # fallback to direct response
            # TODO: check if the suggested tools are in available_tools
            # Use the next suggested tool
            next_tool = suggested_tools[0] if suggested_tools else "get_direct_text_response"
            if next_tool == "get_direct_text_response":
                next_step = agentmake(next_suggestion, system="xomate/suggestion_to_instruction")[-1].get("content", "").strip()
            else:
                next_tool_description = tools.get(next_tool, "No description available.")
                system_tool_instruction = get_system_tool_instruction(next_tool, next_tool_description)
                next_step = agentmake(next_suggestion, system=system_tool_instruction)[-1].get("content", "").strip()

            if messages[-1]["role"] != "assistant": # first iteration
                messages.append({"role": "assistant", "content": "Please provide me with an initial instruction to begin."})
            messages.append({"role": "user", "content": next_step})

            if next_tool == "get_direct_text_response":
                messages = agentmake(messages)
            else:
                tool_result = await client.call_tool(next_tool, {"request": next_step})
                tool_result = tool_result.content[0].text
                messages[-1]["content"] += f"\n\n[Using tool `{next_tool}`]"
                messages.append({"role": "assistant", "content": tool_result})

            next_suggestion = agentmake(messages, system=system_suggestion, follow_up_prompt="Please provide me with the next suggestion.")[-1].get("content", "").strip()
            
            n += 1
            if n > 10:
                print("Error! Too many iterations!")
                break

        pprint.pprint(messages) # TODO: save to file

asyncio.run(main())
