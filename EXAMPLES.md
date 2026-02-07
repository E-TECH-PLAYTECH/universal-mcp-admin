# Universal MCP Admin - Usage Examples

Practical examples showing all major capabilities. These examples use generic server names -- replace them with your own.

## Discovery & Inspection

### List all servers

```
"What MCP servers do I have configured?"
```

The admin calls `list_active_servers()` and returns every server in your Claude Desktop config.

### Inspect a server's source code

```
"Show me the source code of my weather-api server"
```

Calls `inspect_mcp_source("weather-api")` -- returns the full source with file path.

### List all tools in a server

```
"What tools does my data-pipeline server have?"
```

Calls `list_server_tools("data-pipeline")` -- returns every tool name, parameters, types, and docstrings.

### Get detailed info on a specific tool

```
"Show me the signature and documentation for the process_batch tool"
```

Calls `inspect_tool("data-pipeline", "process_batch")`.

### Compare two servers

```
"What tools does my dev server have that production doesn't?"
```

Calls `compare_servers("api-dev", "api-prod")` -- returns tools only in dev, only in prod, and shared.

### Check server status

```
"Which of my servers are currently running?"
```

Calls `list_server_statuses()` -- checks the process table for each configured server.

## Configuration Management

### Add a new server

```
"Add my new analytics server to the config"
```

```python
add_server_config(
    server_name="analytics",
    command="python",
    args=["server.py"],
    cwd="/home/user/analytics-mcp"
)
```

### Remove a server

```
"Remove the old-api server from my config"
```

Calls `remove_server_config("old-api")` -- returns the removed config for reference.

### Update a server's config

```
"Change my api-server's working directory to /opt/api"
```

Calls `update_server("api-server", {"cwd": "/opt/api"})`.

### Disable/enable a server

```
"Disable the experimental server for now but keep the config"
```

Calls `disable_server("experimental")` -- moves config to `_disabledServers`. Later, `enable_server("experimental")` brings it back.

## Hot-Patching (Inject, Remove, Replace)

### Inject a new tool (Python)

```
"Add a temperature converter to my weather server"
```

```python
inject_tool_capability(
    server_name="weather-api",
    tool_name="convert_temperature",
    code="""@mcp.tool()
def convert_temperature(value: float, from_unit: str, to_unit: str) -> float:
    '''Convert between Celsius, Fahrenheit, and Kelvin.'''
    # Normalize to Celsius
    if from_unit == 'F':
        celsius = (value - 32) * 5/9
    elif from_unit == 'K':
        celsius = value - 273.15
    else:
        celsius = value
    # Convert to target
    if to_unit == 'F':
        return celsius * 9/5 + 32
    elif to_unit == 'K':
        return celsius + 273.15
    return celsius
"""
)
```

### Inject a tool (JavaScript)

```
"Add a greeting tool to my Node.js server"
```

```python
inject_tool_capability(
    server_name="my-js-server",
    tool_name="greet",
    code="""server.tool("greet", { name: { type: "string" } }, async ({ name }) => {
    return { content: [{ type: "text", text: `Hello, ${name}!` }] };
});"""
)
```

### Inject into a Rust server with auto-compile

```python
inject_tool_capability(
    server_name="my-rust-server",
    tool_name="add_numbers",
    code='pub fn add_numbers(a: i32, b: i32) -> i32 {\n    a + b\n}',
    auto_compile=True
)
```

### Remove a tool

```
"Remove the deprecated old_handler tool from my server"
```

Calls `remove_tool("api-server", "old_handler")` -- finds the function definition (including decorators and comments), removes it, validates syntax, and creates a backup.

### Replace a tool

```
"Replace the calculate_tax tool with this updated version"
```

Calls `modify_tool("finance-server", "calculate_tax", new_code)` -- finds the existing tool, replaces it in-place, and validates syntax.

## Testing & Validation

### Validate code before injection

```
"Check if this code is valid before I inject it"
```

Calls `validate_tool_code("my-server", tool_code)` -- checks signature structure, syntax, decorator presence, type hints, docstring, and compatibility with the target server.

### Dry-run injection

```
"Simulate adding this tool -- don't actually change anything"
```

Calls `dry_run_injection("my-server", "new_tool", tool_code)` -- returns whether the combined code would be valid, what line the tool would land on, and any warnings.

## Backup & Rollback

### List backups

```
"Show me all backups for my api server"
```

Calls `list_backups(server_name="api-server")` -- returns backup IDs, timestamps, operations, and file paths.

### View what changed

