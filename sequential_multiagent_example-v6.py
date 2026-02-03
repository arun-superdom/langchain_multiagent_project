# Example using MCP with Guardrails (PII Redaction, Harmful Text Detection)


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


load_dotenv()

# Verify API keys
if not os.getenv("OPENAI_API_KEY"):
    raise ValueError("OPENAI_API_KEY not found in environment")
if not os.getenv("TAVILY_API_KEY"):
    raise ValueError("TAVILY_API_KEY not found in environment")

TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
SERVER_PATH = "/Users/arun/Documents/RamSELabs/Corporate Training/Course Materials/ces_it/agents_demos/mcp-servers-ces/mcp-server-demo/main.py"


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
# PIPELINE FUNCTIONS
# =============================================================================

async def run_research_pipeline(writer_agent, editor_agent, topic: str):
    """
    Pipeline with Guardrails:
    1. Input Guardrail: Check Topic for Harmful Content & Redact PII.
    2. Writer Agent researches and drafts
    3. Output Guardrail (Writer): Scan Writer output for PII/Harmful
    4. Editor Agent refines
    5. Output Guardrail (Editor): Final Scan
    """
    print(f"\n{'='*60}")
    print(f"📝 Raw Topic Input: {topic}")
    print(f"{'='*60}\n")

    # --- INPUT GUARDRAILS ---
    input_result = await apply_input_guardrails(topic)
    if not input_result.passed:
        return {"error": "Processing stopped due to harmful content detection in input."}
    
    clean_topic = input_result.text
    print(f"📝 Sanitized Topic: {clean_topic}")
    print(f"{'='*60}\n")

    print("🔍 Writer Agent researching with Tavily and Weather MCP tools...\n")

    writer_result = await writer_agent.ainvoke(
        {
            "messages": [
                HumanMessage(
                    content=(
                        f"Please research and write a detailed article on: '{clean_topic}'\n\n"
                        "Instructions:\n"
                        "1. Use tavily-search to find the latest information and trends about climate impact\n"
                        "2. Use get_weather to check current weather conditions in major cities mentioned\n"
                        "3. Search multiple angles: current state, future predictions, challenges\n"
                        "4. Write a comprehensive article incorporating your research findings and real weather data\n"
                        "5. Include relevant facts, statistics, current weather conditions, and developments"
                    )
                )
            ]
        }
    )

    written_content = writer_result["messages"][-1].content

    # --- INTERMEDIATE GUARDRAILS (Writer Output) ---
    writer_guardrail_result = await apply_output_guardrails(written_content, "Writer Output")
    if not writer_guardrail_result.passed:
        written_content = writer_guardrail_result.text
    else:
        written_content = writer_guardrail_result.text

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

    # --- FINAL OUTPUT GUARDRAILS ---
    final_guardrail_result = await apply_output_guardrails(refined_content, "Final Output")
    if not final_guardrail_result.passed:
        refined_content = final_guardrail_result.text
    else:
        refined_content = final_guardrail_result.text

    print("✅ Editor Agent completed!\n")
    print(f"{'='*60}\n")

    return {"topic": clean_topic, "draft": written_content, "final": refined_content}


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
        "Recent Financial Crisis Impact on Major Global Cities: Current Weather Patterns and Future Predictions. "
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

        # Run the pipeline
        result = await run_research_pipeline(writer_agent, editor_agent, topic)

        # Handle error case
        if "error" in result:
            print(f"\n❌ Pipeline Error: {result['error']}")
            return

        # Display results
        print("\n" + "=" * 60)
        print("📄 FINAL OUTPUT")
        print("=" * 60)
        print(f"\nTopic (Sanitized): {result['topic']}\n")

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
