# Universal MCP Admin

A Meta-MCP Server that acts as an "Architect" or "sysadmin" for other Model Context Protocol (MCP) servers. It allows an LLM to inspect, debug, configure, and extend other MCP servers running on the same machine.

**44 tools. 7 languages. Any MCP server. Zero domain lock-in.**

## What Is This?

Universal MCP Admin is **content-agnostic**. It doesn't know about guitars, finance, or medicine -- it knows about **Code**, **Config**, and **Processes**. Anyone can clone this repo, point it at their own Claude Desktop config, and immediately manage all of their MCP servers through natural language.

It works with MCP servers written in **Python, JavaScript, TypeScript, Rust, C, C++, and Go**.

## Features at a Glance

| Category | Tools | What It Does |
|----------|-------|-------------|
| **Server Inspection** | 4 | List, inspect, compare, and get info on any MCP server |
| **Configuration Management** | 3 | Add, remove, and update servers in `claude_desktop_config.json` |
| **Hot-Patching** | 3 | Inject, remove, or replace tools in any server's source code |
| **Tool Discovery** | 3 | List all tools, inspect signatures, compare tool sets |
| **Backup & Rollback** | 7 | Backup registry, restore, cleanup, diff, checkpoints |
| **Import Management** | 2 | Detect dependencies, auto-inject missing imports |
| **Multi-file Projects** | 3 | Scan project structure, find files, inject into modules |
| **Testing & Validation** | 2 | Validate code before injection, dry-run simulation |
| **Resource Discovery** | 2 | List MCP resources and prompts defined in source |
| **Compilation** | 1 | Build Rust/C/C++/Go/TypeScript servers with auto-detection |
| **Log Analysis** | 3 | Read logs, analyze errors, search by pattern |
| **Server Lifecycle** | 5 | Check status, enable/disable, get info on all servers |
| **Version Control** | 6 | Git init, commit, status, history, revert, branch |

## Installation

### Prerequisites

- Python 3.10+
- pip or uv package manager

### Setup

```bash
git clone https://github.com/E-TECH-PLAYTECH/universal-mcp-admin.git
cd universal-mcp-admin
pip install -r requirements.txt
```

Optional -- restrict operations to a safe directory:

```bash
cp .env.example .env
# Edit .env to set ALLOWED_ROOT_DIR
```

## Configuration

Add to your `claude_desktop_config.json`:

### macOS / Linux

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

### Using uvx

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

Restart Claude Desktop after adding the config. The admin server will automatically discover all other servers in your config.

## Complete Tools Reference (44 Tools)

### Server Inspection & Info

| Tool | Args | Description |
|------|------|-------------|
| `list_active_servers` | -- | List all MCP servers from `claude_desktop_config.json` |
| `inspect_mcp_source` | `server_name` | Read the full source code of any MCP server |
| `get_server_info` | `server_name` | Get config, status, paths, and environment info |
| `restart_claude_instructions` | -- | Platform-specific restart instructions (macOS/Windows/Linux) |

### Configuration Management

| Tool | Args | Description |
|------|------|-------------|
| `add_server_config` | `server_name, command, args?, cwd?, env?` | Add a new server to the config |
| `remove_server_config` | `server_name` | Remove a server from the config |
| `update_server` | `server_name, updates` | Update an existing server's config fields |

### Hot-Patching (Code Injection)

| Tool | Args | Description |
|------|------|-------------|
| `inject_tool_capability` | `server_name, tool_name, code, auto_compile?` | Inject a new tool into any server (7 languages) |
| `remove_tool` | `server_name, tool_name` | Remove a tool from a server's source code |
| `modify_tool` | `server_name, tool_name, new_code` | Replace an existing tool's implementation |

Supported languages: Python, JavaScript, TypeScript, Rust, C, C++, Go. Each language has dedicated syntax validation (AST for Python, `node --check` for JS, `rustc --check` for Rust, etc.).

### Tool Discovery & Introspection

| Tool | Args | Description |
|------|------|-------------|
| `list_server_tools` | `server_name` | List all tools with names, parameters, and docstrings |
| `inspect_tool` | `server_name, tool_name` | Get detailed signature, types, and documentation |
| `compare_servers` | `server_name1, server_name2` | Diff tool sets between two servers |

### Backup & Rollback

| Tool | Args | Description |
|------|------|-------------|
| `list_backups` | `server_name?, file_path?` | List all tracked backups |
| `restore_backup` | `backup_id, target_path?` | Restore a file from backup (creates safety backup first) |
| `cleanup_backups` | `older_than_days?` | Remove old backup files |
| `diff_backup` | `backup_id` | Show unified diff between backup and current file |
| `create_checkpoint` | `server_name, description` | Snapshot all server files as a named checkpoint |
| `list_checkpoints` | `server_name?` | List available checkpoints |
| `restore_from_checkpoint` | `checkpoint_id` | Restore all files from a checkpoint |

### Import & Dependency Management

| Tool | Args | Description |
|------|------|-------------|
| `check_dependencies` | `server_name` | Detect dependencies from requirements.txt, package.json, Cargo.toml, go.mod |
| `add_imports` | `server_name, imports` | Add import statements to a server's source file |

The `inject_tool_capability` tool also supports `auto_import` mode which automatically detects and injects missing imports during hot-patching.

### Multi-file Project Support

| Tool | Args | Description |
|------|------|-------------|
| `get_project_structure` | `server_name` | Detect language, entry point, modules, build files |
| `list_source_files` | `server_name` | List all source files in the project |
| `inject_into_module` | `server_name, module_path, tool_name, code` | Inject into a specific module file |

### Testing & Validation

