# Example using MCP, Guardrails (PII Redaction, Harmful Text Detection) and Memory
# Create an account in Mem0

# Example using MCP with Guardrails (PII Redaction, Harmful Text Detection) + Mem0 Memory

import os
import re
import asyncio
from dotenv import load_dotenv
from openai import OpenAI

from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_mcp_adapters.tools import load_mcp_tools

from langchain.agents import create_agent
from langchain.messages import HumanMessage
from langchain_openai import ChatOpenAI

# Import mem0
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

# Initialize Mem0 Client
mem0_client = MemoryClient(api_key=os.getenv("MEM0_API_KEY"))

# =============================================================================
# GUARDRAILS IMPLEMENTATION
# =============================================================================

class GuardrailResult:
    """Result from guardrail checks."""
    def __init__(self, passed: bool, text: str, issues: list = None):
        self.passed = passed
        self.text = text
        self.issues = issues or []

def redact_pii(text: str) -> GuardrailResult:
    """
    PII Redaction Guardrail - Detects and redacts personally identifiable information.
    
    Detects:
    - Email addresses
    - Phone numbers (US and international formats)
    - Social Security Numbers
    - Credit card numbers
    - IP addresses
    - Names following common patterns
    """
    print("🛡️  GUARDRAIL: Scanning for PII (Personally Identifiable Information)...")
    
    issues = []
    redacted_text = text
    
    # Email addresses
    email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
    emails_found = re.findall(email_pattern, redacted_text)
    if emails_found:
        issues.append(f"Emails detected: {len(emails_found)}")
        redacted_text = re.sub(email_pattern, '[REDACTED_EMAIL]', redacted_text)
    
    # Phone numbers (various formats)
    phone_patterns = [
        r'\+?1?[-.\s]?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}',  # US format
        r'\+\d{1,3}[-.\s]?\d{1,4}[-.\s]?\d{1,4}[-.\s]?\d{1,9}',  # International
    ]
    for pattern in phone_patterns:
        phones_found = re.findall(pattern, redacted_text)
        if phones_found:
            issues.append(f"Phone numbers detected: {len(phones_found)}")
            redacted_text = re.sub(pattern, '[REDACTED_PHONE]', redacted_text)
    
    # Social Security Numbers
    ssn_pattern = r'\b\d{3}[-.\s]?\d{2}[-.\s]?\d{4}\b'
    ssns_found = re.findall(ssn_pattern, redacted_text)
    if ssns_found:
        issues.append(f"SSN-like patterns detected: {len(ssns_found)}")
        redacted_text = re.sub(ssn_pattern, '[REDACTED_SSN]', redacted_text)
    
    # Credit card numbers (basic patterns)
    cc_pattern = r'\b(?:\d{4}[-.\s]?){3}\d{4}\b'
    ccs_found = re.findall(cc_pattern, redacted_text)
    if ccs_found:
        issues.append(f"Credit card-like patterns detected: {len(ccs_found)}")
        redacted_text = re.sub(cc_pattern, '[REDACTED_CC]', redacted_text)
    
    # IP addresses
    ip_pattern = r'\b(?:\d{1,3}\.){3}\d{1,3}\b'
    ips_found = re.findall(ip_pattern, redacted_text)
    if ips_found:
        issues.append(f"IP addresses detected: {len(ips_found)}")
        redacted_text = re.sub(ip_pattern, '[REDACTED_IP]', redacted_text)
    
    if issues:
        print(f"   ⚠️  PII Detected and Redacted: {', '.join(issues)}")
    else:
        print("   ✅ No PII detected.")
    
    return GuardrailResult(
        passed=True,  # PII redaction always passes (it just cleans the text)
        text=redacted_text,
        issues=issues
    )

