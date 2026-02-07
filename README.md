# Universal MCP Admin

A Meta-MCP Server that acts as an "Architect" or "sysadmin" for other Model Context Protocol (MCP) servers. It allows an LLM to inspect, debug, configure, and extend other MCP servers running on the same machine.

## 🎯 Features

Universal MCP Admin is **content-agnostic**. It doesn't know about "guitars" or "finance"—it knows about **Code**, **JSON**, and **Processes**.

### Core Capabilities

1. **📋 List Active Servers** - Read and list all registered MCP servers from `claude_desktop_config.json`
2. **🔍 Inspect Source Code** - Read the source code of any MCP server to understand its implementation
3. **💉 Hot-Patch Tools** - Inject new tool capabilities into existing MCP servers without manual editing
4. **📝 Patch Knowledge Files** - Modify data files (JSON, Markdown, etc.) that drive other agents
5. **🔄 Restart Instructions** - Get platform-specific instructions for restarting Claude Desktop

## 🚀 Installation

### Prerequisites

- Python 3.10 or higher
- pip or uv package manager

### Setup

1. Clone or download this repository:
```bash
git clone https://github.com/E-TECH-PLAYTECH/universal-mcp-admin.git
cd universal-mcp-admin
```

2. Install dependencies:
```bash
pip install -r requirements.txt
# or
uv pip install -r requirements.txt
```

3. (Optional) Configure environment variables:
```bash
cp .env.example .env
# Edit .env to set ALLOWED_ROOT_DIR for safety
```

## 📦 Configuration

Add to your `claude_desktop_config.json`:

### macOS/Linux
```json
{
  "mcpServers": {
    "universal-mcp-admin": {
      "command": "python",
      "args": ["/absolute/path/to/universal-mcp-admin/server.py"],
      "cwd": "/absolute/path/to/universal-mcp-admin"
    }
  }
}
```

### Windows
```json
{
  "mcpServers": {
    "universal-mcp-admin": {
      "command": "python",
      "args": ["C:\\path\\to\\universal-mcp-admin\\server.py"],
      "cwd": "C:\\path\\to\\universal-mcp-admin"
    }
  }
}
```

### Using uvx (alternative)
```json
{
  "mcpServers": {
    "universal-mcp-admin": {
      "command": "uvx",
      "args": ["--from", "/path/to/universal-mcp-admin", "fastmcp", "run", "server.py"]
    }
  }
}
```

## 🛠️ Tools Reference

### 1. `list_active_servers`

Lists all registered MCP servers from Claude Desktop configuration.

**Returns:**
```json
[
  {
    "name": "luthier-physics",
    "command": "python",
    "args": ["server.py"],
    "cwd": "/path/to/luthier"
  }
]
```

### 2. `inspect_mcp_source`

Reads the source code of an MCP server.

**Arguments:**
- `server_name` (string): Name of the server from the config

**Returns:**
```json
{
  "server_name": "luthier-physics",
  "file_path": "/path/to/luthier/server.py",
  "content": "import fastmcp\n..."
}
```

### 3. `inject_tool_capability`

Hot-patches a new tool into an existing MCP server.

**Arguments:**
- `server_name` (string): Server to modify
- `tool_name` (string): Name of the new tool
- `python_code` (string): Complete Python code including decorator

**Example:**
```python
inject_tool_capability(
    "luthier-physics",
    "calculate_volume",
    """@mcp.tool()
def calculate_volume(length: float, width: float, height: float) -> float:
    '''Calculate volume of a rectangular solid.'''
    return length * width * height
"""
)
```

**Returns:**
```json
{
  "success": true,
  "message": "Tool 'calculate_volume' injected successfully. Backup created at ..."
}
```

### 4. `patch_knowledge_file`

Modifies data files using regex pattern replacement.

**Arguments:**
- `file_path` (string): Path to file to modify
- `search_pattern` (string): Regex pattern to find
- `replacement_text` (string): Text to replace with

**Example:**
```python
patch_knowledge_file(
    "/path/to/wood_database.json",
    '"density": 450',
    '"density": 455'
)
```

### 5. `restart_claude_instructions`

Provides platform-specific instructions for restarting Claude Desktop.

**Returns:**
```json
{
  "platform": "Darwin",
  "instructions": "To apply changes:\n1. Quit Claude Desktop...\n2. Relaunch..."
}
```

## 🔒 Safety Features

### 1. Automatic Backups
Every file modification creates a `.bak` backup file automatically.

### 2. Syntax Validation
Python code injection validates syntax using `ast.parse()` before applying changes.

### 3. Directory Restrictions
Set `ALLOWED_ROOT_DIR` in `.env` to limit operations to a specific directory:
```bash
ALLOWED_ROOT_DIR=/home/user/projects
```

### 4. Duplicate Detection
The system checks if a tool already exists before injection to prevent duplicates.

## 📚 Use Case Example

**Scenario:** Your Luthier server needs a tool to calculate wood volume.

**Conversation with Claude:**

> **User:** "My Luthier server needs a tool to calculate volume."

**Admin Agent Actions:**
1. Calls `inspect_mcp_source("luthier-physics")` to understand the server
2. Drafts the Python code for `calculate_volume` function
3. Calls `inject_tool_capability("luthier-physics", "calculate_volume", code)`
4. Calls `restart_claude_instructions()` to tell user how to restart
5. Reports success and provides restart instructions

**Result:** New tool is added without manual file editing!

## 🏗️ Project Structure

```
universal-mcp-admin/
├── server.py              # Main FastMCP server with 5 tools
├── config_manager.py      # Claude Desktop config operations
├── mcp_manager.py         # MCP server inspection and modification
├── requirements.txt       # Python dependencies
├── pyproject.toml         # Project metadata
├── .env.example           # Environment configuration template
├── .gitignore            # Git ignore rules
└── README.md             # This file
```

## 🔧 Development

### Running Tests
```bash
pytest
```

### Code Formatting
```bash
black .
```

### Type Checking
```bash
mypy *.py
```

## 📝 Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `ALLOWED_ROOT_DIR` | Root directory to limit operations (for safety) | None (unrestricted) |
| `CLAUDE_CONFIG_PATH` | Custom path to claude_desktop_config.json | Platform default |

### Default Config Paths

- **macOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Windows:** `%APPDATA%/Claude/claude_desktop_config.json`
- **Linux:** `~/.config/Claude/claude_desktop_config.json`

## ⚠️ Important Notes

1. **Backup Files:** Always keep backups. The system creates `.bak` files, but manual backups are recommended for important servers.

2. **Testing:** Test injected tools in a development environment before production use.

3. **Syntax Errors:** While the system validates syntax, it cannot validate logic. Review injected code carefully.

4. **Restart Required:** Changes to MCP servers require restarting Claude Desktop to take effect.

5. **Python Only:** Hot-patching currently only supports Python MCP servers. JavaScript/Node.js servers can be inspected but not hot-patched.

## 🤝 Contributing

Contributions are welcome! Please feel free to submit issues or pull requests.

## 📄 License

This project is open source and available under the MIT License.

## 🙋 Support

For issues, questions, or suggestions, please open an issue on the GitHub repository.

---

**Built with ❤️ using FastMCP**
