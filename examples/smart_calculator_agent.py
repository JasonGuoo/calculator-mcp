"""
Smart Calculator Agent using the Official MCP Stdio Client

This script strictly follows the structure of the official MCP client quickstart
guide you provided. It launches the `stdio_server.py` script as a subprocess
and communicates with it over standard input/output.

This is the correct way to use the stdio client pattern.
"""
import os
import json
import asyncio
from typing import Optional
from contextlib import AsyncExitStack

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables from a .env file for the OpenAI API Key
load_dotenv()

class MCPClientAgent:
    """An agent that follows the official MCP stdio client example structure."""

    def __init__(self):
        self.session: Optional[ClientSession] = None
        self.exit_stack = AsyncExitStack()
        self.openai_client = OpenAI()

    async def connect_to_server(self, server_script_path: str):
        """Launches and connects to an MCP stdio server script."""
        print(f"Launching and connecting to stdio server: {server_script_path}")
        
        # Use 'uv run python' to ensure it uses the project's virtual environment
        server_params = StdioServerParameters(
            command="uv",
            args=["run", "python", server_script_path],
            env=None
        )
        
        # This context manager handles starting and stopping the server process
        stdio_transport = await self.exit_stack.enter_async_context(stdio_client(server_params))
        self.stdio, self.write = stdio_transport
        self.session = await self.exit_stack.enter_async_context(ClientSession(self.stdio, self.write))
        
        await self.session.initialize()
        
        response = await self.session.list_tools()
        tools = response.tools
        print(f"Successfully connected. Discovered tools: {[tool.name for tool in tools]}")

    async def process_query(self, query: str) -> str:
        """Processes a query using OpenAI and the available MCP tools."""
        if not self.session:
            raise ConnectionError("Cannot process query: Not connected to an MCP server.")

        # Get tools from the session and format them for OpenAI
        response = await self.session.list_tools()
        available_tools = [tool.to_openai() for tool in response.tools]

        # First call to OpenAI to see if it wants to use a tool
        llm_response = self.openai_client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": query}],
            functions=available_tools,
            function_call="auto",
        )
        message = llm_response.choices[0].message

        # If the LLM decides to call a function, execute it via the MCP session
        if message.function_call:
            tool_name = message.function_call.name
            tool_args = json.loads(message.function_call.arguments)

            print(f"--> LLM decided to call tool '{tool_name}' with args: {tool_args}")
            
            # Execute the tool call using the session
            result = await self.session.call_tool(tool_name, tool_args)
            
            # Send the result back to the LLM for a final, natural-language response
            second_response = self.openai_client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "user", "content": query},
                    message,
                    {"role": "function", "name": tool_name, "content": json.dumps(result.dict())},
                ],
            )
            return second_response.choices[0].message.content
        else:
            # The LLM chose to respond directly without using a tool
            return message.content

    async def cleanup(self):
        """Cleans up resources, which also terminates the server subprocess."""
        await self.exit_stack.aclose()
        print("\nClient cleaned up and server process terminated.")

async def main():
    """Main entry point to run the agent."""
    if not os.getenv("OPENAI_API_KEY"):
        print("Error: OPENAI_API_KEY environment variable not set. Please create a .env file.")
        return

    agent = MCPClientAgent()
    try:
        # The server script is in the parent directory of this example script
        # Note: This assumes the script is run from the project root (e.g., `uv run python examples/smart_calculator_agent.py`)
        server_script = "stdio_server.py"
        await agent.connect_to_server(server_script_path=server_script)

        # Process the three example queries
        queries = [
            "My students got these test scores: 98.5, 88, 76.5, 92, 85. What's the class average?",
            "I have a 'spend $100 get $20 off' coupon and a 'buy 2 get 1 free' deal. If items cost $45, $60, and $75, what's the best way to apply these offers?",
            "How do you say 'Paris' in English, French, German, and Japanese?"
        ]

        for query in queries:
            print(f"\n{'='*80}\nQuery: {query}\n{'='*80}")
            response = await agent.process_query(query)
            print(f"\nFinal Response:\n{response}")

    except Exception as e:
        print(f"\nAn error occurred: {e}")
    finally:
        await agent.cleanup()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass # The finally block in main() will handle cleanup

    
    agent = SmartCalculatorAgent(openai_api_key)
    
    # Example queries
    queries = [
        # Math calculation (will use MCP)
        "My students got these test scores: 98.5, 88, 76.5, 92, 85. What's the class average?",
        
        # Complex coupon calculation (will use MCP)
        "I have a 'spend $100 get $20 off' coupon and a 'buy 2 get 1 free' deal. "
        "If items cost $45, $60, and $75, what's the best way to apply these offers?",
        
        # Non-mathematical query (won't use MCP)
        "How do you say 'Paris' in English, French, German, and Japanese?"
    ]
    
    # Process each query
    for query in queries:
        print(f"\n{'='*80}\nQuery: {query}")
        print(f"{'='*80}")
        response = agent.process_query(query)
        print(f"Response: {response}\n")

if __name__ == "__main__":
    main()
