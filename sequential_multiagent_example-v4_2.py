# Example using both Tavily MCP (remote) and Weather MCP (local) servers
# Demonstrates using MCP Tools, Resources, and Prompts

import os
import asyncio
from dotenv import load_dotenv

from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_mcp_adapters.tools import load_mcp_tools

from langchain.agents import create_agent
from langchain.messages import HumanMessage


load_dotenv()

# Verify API keys
if not os.getenv("OPENAI_API_KEY"):
    raise ValueError("OPENAI_API_KEY not found in environment")
if not os.getenv("TAVILY_API_KEY"):
    raise ValueError("TAVILY_API_KEY not found in environment")

TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
SERVER_PATH = "/Users/arun/Documents/RamSELabs/Corporate Training/Course Materials/ces_it/agents_demos/mcp-servers-ces/mcp-server-demo/main.py"

async def run_research_pipeline(writer_agent, editor_agent, topic: str, greeting_msg: str, greeting_prompt_text: str):
    """1) Writer researches+drafts with both Tavily and Weather tools, 2) Editor refines."""
    print(f"\n{'='*60}")
    print(f"📝 Topic: {topic}")
    print(f"{'='*60}\n")

    # Display the greeting resource
    print(f"📬 MCP Resource Greeting: {greeting_msg}\n")
    
    print("🔍 Writer Agent researching with Tavily and Weather MCP tools...\n")

    writer_result = await writer_agent.ainvoke(
        {
            "messages": [
                HumanMessage(
                    content=(
                        f"{greeting_prompt_text}\n\n"
                        f"Now, please research and write a detailed article on: '{topic}'\n\n"
                        "Instructions:\n"
                        "1. Use tavily-search to find the latest information and trends about climate impact\n"
                        "2. Use get_weather to check current weather conditions in major cities mentioned\n"
                        "3. Search multiple angles: current state, future predictions, challenges\n"
                        "4. Write a comprehensive article incorporating your research findings and real weather data\n"
                        "5. Include relevant facts, statistics, current weather conditions, and developments\n"
                        "6. Start your article with a friendly greeting to engage the reader"
                    )
                )
            ]
        }
    )

    written_content = writer_result["messages"][-1].content

    print("✅ Writer Agent completed. Passing to Editor...\n")
    print(f"{'='*60}\n")

    print("✏️  Editor Agent refining content...\n")

    editor_result = await editor_agent.ainvoke(
        {
            "messages": [
                HumanMessage(
                    content=(
                        "Please refine and enhance the following article:\n\n"
                        f"{written_content}\n\n"
                        "Focus on:\n"
                        "- Clarity and flow\n"
                        "- Grammar and style\n"
                        "- Structure and readability\n"
                        "- Fact consistency and accuracy"
                    )
                )
            ]
        }
    )

    refined_content = editor_result["messages"][-1].content

    print("✅ Editor Agent completed!\n")
    print(f"{'='*60}\n")

    return {"topic": topic, "draft": written_content, "final": refined_content}