| Tool | Args | Description |
|------|------|-------------|
| `validate_tool_code` | `server_name, tool_code` | Validate signature, syntax, and compatibility before injection |
| `dry_run_injection` | `server_name, tool_name, tool_code` | Simulate injection without modifying files |

### Resource & Prompt Discovery

| Tool | Args | Description |
|------|------|-------------|
| `list_server_resources` | `server_name` | List MCP resources and prompts from source code |
| `inspect_resource` | `server_name, resource_uri` | Get details on a specific resource |

### Compilation

| Tool | Args | Description |
|------|------|-------------|
| `compile_server` | `server_name, force?` | Compile a server (auto-detects Cargo, Make, CMake, Go, tsc, Meson, Zig) |

Build commands are cached. Failed builds are recorded for smarter suggestions on retry.

### File Patching

| Tool | Args | Description |
|------|------|-------------|
| `patch_knowledge_file` | `file_path, search_pattern, replacement_text` | Modify any file using regex replacement |

### Log Analysis

| Tool | Args | Description |
|------|------|-------------|
| `get_server_logs` | `server_name?, lines?` | Read recent log output |
| `analyze_errors` | `server_name?` | Detect error patterns (exceptions, panics, segfaults, connection errors) |
| `search_logs` | `server_name?, pattern` | Search logs with regex |

### Server Lifecycle

| Tool | Args | Description |
|------|------|-------------|
| `check_server_status` | `server_name` | Check if a server process is running |
| `list_server_statuses` | -- | Check status of all configured servers |
| `enable_server` | `server_name` | Re-enable a disabled server |
| `disable_server` | `server_name` | Disable a server (config preserved for re-enabling) |

### Version Control (Git)

| Tool | Args | Description |
|------|------|-------------|
| `init_git_repo` | `server_name` | Initialize a git repo with .gitignore |
| `commit_changes` | `server_name, message, files?` | Stage and commit changes |
| `get_git_status` | `server_name` | Get branch, modified/added/deleted files |
| `view_git_history` | `server_name, limit?` | View recent commits |
| `revert_commit` | `server_name, commit_hash` | Revert a specific commit |
| `create_branch` | `server_name, branch_name` | Create and checkout a new branch |

## Safety Features

1. **Automatic Backups** -- Every file modification creates a `.bak` backup, tracked in a central registry with timestamps and metadata.

2. **Syntax Validation** -- Code is validated before injection using language-native tools: Python AST, Node.js `--check`, `rustc --check`, `gcc -fsyntax-only`, `g++ -fsyntax-only`, `go build`, `tsc --noEmit`.

3. **Dry-Run Mode** -- Simulate any injection without touching files. See exactly what would change.

4. **Checkpoint System** -- Snapshot all of a server's files before making changes. Restore with one command.

5. **Directory Restrictions** -- Set `ALLOWED_ROOT_DIR` to prevent modifications outside a safe directory.

6. **Duplicate Detection** -- Tool injection checks if a tool already exists to prevent overwrites.

7. **Self-Modification Awareness** -- The system detects when modifying its own source code and allows it (enabling recursive self-improvement).

## Project Structure

```
universal-mcp-admin/
├── server.py              # Main FastMCP server (44 MCP tools)
├── config_manager.py      # Config CRUD operations
├── mcp_manager.py         # Code manipulation, tool find/remove/replace
├── build_detector.py      # Build system auto-detection
├── build_cache.py         # Build command caching and learning
├── backup_manager.py      # Backup registry, checkpoints, diff
├── import_manager.py      # Import extraction and injection (6 languages)
├── tool_analyzer.py       # Tool discovery and introspection
├── project_scanner.py     # Multi-file project support
├── tool_tester.py         # Validation, dry-run, compatibility
├── resource_discovery.py  # MCP resource and prompt introspection
├── log_manager.py         # Log access and error analysis
├── server_monitor.py      # Server lifecycle and status
├── git_manager.py         # Git operations wrapper
├── requirements.txt       # Python dependencies
├── pyproject.toml         # Project metadata
├── .env.example           # Environment config template
├── EXAMPLES.md            # Usage examples
└── README.md              # This file
```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `ALLOWED_ROOT_DIR` | Restrict file operations to this directory | None (unrestricted) |
| `CLAUDE_CONFIG_PATH` | Custom path to `claude_desktop_config.json` | Platform default |

### Default Config Paths

- **macOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Windows:** `%APPDATA%/Claude/claude_desktop_config.json`
- **Linux:** `~/.config/Claude/claude_desktop_config.json`

## Use Cases

**For anyone with MCP servers:**

- "List all my servers and check which ones are running"
- "Add a new tool to my weather server that converts Celsius to Fahrenheit"
- "Show me what tools my API server has"
- "Remove the deprecated `old_handler` tool from my server"
- "Create a checkpoint before I make changes, so I can roll back"
- "Compare the tools in my dev server vs production server"
- "Check my server's dependencies and add the missing imports"
- "Validate this code before injecting it"
- "Initialize a git repo for my server and commit the current state"
- "Show me the error logs for my server"

**Self-extending AI systems:**

The admin can modify any MCP server, including itself. This enables recursive self-improvement -- an AI agent can request new capabilities, and the admin will write, validate, and inject the code.

## Important Notes

1. **Restart Required** -- Changes to MCP server source code require restarting Claude Desktop.
2. **Logic vs Syntax** -- The system validates syntax but cannot validate logic. Review injected code.
3. **Compiled Languages** -- Rust/C/C++/Go/TypeScript servers need compilation after hot-patching. Use `compile_server` or set `auto_compile=True`.
4. **Backups** -- The system creates `.bak` files and tracks them in a registry. Use checkpoints for multi-file snapshots.

## Contributing

Contributions are welcome. Please open issues or pull requests.

## License

This project is open source and available under the MIT License.

---

**Built with FastMCP**
