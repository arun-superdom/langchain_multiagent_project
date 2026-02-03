# Simplified Multi-Agent Pipeline with MCP Tools + Mem0 Memory

# This example is without guardrails for clarity.

import os
import asyncio
from dotenv import load_dotenv

from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_mcp_adapters.tools import load_mcp_tools
from langchain.agents import create_agent
from langchain.messages import HumanMessage
from langchain_openai import ChatOpenAI

from mem0 import MemoryClient

load_dotenv()

# Verify API keys
if not os.getenv("OPENAI_API_KEY"):
    raise ValueError("OPENAI_API_KEY not found in environment")
if not os.getenv("TAVILY_API_KEY"):
    raise ValueError("TAVILY_API_KEY not found in environment")
if not os.getenv("MEM0_API_KEY"):
    raise ValueError("MEM0_API_KEY not found in environment")

TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
SERVER_PATH = "/Users/arun/Documents/RamSELabs/Corporate Training/Course Materials/ces_it/agents_demos/mcp-servers-ces/mcp-server-demo/main.py"

# Initialize Mem0
mem0_client = MemoryClient(api_key=os.getenv("MEM0_API_KEY"))

# =============================================================================
# MEM0 HELPER FUNCTIONS
# =============================================================================

def retrieve_memories(query: str, user_id: str, limit: int = 5) -> str:
    """Retrieve relevant memories from mem0."""
    try:
        print(f"🧠 Retrieving memories for user: {user_id}...")
        
        filters = {
            "AND": [
                {"user_id": user_id}
            ]
        }
        
        search_results = mem0_client.search(
            query=query,
            version="v2",
            filters=filters,
            limit=limit
        )
        
        if search_results and 'results' in search_results:
            memories = search_results['results']
            if memories:
                formatted = '\n'.join([f"{i+1}. {m.get('memory', '')}" for i, m in enumerate(memories)])
                print(f"   ✅ Found {len(memories)} relevant memories\n")
                return formatted
        
        print("   ℹ️  No previous memories found\n")
        return ""
        
    except Exception as e:
        print(f"   ⚠️  Memory retrieval error: {e}\n")
        return ""

def save_memory(user_id: str, messages: list, metadata: dict = None):
    """Save conversation to mem0."""
    try:
        print(f"💾 Saving to mem0...")
        
        result = mem0_client.add(
            messages=messages,
            user_id=user_id,
            metadata=metadata
        )
        
        if result and 'results' in result:
            print(f"   ✅ Saved {len(result['results'])} memories\n")
        else:
            print(f"   ✅ Memory saved\n")
        
        return result
        
    except Exception as e:
        print(f"   ⚠️  Memory save error: {e}\n")
        return None

def get_all_memories(user_id: str):
    """Retrieve all memories for a user."""
    try:
        print(f"📚 Retrieving all memories for user: {user_id}...")
        
        # FIX: v2 API requires filters for get_all too
        filters = {
            "AND": [
                {"user_id": user_id}
            ]
        }
        
        all_memories = mem0_client.get_all(
            version="v2",  # Must specify v2
            filters=filters  # Required in v2
        )
        
        if all_memories and 'results' in all_memories:
            count = len(all_memories['results'])
            print(f"   ✅ Found {count} total memories\n")
            return all_memories['results']
        
        print("   ℹ️  No memories found\n")
        return []
        
    except Exception as e:
        print(f"   ⚠️  Error: {e}\n")
        return []


# =============================================================================
# PIPELINE
# =============================================================================

