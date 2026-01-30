# with tavily search tool integrated into the writer agent

import os
from langchain.agents import create_agent
from langchain.messages import HumanMessage
from langchain_tavily import TavilySearch #pip install langchain-tavily
from dotenv import load_dotenv

load_dotenv()

# Initialize Tavily Search Tool
tavily_tool = TavilySearch(
    max_results=10,
    topic="general",
    search_depth="advanced",  # Use advanced for better research quality
)


# Writer Agent WITH TOOL
writer_agent = create_agent(
    model="gpt-5.2",
    system_prompt="""You are a creative writer with working experience in Top Media Company. 
    You have access to web search capabilities. Before writing, use the search tool to 
    research the topic thoroughly to ensure accuracy and include latest information.""",
    tools=[tavily_tool],  # Add the search tool
)

print("Writer Agent with search tool created successfully.")

# Editor Agent (no changes)
editor_agent = create_agent(
    model="gpt-4o-mini",
    system_prompt="You are a meticulous editor, skilled at refining and enhancing written content",
)

print("Editor Agent created successfully.")


def run_sequential_pipeline(topic: str): 
    """
    Sequential multi-agent pipeline with tool-enabled Writer.
    1) Writer agent researches and creates content on a given topic
    2) Editor agent refines that content.
    """
    print(f"\n{'='*60}")
    print(f"Topic: {topic}")
    print(f"{'='*60}\n")
    
    # Step 1: Writer Agent researches and creates content
    print("🔍 Writer Agent researching and drafting...\n")
    
    writer_result = writer_agent.invoke(
        {
            "messages": [
                HumanMessage(
                    content=f"""Please research and write a detailed article on: '{topic}'
                    
                    Instructions:
                    1. First, search for latest information and trends about this topic
                    2. Then write a comprehensive article incorporating your research
                    3. Include relevant facts, statistics, and current developments"""
                )
            ]
        }
    )

    writer_messages = writer_result["messages"]
    written_content = writer_messages[-1].content

    print("✅ Writer Agent's Output Delivered to Editor Agent\n")
    print(f"{'='*60}\n")

    # Step 2: Editor Agent refines content
    print("✏️  Editor Agent refining content...\n")
    
    editor_result = editor_agent.invoke(
        {
            "messages": [
                HumanMessage(
                    content=f"""Please refine and enhance the following article:
                    
                    {written_content}
                    
                    Focus on:
                    - Clarity and flow
                    - Grammar and style
                    - Structure and readability
                    - Fact consistency"""
                )
            ]
        }
    )

    editor_messages = editor_result["messages"]
    refined_content = editor_messages[-1].content

    print("✅ Editor Agent Output Ready\n")
    print(f"{'='*60}\n")
    
    return {
        "topic": topic,
        "draft": written_content,
        "final": refined_content
    }


if __name__ == "__main__":
    # Ensure TAVILY_API_KEY is set in your .env file
    if not os.getenv("TAVILY_API_KEY"):
        print("⚠️  Warning: TAVILY_API_KEY not found in environment variables")
        print("Get your free API key at: https://tavily.com")
        exit(1)
    
    topic = "The odds of Humans Colonizing Mars in the Next 50 Years"
    result = run_sequential_pipeline(topic)

    print("\n" + "="*60)
    print("📄 FINAL OUTPUT")
    print("="*60)
    print(f"\nTopic: {result['topic']}\n")

    print("\n" + "-"*60)
    print("Draft Content (with research):")
    print("-"*60)
    print(result['draft'])

    print("\n" + "-"*60)
    print("Refined Content:")
    print("-"*60)
    print(result['final'])
