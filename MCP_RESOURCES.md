# MCP Resources and Prompts Guide

This guide explains how to use MCP (Model Context Protocol) **Resources** and **Prompts** in addition to Tools with LangChain agents.

## Overview

The Model Context Protocol (MCP) provides three main capabilities:

1. **Tools** - Functions that agents can call to perform actions (e.g., `get_weather`, `add`)
2. **Resources** - Static or dynamic data that can be read (e.g., configuration, documentation, greetings)
3. **Prompts** - Templated instructions that can be customized with arguments (e.g., greeting styles)

## What Are MCP Resources?

**Resources** are URI-addressable pieces of content that an MCP server exposes. They can be:
- Static content (configuration files, documentation)
- Dynamic content (current state, generated data)
- Any text-based information with a MIME type

### Resource Structure

```python
types.Resource(
    uri="greeting://default",           # Unique URI identifier
    name="Default Greeting",             # Human-readable name
    mimeType="text/plain",              # Content type
    description="A default greeting message"  # What it contains
)
```

### Using Resources in Your Code

```python
from langchain_mcp_adapters.resources import load_mcp_resources

# Load all available resources
resources = await load_mcp_resources(session)

# Read a specific resource by URI
resource_content = await session.read_resource("greeting://default")
message = resource_content[0].text
```

### Common Use Cases for Resources

- **Configuration data** - Application settings, API endpoints
- **Documentation** - Help text, usage guidelines
- **Static content** - Welcome messages, templates
- **Dynamic content** - Current state, cached data
- **Reference data** - Lookup tables, constants

## What Are MCP Prompts?

**Prompts** are templated instructions with customizable arguments. They help standardize how you interact with agents while allowing flexibility through parameters.

### Prompt Structure

```python
types.Prompt(
    name="greet_user",
    description="Generate a greeting with different styles",
    arguments=[
        types.PromptArgument(
            name="name",
            description="The person's name to greet",
            required=True,
        ),
        types.PromptArgument(
            name="style",
            description="The style of greeting",
            required=False,
        ),
    ],
)
```

### Using Prompts in Your Code

```python
from langchain_mcp_adapters.prompts import load_mcp_prompts

# Load all available prompts
prompts = await load_mcp_prompts(session)

# Get a prompt with specific arguments
prompt_result = await session.get_prompt(
    "greet_user",
    {"name": "Alice", "style": "formal"}
)

# Extract the generated prompt text
prompt_text = prompt_result.messages[0].content.text
```

### Common Use Cases for Prompts

- **Standardized instructions** - Consistent task descriptions
- **Customizable templates** - Variable content with fixed structure
- **Multi-style responses** - Different tones (formal, casual, friendly)
- **Dynamic instructions** - Context-specific guidance
- **Reusable patterns** - Common workflows with parameters

## Complete Example: sequential_multiagent_example-v4_2.py

This example demonstrates using Tools, Resources, and Prompts together.

### What It Does

1. **Loads Tools** from Tavily (web search) and Weather MCP servers
2. **Loads Resources** to get a greeting message
3. **Loads Prompts** to generate a customized greeting instruction
4. **Uses all three** in a multi-agent pipeline:
   - Writer agent researches using tools
   - Writer uses the greeting prompt to engage readers
   - Editor refines the content

### Code Structure

```python
# Import MCP adapters
from langchain_mcp_adapters.tools import load_mcp_tools
from langchain_mcp_adapters.resources import load_mcp_resources
from langchain_mcp_adapters.prompts import load_mcp_prompts

# Create MCP client with multiple servers
client = MultiServerMCPClient({
    "tavily": {...},           # Remote HTTP server
    "weather-server": {...}    # Local stdio server
})

async with client.session("weather-server") as weather_session:
    # 1. Load Tools
    tools = await load_mcp_tools(weather_session)
    
    # 2. Load and Read Resources
    resources = await load_mcp_resources(weather_session)
    greeting = await weather_session.read_resource("greeting://default")
    
    # 3. Load and Get Prompts
    prompts = await load_mcp_prompts(weather_session)
    prompt = await weather_session.get_prompt(
        "greet_user",
        {"name": "Climate Researcher", "style": "friendly"}
    )
    
    # 4. Use them in your agent workflow
    agent = create_agent(model="gpt-4o", tools=tools, ...)
    result = await agent.ainvoke({"messages": [prompt, ...]})
```

## Running the Example

### Prerequisites

