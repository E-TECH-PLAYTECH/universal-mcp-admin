# Universal MCP Admin - Usage Examples

This document provides practical examples of using the Universal MCP Admin to manage and extend other MCP servers.

## Example 1: Listing Active MCP Servers

View all registered MCP servers in your Claude Desktop configuration:

```python
# In Claude, simply ask:
"What MCP servers are currently registered?"

# The universal-mcp-admin will call list_active_servers() and return:
[
    {
        "name": "luthier-physics",
        "command": "python",
        "args": ["server.py"],
        "cwd": "/Users/username/projects/luthier"
    },
    {
        "name": "finance-tracker",
        "command": "node",
        "args": ["dist/index.js"],
        "cwd": "/Users/username/projects/finance"
    }
]
```

## Example 2: Inspecting Server Source Code

Read and understand another server's implementation:

```python
# Ask Claude:
"Show me the source code of the luthier-physics server"

# Result:
{
    "server_name": "luthier-physics",
    "file_path": "/Users/username/projects/luthier/server.py",
    "content": "from fastmcp import FastMCP\n\nmcp = FastMCP('luthier')..."
}
```

## Example 3: Hot-Patching a New Tool

Add a volume calculation tool to an existing server without manual editing:

```python
# Tell Claude:
"Add a volume calculator tool to the luthier-physics server"

# Claude will:
# 1. Draft the tool code
# 2. Call inject_tool_capability with:

inject_tool_capability(
    server_name="luthier-physics",
    tool_name="calculate_wood_volume",
    python_code="""
@mcp.tool()
def calculate_wood_volume(length_cm: float, width_cm: float, height_cm: float) -> dict:
    '''
    Calculate the volume of a wooden piece.
    
    Args:
        length_cm: Length in centimeters
        width_cm: Width in centimeters
        height_cm: Height in centimeters
    
    Returns:
        Dictionary with volume in cubic centimeters and cubic inches
    '''
    volume_cm3 = length_cm * width_cm * height_cm
    volume_in3 = volume_cm3 / 16.387064
    
    return {
        "volume_cm3": volume_cm3,
        "volume_in3": volume_in3,
        "dimensions": {
            "length_cm": length_cm,
            "width_cm": width_cm,
            "height_cm": height_cm
        }
    }
"""
)

# Result:
{
    "success": true,
    "message": "Tool 'calculate_wood_volume' injected successfully. Backup created at /Users/username/projects/luthier/server.py.bak"
}
```

## Example 4: Updating a Knowledge File

Modify a JSON data file that another agent uses:

```python
# Tell Claude:
"Update the density of oak in the wood database to 750 kg/m³"

# Claude will call:
patch_knowledge_file(
    file_path="/Users/username/projects/luthier/wood_database.json",
    search_pattern=r'"oak":\s*{\s*"density":\s*\d+',
    replacement_text='"oak": {"density": 750'
)

# Result:
{
    "success": true,
    "message": "File patched successfully. Backup created at /Users/username/projects/luthier/wood_database.json.bak"
}
```

## Example 5: Complex Multi-Step Operation

A complete workflow demonstrating the power of meta-programming:

**Scenario:** Your finance tracker needs to calculate compound interest, but this feature doesn't exist yet.

**Conversation:**

**User:** "My finance tracker needs a compound interest calculator."

**Claude (using universal-mcp-admin):**

1. **Inspect the server:**
   ```
   inspect_mcp_source("finance-tracker")
   ```

2. **Verify the tool doesn't exist:**
   - Checks source code for existing `calculate_compound_interest` function

3. **Design the tool:**
   - Drafts Python code following the server's patterns
   - Includes proper type hints and documentation

4. **Inject the tool:**
   ```python
   inject_tool_capability(
       server_name="finance-tracker",
       tool_name="calculate_compound_interest",
       python_code="""
   @mcp.tool()
   def calculate_compound_interest(
       principal: float,
       annual_rate: float,
       years: int,
       compounds_per_year: int = 12
   ) -> dict:
       '''
       Calculate compound interest on an investment.
       
       Args:
           principal: Initial investment amount
           annual_rate: Annual interest rate (as decimal, e.g., 0.05 for 5%)
           years: Number of years
           compounds_per_year: Compounding frequency (default: 12 for monthly)
       
       Returns:
           Dictionary with final amount, total interest, and breakdown
       '''
       final_amount = principal * (1 + annual_rate / compounds_per_year) ** (compounds_per_year * years)
       total_interest = final_amount - principal
       
       return {
           "principal": principal,
           "final_amount": round(final_amount, 2),
           "total_interest": round(total_interest, 2),
           "annual_rate": annual_rate,
           "years": years,
           "compounds_per_year": compounds_per_year
       }
   """
   )
   ```

