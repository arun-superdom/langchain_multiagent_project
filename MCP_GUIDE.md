
# Model Context Protocol (MCP) Guide

## Introduction

The Model Context Protocol (MCP) is a standardized protocol that enables AI agents and language models to securely access external tools and data sources. It provides a unified way for AI systems to interact with various services, APIs, and resources through a well-defined interface.

## What is MCP?

MCP is an open protocol developed by Anthropic that allows AI models to:
- Access external tools and services
- Execute functions and retrieve data
- Maintain context across interactions
- Work with diverse data sources securely

The protocol standardizes how AI agents can "call tools" - essentially executing code or accessing APIs to perform tasks beyond their built-in capabilities.

## Core Components

### MCP Server
An MCP server is a program that exposes tools and resources to AI clients. Servers can be:
- **Custom MCP Servers**: Built by developers for specific use cases
- **Official MCP Servers**: Provided by service providers (GitHub, Slack, Atlassian, etc.)
- **Community MCP Servers**: Third-party servers published by the community

### MCP Client
An MCP client is typically an AI agent or language model that connects to MCP servers to access tools. Clients:
- Discover available tools from servers
- Execute tool calls
- Handle responses and maintain context

### Transports
Transports define how clients and servers communicate:
- **stdio**: Local communication via standard input/output (for local servers)
- **SSE (Server-Sent Events)**: HTTP-based transport for remote connections (deprecated)
- **Streamable HTTP**: Modern HTTP transport for remote connections (recommended)

## Connection Models

### 1. stdio (Local Machine)
- Used for servers running on the same machine as the client
- Communication via standard input/output streams
- Ideal for development and local tool execution
- Transport: `"stdio"`
- **Server Management**: The MCP client **automatically starts the server process** when you create a session. No manual server startup needed.
- **Example Configuration**:
  ```python
  "weather-server": {
      "transport": "stdio",
      "command": "uv",  # or "python"
      "args": ["run", "python", "/path/to/server.py"],
  }
  ```
  When you call `client.session("weather-server")`, the client runs the command and manages the process automatically.

### 2. SSE (Server-Sent Events) - Deprecated
- HTTP-based transport for remote connections
- Server pushes updates to clients
- Limited bidirectional communication
- Transport: `"http"`
- **Server Management**: The server must be manually started before the client connects
- **Note**: This transport is deprecated in favor of Streamable HTTP

### 3. Streamable HTTP - Recommended
- Modern HTTP transport for remote connections
- Full bidirectional streaming
- Better performance and reliability
- Transport: `"streamable_http"`
- **Server Management**: The server must already be running at the specified URL. The client connects to it via HTTP.
- **Example Configuration**:
  ```python
  "tavily": {
      "transport": "streamable_http",
      "url": "https://mcp.tavily.com/mcp/?tavilyApiKey=YOUR_KEY",
      "headers": {"DEFAULT_PARAMETERS": '{"search_depth":"advanced"}'}
  }
  ```
  The server at the URL must be running and accessible before the client connects.

## Building an MCP Server

### Requirements
- Programming language support (Python, TypeScript, Java, Rust, etc.)
- MCP SDK or framework
- Tool definitions with proper schemas
- Transport configuration
- **For stdio**: Python/Node executable that can be launched by the client
- **For HTTP/Streamable HTTP**: Running server accessible at a network URL

### Server Structure
A typical MCP server includes:
1. **Tool Definitions**: Functions with names, descriptions, parameters, and return types
2. **Resource Handlers**: For serving data and files
3. **Prompt Handlers**: For providing context and instructions
4. **Transport Layer**: Handling client connections

### Tool Requirements
Each tool must have:
- **Function Name**: Unique identifier
- **Description**: Clear explanation of what the tool does
- **Parameters**: Input schema (if any)
- **Return Data**: Output format and structure

## Example: Custom LinkedIn MCP Server

### Overview
A LinkedIn MCP server could provide tools for social media automation and analysis.

### Implementation Steps
1. **Choose Transport**: Use `streamable_http` for remote access
2. **Define Tools**:
   - `linkedin_post_creator`: Create new posts
   - `linkedin_comment_writer`: Write comments on posts
   - `linkedin_search`: Search for content/people
   - `linkedin_post_like`: Like posts
   - `linkedin_profile_analyzer`: Analyze profiles
   - `linkedin_connection_manager`: Manage connections