async def run_research_pipeline(writer_agent, editor_agent, topic: str, user_id: str = "researcher"):
    """
    Multi-Agent Research Pipeline with Memory:
    1. Retrieve past research from mem0
    2. Writer Agent researches with MCP tools + memory context
    3. Editor Agent refines
    4. Save to mem0 for future use
    """
    print(f"\n{'='*60}")
    print(f"📝 RESEARCH PIPELINE: {topic}")
    print(f"{'='*60}\n")

    # Retrieve memories
    past_context = retrieve_memories(query=topic, user_id=user_id, limit=5)
    
    # Build writer prompt with memory context
    memory_section = f"""
Previous Research Context:
{past_context if past_context else "No previous research on this topic."}
""" if past_context else "This is a new research topic."

    writer_prompt = f"""Research and write a detailed article on: '{topic}'

{memory_section}

Instructions:
1. Use tavily-search (topic='general') to find latest information
2. Use get_weather for current conditions in relevant cities
3. Build upon previous context if available
4. Write a comprehensive article with research findings and weather data
5. Include facts, statistics, and current developments
"""

    print("🔍 Writer Agent researching...\n")
    
    writer_result = await writer_agent.ainvoke(
        {"messages": [HumanMessage(content=writer_prompt)]}
    )
    
    draft = writer_result["messages"][-1].content
    print("✅ Draft completed\n")
    
    # Editor refinement
    print("✏️  Editor Agent refining...\n")
    
    editor_result = await editor_agent.ainvoke(
        {
            "messages": [
                HumanMessage(
                    content=f"""Refine and enhance this article:

{draft}

Focus on:
- Clarity and flow
- Grammar and style
- Structure and readability
- Fact consistency
"""
                )
            ]
        }
    )
    
    final = editor_result["messages"][-1].content
    print("✅ Refinement completed\n")
    
    # Save to mem0
    interaction = [
        {"role": "user", "content": f"Research topic: {topic}"},
        {"role": "assistant", "content": final}
    ]
    
    save_memory(
        user_id=user_id,
        messages=interaction,
        metadata={"topic": topic, "type": "research_article"}
    )
    
    return {
        "topic": topic,
        "memories_used": past_context,
        "had_previous_context": bool(past_context),
        "draft": draft,
        "final": final
    }

async def main():
    """Main execution."""
    
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

    print("🔌 Initializing MCP sessions...\n")

    topic = "Climate Change Impact on Major Cities: Weather Patterns and Predictions"

    async with client.session("tavily") as tavily_session, \
               client.session("weather-server") as weather_session:
        
        # Load MCP tools
        tavily_tools = await load_mcp_tools(tavily_session)
        print(f"✅ Tavily tools: {len(tavily_tools)}")
        
        weather_tools = await load_mcp_tools(weather_session)
        print(f"✅ Weather tools: {len(weather_tools)}")
        
        all_tools = tavily_tools + weather_tools
        print(f"✅ Total tools: {len(all_tools)}\n")

        # Create agents
        writer_agent = create_agent(
            model="gpt-4o",
            system_prompt=(
                "You are a creative writer and researcher specializing in climate journalism. "
                "Use tavily-search (topic='general') to research and get_weather for current conditions. "
                "Research thoroughly, then incorporate real-time weather data into your article."
            ),
            tools=all_tools,
        )
        print("✅ Writer Agent created\n")

        editor_agent = create_agent(
            model="gpt-4o-mini",
            system_prompt="You are a meticulous editor skilled at refining written content.",
        )
        print("✅ Editor Agent created\n")

        # Run pipeline
        result = await run_research_pipeline(
            writer_agent, 
            editor_agent, 
            topic,
            user_id="climate_researcher"
        )

        # Display results
        print("=" * 80)
        print("📄 FINAL OUTPUT")
        print("=" * 80)
        print(f"\nTopic: {result['topic']}\n")

        if result['had_previous_context']:
            print("-" * 80)
            print("🧠 Previous Context Used:")
            print("-" * 80)
            print(result['memories_used'])
        else:
            print("-" * 80)
            print("🆕 New research - no previous context")
            print("-" * 80)

        print("\n" + "-" * 80)
        print("📋 DRAFT:")
        print("-" * 80)
        print(result["draft"])

        print("\n" + "-" * 80)
        print("✨ FINAL:")
        print("-" * 80)
        print(result["final"])

        # Show all memories
        print("\n" + "=" * 80)
        print("📚 ALL MEMORIES:")
        print("=" * 80)
        all_mems = get_all_memories("climate_researcher")
        for i, m in enumerate(all_mems, 1):
            print(f"\n{i}. {m.get('memory', 'N/A')}")

    print("\n✅ Complete!\n")

if __name__ == "__main__":
    asyncio.run(main())