5. **Provide restart instructions:**
   ```
   restart_claude_instructions()
   ```

**Claude:** "I've successfully added a compound interest calculator to your finance tracker! The tool is now available with the following parameters:
- `principal`: Your initial investment
- `annual_rate`: Interest rate as a decimal (e.g., 0.05 for 5%)
- `years`: Investment duration
- `compounds_per_year`: How often interest compounds (default is 12 for monthly)

To use this new feature, please restart Claude Desktop:
1. Quit Claude Desktop (Cmd+Q on Mac)
2. Relaunch the application
3. The new tool will be available immediately

A backup of your original server file has been saved."

## Example 6: Regex Pattern Replacement

Update configuration in a markdown file:

```python
# Update a system prompt
patch_knowledge_file(
    file_path="/path/to/agent/system_prompt.md",
    search_pattern=r"Temperature: \d+\.\d+",
    replacement_text="Temperature: 0.7"
)

# Update multiple values in a JSON config
patch_knowledge_file(
    file_path="/path/to/config.json",
    search_pattern=r'"max_tokens":\s*\d+',
    replacement_text='"max_tokens": 4096'
)
```

## Safety Features in Action

### Automatic Backups

Every modification creates a `.bak` file:
```
Before: server.py
After:  server.py (modified) + server.py.bak (original)
```

### Syntax Validation

Invalid Python code is rejected:
```python
# This will be rejected:
inject_tool_capability(
    "server",
    "broken_tool",
    "def broken syntax here"
)

# Result:
{
    "success": false,
    "message": "Invalid Python code: Syntax error at line 1: invalid syntax"
}
```

### Duplicate Detection

Prevents injecting tools that already exist:
```python
# If calculate_volume already exists:
inject_tool_capability("server", "calculate_volume", code)

# Result:
{
    "success": false,
    "message": "Tool 'calculate_volume' already exists in /path/to/server.py"
}
```

### Directory Restrictions

Set `ALLOWED_ROOT_DIR` in `.env` to limit operations:
```bash
ALLOWED_ROOT_DIR=/Users/username/projects
```

Any attempt to modify files outside this directory will fail:
```python
patch_knowledge_file("/etc/passwd", "pattern", "replacement")

# Result:
{
    "success": false,
    "message": "Failed to patch file: Path '/etc/passwd' is outside allowed root directory '/Users/username/projects'"
}
```

## Tips for Best Results

1. **Be Specific:** When asking Claude to add functionality, describe what you want in detail.
   
2. **Verify First:** Ask Claude to inspect the server before making changes to understand its structure.

3. **Test in Development:** Use a copy of your production server when testing new capabilities.

4. **Keep Backups:** The system creates `.bak` files, but maintain your own backups for important servers.

5. **Restart After Changes:** Always restart Claude Desktop after modifying server code.

6. **Use Version Control:** Keep your MCP servers in git repositories to track changes.

## Advanced Use Case: Self-Improving Systems

The universal-mcp-admin enables AI agents to improve themselves and each other:

**Scenario:** An agent discovers it needs a capability it doesn't have.

```
Agent: "I need to calculate prime numbers but I don't have that tool."

universal-mcp-admin:
1. Inspects the agent's source code
2. Verifies the tool doesn't exist
3. Writes the tool based on best practices
4. Injects the tool into the agent
5. Instructs user to restart

Result: The agent now has the capability it needed, without human intervention.
```

This creates a **self-extending ecosystem** where:
- Agents can request new capabilities
- The admin agent provides those capabilities
- Each agent becomes more powerful over time
- The entire system evolves based on actual usage patterns

## Troubleshooting

### Tool Not Showing After Injection

**Problem:** Injected a tool but it's not available.

**Solution:** Restart Claude Desktop completely (not just closing the window).

### Syntax Error in Injected Code

**Problem:** The injected code has a syntax error.

**Solution:** The system validates syntax before injection. If this happens, check:
- The full file syntax (might be incompatible with the target server)
- Use `inspect_mcp_source` to understand the server's patterns

### Cannot Find Server Source File

**Problem:** `inspect_mcp_source` fails to find the file.

**Solution:** 
- Verify the server is properly configured in `claude_desktop_config.json`
- Check that the `cwd` (working directory) is correctly set
- Ensure the command and args point to a valid Python or JavaScript file

### Regex Pattern Not Matching

**Problem:** `patch_knowledge_file` reports pattern not found.

**Solution:**
- Test your regex pattern first
- Use a regex tester website
- Check for whitespace or formatting differences
- Use `inspect_mcp_source` to see the exact file content

---

For more information, see the [README.md](README.md) file.