1. **API Keys** - Set up in `.env` file:
   ```env
   OPENAI_API_KEY=your_openai_key
   TAVILY_API_KEY=your_tavily_key
   OPENWEATHERMAP_API_KEY=your_weather_key
   ```

2. **Dependencies** - Install required packages:
   ```bash
   pip install -r requirements.txt
   ```

3. **MCP Server** - Ensure your MCP server is available at the specified path

### Run the Example

```bash
# Activate virtual environment
source .venv/bin/activate  # On Unix/macOS
# or
.venv\Scripts\activate  # On Windows

# Run the script
python sequential_multiagent_example-v4_2.py
```

### Expected Output

The script will:

1. **Connect to MCP servers** (Tavily and Weather)
2. **List all tools** from both servers
3. **List all resources** with their URIs and descriptions
4. **Display greeting resource** content
5. **List all prompts** with their arguments
6. **Generate a greeting prompt** with custom parameters
7. **Run the multi-agent pipeline**:
   - Writer researches climate change
   - Writer uses weather tools for real-time data
   - Writer incorporates the greeting prompt
   - Editor refines the article
8. **Display final output** with draft and refined versions

## Key Differences

| Feature | Tools | Resources | Prompts |
|---------|-------|-----------|---------|
| Purpose | Execute actions | Provide data | Generate instructions |
| Direction | Agent → Server | Server → Agent | Server → Agent |
| Dynamic | Yes (with args) | Can be static or dynamic | Dynamic (with args) |
| Returns | Execution result | Content/data | Instruction template |
| Use in Agent | Direct tool calling | Context enrichment | Instruction customization |

## Benefits of Using Resources and Prompts

### Resources
- **Consistency** - Single source of truth for data
- **Centralization** - Manage content in one place
- **Flexibility** - Easy to update without code changes
- **Reusability** - Multiple agents can access same resources

### Prompts
- **Standardization** - Consistent instructions across use cases
- **Customization** - Flexible parameters for different contexts
- **Maintainability** - Update prompts in one place
- **Quality** - Pre-tested, optimized instructions

## Advanced Usage

### Multiple Resources

```python
# Read multiple resources
config = await session.read_resource("config://app-settings")
docs = await session.read_resource("docs://api-guide")
examples = await session.read_resource("examples://use-cases")

# Use in agent context
context = f"{config}\\n{docs}\\n{examples}"
```

### Conditional Prompts

```python
# Choose prompt based on context
style = "formal" if is_business else "casual"
prompt = await session.get_prompt(
    "greet_user",
    {"name": user_name, "style": style}
)
```

### Resource Caching

```python
# Cache frequently accessed resources
resource_cache = {}

async def get_resource(session, uri):
    if uri not in resource_cache:
        content = await session.read_resource(uri)
        resource_cache[uri] = content[0].text
    return resource_cache[uri]
```

## Troubleshooting

### Common Issues

1. **Resource not found**
   - Verify the URI is correct
   - Check if the resource is registered in the MCP server
   - Ensure the session is connected

2. **Prompt arguments missing**
   - Check required vs optional arguments
   - Verify argument names match the prompt definition
   - Provide default values for optional args

3. **Import errors**
   - Ensure `langchain-mcp-adapters` is installed
   - Check version compatibility
   - Update packages if needed

### Debug Tips

```python
# List available resources
resources = await load_mcp_resources(session)
for r in resources:
    print(f"URI: {r.uri}, Name: {r.name}")

# List available prompts
prompts = await load_mcp_prompts(session)
for p in prompts:
    print(f"Name: {p.name}, Args: {p.arguments}")
```

## Best Practices

1. **Use descriptive URIs** - Make resource URIs self-documenting
2. **Document prompts** - Clear descriptions and argument usage
3. **Error handling** - Handle missing resources gracefully
4. **Validate arguments** - Check prompt arguments before calling
5. **Cache when appropriate** - Don't reload static resources repeatedly
6. **Version resources** - Use URIs like `config://v2/settings` for versions

## Additional Resources

- [MCP Specification](https://modelcontextprotocol.io/docs)
- [LangChain MCP Adapters](https://github.com/langchain-ai/langchain-mcp)
- [MCP Server Examples](https://github.com/modelcontextprotocol/servers)

## Summary

This example demonstrates the full power of MCP by combining:
- **Tools** for taking actions (weather, search, math)
- **Resources** for accessing data (greetings, config)
- **Prompts** for customizing instructions (greeting styles)

All three work together to create sophisticated, flexible agent workflows that are maintainable and reusable.