async def detect_harmful_content(text: str) -> GuardrailResult:
    """
    Harmful Content Detection Guardrail - Uses OpenAI's moderation API.
    
    Checks for:
    - Hate speech
    - Harassment
    - Self-harm content
    - Sexual content
    - Violence
    - Illegal content
    """
    print("🛡️  GUARDRAIL: Checking for harmful content...")
    
    try:
        client = OpenAI()
        
        # Use OpenAI's moderation endpoint
        response = client.moderations.create(input=text)
        
        result = response.results[0]
        
        if result.flagged:
            # Collect all flagged categories
            flagged_categories = []
            categories = result.categories
            
            if categories.hate:
                flagged_categories.append("hate")
            if categories.harassment:
                flagged_categories.append("harassment")
            if categories.self_harm:
                flagged_categories.append("self-harm")
            if categories.sexual:
                flagged_categories.append("sexual")
            if categories.violence:
                flagged_categories.append("violence")
            if hasattr(categories, 'self_harm_intent') and categories.self_harm_intent:
                flagged_categories.append("self-harm-intent")
            if hasattr(categories, 'hate_threatening') and categories.hate_threatening:
                flagged_categories.append("hate-threatening")
            if hasattr(categories, 'violence_graphic') and categories.violence_graphic:
                flagged_categories.append("violence-graphic")
            
            print(f"   ❌ BLOCKED: Harmful content detected! Categories: {', '.join(flagged_categories)}")
            return GuardrailResult(
                passed=False,
                text=text,
                issues=[f"Harmful content: {', '.join(flagged_categories)}"]
            )
        
        print("   ✅ Content passed moderation check.")
        return GuardrailResult(passed=True, text=text, issues=[])
        
    except Exception as e:
        print(f"   ⚠️  Moderation check warning: {e}")
        # Fail open - allow content if moderation service fails
        return GuardrailResult(passed=True, text=text, issues=[f"Moderation check skipped: {e}"])

async def apply_input_guardrails(text: str) -> GuardrailResult:
    """Apply all input guardrails in sequence."""
    print("\n🔒 ACTIVATING INPUT GUARDRAILS...")
    
    # Step 1: Check for harmful content
    harmful_result = await detect_harmful_content(text)
    if not harmful_result.passed:
        return harmful_result
    
    # Step 2: Redact PII
    pii_result = redact_pii(text)
    
    print("🔓 Input guardrails complete.\n")
    return pii_result

async def apply_output_guardrails(text: str, stage: str = "Output") -> GuardrailResult:
    """Apply all output guardrails in sequence."""
    print(f"\n🔒 ACTIVATING {stage.upper()} GUARDRAILS...")
    
    # Step 1: Check for harmful content
    harmful_result = await detect_harmful_content(text)
    if not harmful_result.passed:
        return GuardrailResult(
            passed=False,
            text="[CONTENT BLOCKED BY MODERATION - Harmful content detected]",
            issues=harmful_result.issues
        )
    
    # Step 2: Redact any PII that might have been generated
    pii_result = redact_pii(text)
    
    print(f"🔓 {stage} guardrails complete.\n")
    return pii_result

# =============================================================================
# MEM0 HELPER FUNCTIONS (FIXED FOR V2 API)
# =============================================================================

def retrieve_memories(query: str, user_id: str, limit: int = 5) -> str:
    """
    Retrieve relevant memories from mem0 based on the query.
    
    Args:
        query: Search query to find relevant memories
        user_id: User identifier for personalized memories
        limit: Maximum number of memories to retrieve
    
    Returns:
        Formatted string of memories or empty string if none found
    """
    try:
        print(f"🧠 Retrieving memories for user: {user_id}...")
        
        # FIX: Mem0 v2 API requires filters with logical operators
        filters = {
            "AND": [
                {"user_id": user_id}
            ]
        }
        
        # Search memories with mem0 v2 API
        search_results = mem0_client.search(
            query=query,
            version="v2",  # IMPORTANT: Must specify v2
            filters=filters,
            limit=limit
        )
        
        # Extract memories from results
        if search_results and 'results' in search_results:
            memories = search_results['results']
            
            if memories:
                # Format memories for context
                formatted_memories = []
                for idx, mem in enumerate(memories, 1):
                    memory_text = mem.get('memory', '')
                    if memory_text:
                        formatted_memories.append(f"{idx}. {memory_text}")
                
                if formatted_memories:
                    result = '\n'.join(formatted_memories)
                    print(f"   ✅ Found {len(formatted_memories)} relevant memories")
                    return result
        
        print("   ℹ️  No previous memories found")
        return ""
        
    except Exception as e:
        print(f"   ⚠️  Memory retrieval error: {e}")
        return ""


def save_memory(user_id: str, messages: list, metadata: dict = None):
    """
    Save conversation to mem0.
    
    Args:
        user_id: User identifier
        messages: List of message dicts with 'role' and 'content'
        metadata: Optional metadata dict for categorizing memories
    
    Returns:
        Result from mem0 add operation or None if failed
    """
    try:
        print(f"\n💾 Saving interaction to mem0 for user: {user_id}...")
        
        # Add messages to mem0 - user_id is passed directly for add operation
        result = mem0_client.add(
            messages=messages,
            user_id=user_id,
            metadata=metadata
        )
        
        # Check results
        if result and 'results' in result:
            memories_added = len(result['results'])
            print(f"   ✅ Successfully saved {memories_added} memories")
        else:
            print(f"   ✅ Memory saved successfully")
        
        return result
        
    except Exception as e:
        print(f"   ⚠️  Memory save error: {e}")
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



