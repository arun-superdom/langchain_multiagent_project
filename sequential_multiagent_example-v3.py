# this example uses MCP server 

# TAVILY_API_URL=https://mcp.tavily.com/mcp/?tavilyApiKey=
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


async def run_sequential_pipeline(writer_agent, editor_agent, topic: str):
    """1) Writer researches+drafts, 2) Editor refines."""
    print(f"\n{'='*60}")
    print(f"📝 Topic: {topic}")
    print(f"{'='*60}\n")

    print("🔍 Writer Agent researching with Tavily MCP...\n")

    writer_result = await writer_agent.ainvoke(
        {
            "messages": [
                HumanMessage(
                    content=(
                        f"Please research and write a detailed article on: '{topic}'\n\n"
                        "Instructions:\n"
                        "1. Use tavily-search to find the latest information and trends\n"
                        "2. Search multiple angles: current state, future predictions, challenges\n"
                        "3. Write a comprehensive article incorporating your research findings\n"
                        "4. Include relevant facts, statistics, and current developments"
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
            "transport": "streamable_http",  # HTTP transport for remote MCP server 
                "url": f"https://mcp.tavily.com/mcp/?tavilyApiKey={TAVILY_API_KEY}",
                "headers": {
                    "DEFAULT_PARAMETERS": '{"search_depth":"advanced","max_results":5}'
                },
            }
        }
    )

    print("🔌 Creating MCP session to Tavily...\n")

    topic = "The Future of Artificial Intelligence in Everyday Life"

    # Use session context manager for proper lifecycle
    async with client.session("tavily") as session:
        # Load tools from the session
        tavily_tools = await load_mcp_tools(session)

        print(f"✅ Loaded {len(tavily_tools)} tools from Tavily MCP:")
        for tool in tavily_tools:
            print(f"   - {tool.name}: {tool.description}")
        print()

        # Create Writer Agent with MCP tools
        writer_agent = create_agent(
            model="gpt-4o",
            system_prompt=(
                "You are a creative writer with working experience in a top media company. "
                "You have access to Tavily's advanced search and extraction tools via MCP. "
                "Before writing, use tavily-search to research the topic thoroughly and gather latest information. "
                "Use tavily-extract if you need to extract content from specific URLs."
            ),
            tools=tavily_tools,
        )
        
        print("✅ Writer Agent with Tavily MCP tools created\n")

        # Create Editor Agent (no tools)
        editor_agent = create_agent(
            model="gpt-4o-mini",
            system_prompt="You are a meticulous editor, skilled at refining and enhancing written content.",
        )
        
        print("✅ Editor Agent created\n")

        # Run the pipeline
        result = await run_sequential_pipeline(writer_agent, editor_agent, topic)

        # Display results
        print("\n" + "=" * 60)
        print("📄 FINAL OUTPUT")
        print("=" * 60)
        print(f"\nTopic: {result['topic']}\n")

        print("\n" + "-" * 60)
        print("📋 Draft Content (Research-backed via MCP):")
        print("-" * 60)
        print(result["draft"])

        print("\n" + "-" * 60)
        print("✨ Refined Content:")
        print("-" * 60)
        print(result["final"])

    print("\n✅ MCP session closed automatically")


if __name__ == "__main__":
    asyncio.run(main())