async def main():
    """Main execution function."""
    
    client = MultiServerMCPClient(
        {
            "tavily": {
                "transport": "streamable_http",
                "url": f"https://mcp.tavily.com/mcp/?tavilyApiKey={TAVILY_API_KEY}",
                "headers": {
                    "DEFAULT_PARAMETERS": '{"search_depth":"advanced","max_results":5}'
                },
            },
            "weather-server": {
                "transport": "stdio",
                "command": "uv",
                "args": ["run", "python", SERVER_PATH],
            }
        }
    )

    print("🔌 Creating MCP sessions...\n")

    topic = "Climate Change Impact on Major Global Cities: Current Weather Patterns and Future Predictions"

    # Load tools, resources, and prompts from both MCP servers
    async with client.session("tavily") as tavily_session, \
               client.session("weather-server") as weather_session:
        
        # ===== LOAD TOOLS =====
        # Load Tavily tools
        tavily_tools = await load_mcp_tools(tavily_session)
        print(f"✅ Loaded {len(tavily_tools)} tools from Tavily MCP:")
        for tool in tavily_tools:
            print(f"   - {tool.name}: {tool.description}")
        print()

        # Load Weather tools
        weather_tools = await load_mcp_tools(weather_session)
        print(f"✅ Loaded {len(weather_tools)} tools from Weather MCP:")
        for tool in weather_tools:
            print(f"   - {tool.name}: {tool.description}")
        print()

        # Combine all tools for the writer agent
        all_tools = tavily_tools + weather_tools
        print(f"✅ Total tools available: {len(all_tools)}\n")
        
        # ===== LOAD RESOURCES =====
        # List available resources from Weather MCP server
        print("📦 Listing resources from Weather MCP...\n")
        resources_list = await weather_session.list_resources()
        for resource in resources_list.resources:
            print(f"   - {resource.name} ({resource.uri})")
            print(f"     Description: {resource.description}")
            if hasattr(resource, 'mimeType'):
                print(f"     MIME Type: {resource.mimeType}")
        print()
        
        # Note: Resources might not be readable due to MCP server implementation
        # The server's read_resource handler needs to return ReadResourceResult
        greeting_msg = "Hello! Welcome to the MCP Demo Server!"  # Default fallback
        print(f"📬 Using default greeting: {greeting_msg}\n")
        
        # ===== LOAD PROMPTS =====
        # List available prompts from Weather MCP server
        print("📝 Listing prompts from Weather MCP...\n")
        prompts_list = await weather_session.list_prompts()
        for prompt in prompts_list.prompts:
            print(f"   - {prompt.name}: {prompt.description}")
            if hasattr(prompt, 'arguments') and prompt.arguments:
                print(f"     Arguments:")
                for arg in prompt.arguments:
                    required_str = "(required)" if arg.required else "(optional)"
                    print(f"       * {arg.name}: {arg.description} {required_str}")
        print()
        
        # Get a specific prompt with custom arguments
        print("🎭 Generating custom greeting prompt...\n")
        greeting_prompt_result = await weather_session.get_prompt(
            "greet_user",
            {"name": "Climate Researcher", "style": "friendly"}
        )
        greeting_prompt_text = greeting_prompt_result.messages[0].content.text
        print(f"✅ Generated: {greeting_prompt_text}\n")

        # Create Writer Agent with both Tavily and Weather MCP tools
        writer_agent = create_agent(
            model="gpt-4o",
            system_prompt=(
                "You are a creative writer and researcher with experience in climate and environmental journalism. "
                "You have access to:\n"
                "1. Tavily's advanced search and extraction tools - use tavily-search with topic='general' to research climate trends\n"
                "2. Weather tools - use get_weather to check current conditions in cities you're writing about\n"
                "3. Math tools - use add/subtract for any calculations needed\n\n"
                "IMPORTANT: When using tavily-search, always set the topic parameter to 'general'.\n\n"
                "Before writing, research thoroughly using tavily-search, then get real-time weather data for major cities. "
                "Incorporate both research findings and actual current weather conditions into your article."
            ),
            tools=all_tools,
        )
        
        print("✅ Writer Agent with Tavily + Weather MCP tools created\n")

        # Create Editor Agent (no tools)
        editor_agent = create_agent(
            model="gpt-4o-mini",
            system_prompt="You are a meticulous editor, skilled at refining and enhancing written content.",
        )
        
        print("✅ Editor Agent created\n")

        # Run the pipeline with MCP resources and prompts
        result = await run_research_pipeline(
            writer_agent, 
            editor_agent, 
            topic,
            greeting_msg,
            greeting_prompt_text
        )

        # Display results
        print("\n" + "=" * 60)
        print("📄 FINAL OUTPUT")
        print("=" * 60)
        print(f"\nTopic: {result['topic']}\n")

        print("\n" + "-" * 60)
        print("📋 Draft Content (Research + Weather Data via MCP):")
        print("-" * 60)
        print(result["draft"])

        print("\n" + "-" * 60)
        print("✨ Refined Content:")
        print("-" * 60)
        print(result["final"])

    print("\n✅ MCP sessions closed automatically")


if __name__ == "__main__":
    asyncio.run(main())