def search_with_advanced_filters(query: str, user_id: str, categories: list = None, limit: int = 5):
    """
    Advanced search with category filtering.
    
    Args:
        query: Search query
        user_id: User identifier
        categories: List of categories to filter by (e.g., ["research", "climate"])
        limit: Maximum results
    
    Returns:
        Formatted string of memories
    """
    try:
        print(f"🔍 Advanced search with filters...")
        
        # Build filters with categories if provided
        filter_conditions = [{"user_id": user_id}]
        
        if categories:
            # Use 'in' operator for exact category matching
            filter_conditions.append({
                "categories": {"in": categories}
            })
        
        filters = {"AND": filter_conditions}
        
        search_results = mem0_client.search(
            query=query,
            version="v2",
            filters=filters,
            limit=limit
        )
        
        if search_results and 'results' in search_results:
            memories = search_results['results']
            if memories:
                formatted = '\n'.join([f"- {m.get('memory', '')}" for m in memories])
                print(f"   ✅ Found {len(memories)} memories")
                return formatted
        
        print("   ℹ️  No memories found")
        return ""
        
    except Exception as e:
        print(f"   ⚠️  Advanced search error: {e}")
        return ""

        
# =============================================================================
# PIPELINE FUNCTIONS WITH MEM0
# =============================================================================