3. **Tool Specifications**:
   ```json
   {
     "name": "linkedin_post_creator",
     "description": "Create a new LinkedIn post",
     "parameters": {
       "type": "object",
       "properties": {
         "content": {"type": "string", "description": "Post content"},
         "visibility": {"type": "string", "enum": ["public", "connections"]}
       },
       "required": ["content"]
     }
   }
   ```

### Supported Languages
- TypeScript
- Python
- Java
- Rust

## Security Considerations

### For Custom Servers
- **Authentication**: Implement proper API key management
- **Authorization**: Validate user permissions
- **Input Validation**: Sanitize all inputs
- **Rate Limiting**: Prevent abuse
- **Encryption**: Use HTTPS for remote connections

### For Community Servers
- **Code Review**: Check for vulnerabilities
- **Dependency Scanning**: Monitor third-party packages
- **Access Controls**: Limit data exposure
- **Audit Logging**: Track tool usage

## Best Practices

### Server Development
1. **Clear Tool Naming**: Use descriptive, consistent naming conventions
2. **Comprehensive Descriptions**: Document what each tool does and doesn't do
3. **Error Handling**: Provide meaningful error messages
4. **Versioning**: Plan for API evolution
5. **Testing**: Thoroughly test all tools and edge cases

### Client Integration
1. **Tool Discovery**: Dynamically discover available tools
2. **Context Management**: Maintain conversation context
3. **Fallback Handling**: Gracefully handle tool failures
4. **Caching**: Cache results when appropriate
5. **Monitoring**: Track tool usage and performance

## Official MCP Servers

Some notable official MCP servers include:
- **GitHub MCP Server**: Repository management, issues, PRs
- **Slack MCP Server**: Messaging and channel management
- **Atlassian MCP Server**: Jira and Confluence integration
- **Tavily MCP Server**: Web search and content retrieval

### Quick Decision: Which Transport to Use?

| Transport | When to Use | Server Management | Best For |
|-----------|------------|-------------------|----------|
| **stdio** | Local development and testing | Auto-started by client | Custom local tools |
| **Streamable HTTP** | Production, remote servers | Must be running | Public APIs, cloud services |
| **SSE** | Legacy systems | Must be running | Deprecated (avoid new projects) |

### For stdio Transport (Local Development)
1. **No need to manually start the server** - The client handles this
2. Specify the command to run your server in the configuration
3. The client will:
   - Execute the command when `client.session()` is called
   - Manage the process automatically
   - Clean up when the session closes

Example:
```python
client = MultiServerMCPClient({
    "my-server": {
        "transport": "stdio",
        "command": "python",
        "args": ["/path/to/server.py"]
    }
})

async with client.session("my-server") as session:
    # Client automatically starts "/path/to/server.py"
    # Server is running during the async context
    tools = await load_mcp_tools(session)
    # Server is automatically stopped when context exits
```

### For Streamable HTTP Transport (Remote Servers)
1. **The server MUST be running before** the client attempts to connect
2. Verify the server is accessible at the specified URL
3. Handle connection timeouts and network errors gracefully

Example:
```python
client = MultiServerMCPClient({
    "remote-api": {
        "transport": "streamable_http",
        "url": "https://api.example.com/mcp",
        "headers": {"Authorization": "Bearer TOKEN"}
    }
})

# Important: The server at https://api.example.com/mcp must be running!
async with client.session("remote-api") as session:
    tools = await load_mcp_tools(session)
    # Connect to the running server
```

### Getting Started

### Quick Decision: Which Transport to Use?
5. **Test Locally**: Use stdio transport for initial testing
6. **Deploy Securely**: Implement security measures for production

## Resources

- [Official MCP Documentation](https://modelcontextprotocol.io/)
- [MCP GitHub Repository](https://github.com/modelcontextprotocol)
- [Community Servers Directory](https://github.com/modelcontextprotocol/awesome-mcp)
- [SDKs and Tools](https://modelcontextprotocol.io/sdk)

## Conclusion

MCP represents a significant advancement in AI tool integration, providing a standardized, secure way for AI agents to access external capabilities. By following this guide, developers can build powerful MCP servers that extend AI functionality while maintaining security and reliability.

Whether you're building custom tools for specific domains or integrating with existing services, MCP offers a flexible framework for AI-powered automation and intelligence.