```
"Show me the diff for backup abc123"
```

Calls `diff_backup("abc123")` -- returns a unified diff between the backup and current file.

### Restore from backup

```
"Restore the api server from backup abc123"
```

Calls `restore_backup("abc123")` -- creates a safety backup of the current file first, then restores.

### Checkpoints (multi-file snapshots)

```
"Create a checkpoint of my server before I make big changes"
```

```python
create_checkpoint("api-server", "Before refactoring auth module")
```

Later:

```
"Something broke -- restore from the checkpoint"
```

```python
list_checkpoints("api-server")  # Find the checkpoint ID
restore_from_checkpoint("cp-abc123")  # Restores all files
```

## Import & Dependency Management

### Check what dependencies a server uses

```
"What packages does my server depend on?"
```

Calls `check_dependencies("my-server")` -- reads requirements.txt, package.json, Cargo.toml, or go.mod.

### Add imports to a server

```
"Add the json and datetime imports to my server"
```

```python
add_imports("my-server", ["import json", "from datetime import datetime"])
```

## Multi-file Projects

### Scan project structure

```
"Show me the structure of my api server's project"
```

Calls `get_project_structure("api-server")` -- returns language, entry point, source files, modules, and build files.

### List all source files

```
"How many source files does my server have?"
```

Calls `list_source_files("api-server")`.

### Inject into a specific module

```
"Add this utility function to the helpers module"
```

```python
inject_into_module(
    server_name="api-server",
    module_path="/path/to/api/helpers.py",
    tool_name="format_date",
    code="def format_date(dt): return dt.strftime('%Y-%m-%d')"
)
```

## Compilation

### Compile a server

```
"Compile my Rust server"
```

Calls `compile_server("my-rust-server")` -- auto-detects Cargo.toml, runs `cargo build`, caches the command, and returns stdout/stderr.

Supported build systems: Cargo (Rust), Make, CMake, Go, npm/tsc (TypeScript), Meson, Zig.

## Log Analysis

### Read server logs

```
"Show me the last 50 lines of logs"
```

Calls `get_server_logs(lines=50)`.

### Find errors in logs

```
"Are there any errors in my server logs?"
```

Calls `analyze_errors("my-server")` -- scans for exceptions, panics, segfaults, connection errors, and more.

### Search logs

```
"Search the logs for timeout errors"
```

Calls `search_logs(pattern="timeout")`.

## Version Control

### Initialize a repo

```
"Set up git for my server"
```

Calls `init_git_repo("my-server")` -- runs `git init` and creates a `.gitignore`.

### Commit changes

```
"Commit the current state with message 'Add temperature converter'"
```

Calls `commit_changes("my-server", "Add temperature converter")`.

### Check status

```
"Are there uncommitted changes in my server?"
```

Calls `get_git_status("my-server")` -- returns branch, modified/added/deleted/untracked files.

### View history

```
"Show me the last 5 commits"
```

Calls `view_git_history("my-server", limit=5)`.

### Revert a commit

```
"Revert the last commit"
```

Calls `revert_commit("my-server", "abc1234")`.

### Create a branch

```
"Create a feature branch for the new auth system"
```

Calls `create_branch("my-server", "feature/auth-system")`.

## MCP Resource Discovery

### List resources and prompts

```
"What MCP resources does my server expose?"
```

Calls `list_server_resources("my-server")` -- parses source for `@mcp.resource()` decorators and `@mcp.prompt()` definitions.

## Complex Workflows

### Safe tool injection with full validation

1. `validate_tool_code("my-server", code)` -- check syntax and compatibility
2. `dry_run_injection("my-server", "new_tool", code)` -- simulate without changes
3. `create_checkpoint("my-server", "Before adding new_tool")` -- snapshot current state
4. `inject_tool_capability("my-server", "new_tool", code)` -- inject
5. `commit_changes("my-server", "Add new_tool")` -- commit to git

### Audit and compare environments

1. `list_server_tools("api-dev")` -- see dev tools
2. `list_server_tools("api-prod")` -- see prod tools
3. `compare_servers("api-dev", "api-prod")` -- find differences
4. `check_dependencies("api-dev")` -- verify dependencies match

### Diagnose a broken server

1. `check_server_status("my-server")` -- is it running?
2. `get_server_logs("my-server")` -- read recent output
3. `analyze_errors("my-server")` -- categorize errors
4. `list_backups(server_name="my-server")` -- find last good state
5. `restore_backup("backup-id")` -- roll back if needed

---

For the full tools reference, see [README.md](README.md).