async def run_research_pipeline(writer_agent, editor_agent, topic: str, user_id: str = "researcher"):
    """
    Enhanced Pipeline with Guardrails + Mem0:
    1. Retrieve relevant memories from past research
    2. Input Guardrail: Check Topic for Harmful Content & Redact PII
    3. Writer Agent researches with context from memories
    4. Output Guardrail (Writer): Scan Writer output for PII/Harmful
    5. Editor Agent refines
    6. Output Guardrail (Editor): Final Scan
    7. Save interaction to mem0 for future use
    """
    print(f"\n{'='*60}")
    print(f"📝 Research Pipeline Starting")
    print(f"{'='*60}\n")
    print(f"Raw Topic Input: {topic}\n")

    # --- STEP 1: RETRIEVE MEMORIES ---
    print(f"{'='*60}")
    print("STEP 1: MEMORY RETRIEVAL")
    print(f"{'='*60}\n")
    
    past_context = retrieve_memories(query=topic, user_id=user_id, limit=5)
    
    print(f"\n{'='*60}\n")

    # --- STEP 2: INPUT GUARDRAILS ---
    print(f"{'='*60}")
    print("STEP 2: INPUT VALIDATION")
    print(f"{'='*60}\n")
    
    input_result = await apply_input_guardrails(topic)
    if not input_result.passed:
        print(f"\n❌ Pipeline stopped: {input_result.issues}")
        return {"error": "Processing stopped due to harmful content detection in input."}
    
    clean_topic = input_result.text
    print(f"\n✅ Sanitized Topic: {clean_topic}")
    print(f"\n{'='*60}\n")

    # --- STEP 3: WRITER AGENT WITH MEMORY CONTEXT ---
    print(f"{'='*60}")
    print("STEP 3: WRITER AGENT (Research + Draft)")
    print(f"{'='*60}\n")
    
    # Build enhanced prompt with memory context
    memory_context_section = f"""
Previous Research Context (from memory):
{past_context if past_context else "No previous research found on this topic."}
""" if past_context else "This is a new research topic with no previous context."

    writer_prompt = f"""Please research and write a detailed article on: '{clean_topic}'

{memory_context_section}

Instructions:
1. Use tavily-search to find the latest information and trends about the topic
2. Use get_weather to check current weather conditions in major cities mentioned
3. If previous research context exists, build upon it - avoid repetition and add new insights
4. Search multiple angles: current state, future predictions, challenges
5. Write a comprehensive article incorporating your research findings and real weather data
6. Include relevant facts, statistics, current weather conditions, and developments
"""

    print("🔍 Writer Agent researching with Tavily, Weather MCP tools, and mem0 context...\n")

    writer_result = await writer_agent.ainvoke(
        {
            "messages": [
                HumanMessage(content=writer_prompt)
            ]
        }
    )

    written_content = writer_result["messages"][-1].content

    print("\n✅ Writer Agent completed draft.\n")
    print(f"{'='*60}\n")

    # --- STEP 4: WRITER OUTPUT GUARDRAILS ---
    print(f"{'='*60}")
    print("STEP 4: WRITER OUTPUT VALIDATION")
    print(f"{'='*60}\n")
    
    writer_guardrail_result = await apply_output_guardrails(written_content, "Writer Output")
    if not writer_guardrail_result.passed:
        written_content = writer_guardrail_result.text
        print(f"\n⚠️  Writer output was blocked/modified")
    else:
        written_content = writer_guardrail_result.text
        print(f"\n✅ Writer output passed validation")

    print(f"\n{'='*60}\n")

    # --- STEP 5: EDITOR AGENT ---
    print(f"{'='*60}")
    print("STEP 5: EDITOR AGENT (Refinement)")
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

    print("\n✅ Editor Agent completed refinement.\n")
    print(f"{'='*60}\n")

    # --- STEP 6: FINAL OUTPUT GUARDRAILS ---
    print(f"{'='*60}")
    print("STEP 6: FINAL OUTPUT VALIDATION")
    print(f"{'='*60}\n")
    
    final_guardrail_result = await apply_output_guardrails(refined_content, "Final Output")
    if not final_guardrail_result.passed:
        refined_content = final_guardrail_result.text
        print(f"\n⚠️  Final output was blocked/modified")
    else:
        refined_content = final_guardrail_result.text
        print(f"\n✅ Final output passed validation")

    print(f"\n{'='*60}\n")

    # --- STEP 7: SAVE TO MEM0 ---
    print(f"{'='*60}")
    print("STEP 7: SAVING TO MEMORY")
    print(f"{'='*60}\n")
    
    # Prepare conversation for memory storage
    interaction_messages = [
        {"role": "user", "content": f"Research topic: {clean_topic}"},
        {"role": "assistant", "content": refined_content}
    ]
    
    # Save with metadata for better organization
    metadata = {
        "topic": clean_topic,
        "type": "research_article",
        "timestamp": asyncio.get_event_loop().time()
    }
    
    save_memory(
        user_id=user_id,
        messages=interaction_messages,
        metadata=metadata
    )
    
    print(f"\n{'='*60}\n")

    return {
        "topic": clean_topic,
        "memories_used": past_context,
        "had_previous_context": bool(past_context),
        "draft": written_content,
        "final": refined_content
    }

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

    # Example INPUT with potential PII to demonstrate guardrails
    topic = (
        "Recent Climate Change Impact on Major Global Cities: Current Weather Patterns and Future Predictions. "
        "Contact info: researcher@climate-org.com or call 555-123-4567 for more details."
    )

    # Load tools from both MCP servers
    async with client.session("tavily") as tavily_session, \
               client.session("weather-server") as weather_session:
        
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

        # Run the pipeline with mem0 integration
        result = await run_research_pipeline(
            writer_agent, 
            editor_agent, 
            topic,
            user_id="climate_researcher"  # Unique identifier for this research context
        )

        # Handle error case
        if "error" in result:
            print(f"\n❌ Pipeline Error: {result['error']}")
            return

        # Display results
        print("\n" + "=" * 80)
        print("📄 FINAL RESEARCH OUTPUT (with Mem0 Context)")
        print("=" * 80)
        print(f"\nTopic (Sanitized): {result['topic']}\n")

        # Show if previous context was used
        if result['had_previous_context']:
            print("\n" + "-" * 80)
            print("🧠 Previous Research Context Used:")
            print("-" * 80)
            print(result['memories_used'])
        else:
            print("\n" + "-" * 80)
            print("🆕 This is new research - no previous context available")
            print("-" * 80)

        print("\n" + "-" * 80)
        print("📋 Draft Content (Research + Weather Data via MCP):")
        print("-" * 80)
        print(result["draft"])

        print("\n" + "-" * 80)
        print("✨ Refined Content (Editor Enhanced):")
        print("-" * 80)
        print(result["final"])

        # Optional: Show all memories for this user
        print("\n" + "=" * 80)
        print("📚 All Stored Memories for this User:")
        print("=" * 80)
        all_memories = get_all_memories(user_id="climate_researcher")
        for idx, mem in enumerate(all_memories, 1):
            print(f"\n{idx}. {mem.get('memory', 'N/A')}")
            if 'metadata' in mem:
                print(f"   Metadata: {mem['metadata']}")

    print("\n✅ MCP sessions closed automatically")
    print("\n🎉 Pipeline completed successfully with Mem0 integration!\n")

if __name__ == "__main__":
    asyncio.run(main())
