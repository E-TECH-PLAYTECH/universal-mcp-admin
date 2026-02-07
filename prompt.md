I need you to build a powerful Meta-MCP Server called `universal-mcp-admin`.

  The Goal
  This server acts as an "Architect" or "sysadmin" for other Model Context Protocol (MCP) servers. It allows an LLM to
  inspect, debug, configure, and extend other MCP servers running on the same machine.

  It is content-agnostic. It doesn't know about "guitars" or "finance"—it knows about Code, JSON, and Processes.

  Repository Structure
  Initialize a new Python project universal-mcp-admin with:
   * server.py: The FastMCP server.
   * mcp_manager.py: Logic for parsing and modifying other MCPs.
   * config_manager.py: Logic for editing claude_desktop_config.json.

  Core Tools to Implement

  1. Tool: `list_active_servers`
   * Purpose: Read the user's claude_desktop_config.json and return a list of all registered MCP servers, their
     commands, and working directories.

  2. Tool: `inspect_mcp_source`
   * Args: server_name (from the config list).
   * Purpose: Locate the source code file (e.g., server.py or index.js) for that server and return its content
     (truncated if huge). It essentially "reads the mind" of another agent.

  3. Tool: `inject_tool_capability`
   * Args: server_name, tool_name, python_code.
   * Purpose: HOT-PATCHING.
       1. Read the target server's python file.
       2. Check if tool_name already exists.
       3. Append the new @mcp.tool() function code to the end of the file.
       4. (Safety) Verify syntax before saving.
       * Note: This allows the AI to write new abilities for itself or its peers.

  4. Tool: `patch_knowledge_file`
   * Args: file_path, search_pattern (regex), replacement_text.
   * Purpose: Modify the data files (JSON/Markdown) that drive other agents.
       * Example: Update a wood_database.json or a system_prompt.md.

  5. Tool: `restart_claude_instructions`
   * Purpose: Returns the exact text instructions (for the user) on how to restart the host application to apply
     changes.

  Safety Constraints
   1. Backups: Every file modified (inject_tool, patch_knowledge) MUST create a .bak copy first.
   2. Scope: Allow limiting operations to a specific root directory (e.g., ~/projects/) via .env to prevent editing
      system files.
   3. Validation: If inject_tool_capability receives code that fails ast.parse(), reject it. Do not break the target
      server.

  Use Case Example
  User: "My Luthier server needs a tool to calculate volume."
  Admin Agent:
   1. Calls inspect_mcp_source("luthier-physics").
   2. Drafts the Python code for calculate_volume.
   3. Calls inject_tool_capability("luthier-physics", "calculate_volume", code).
   4. Tells user to restart.

  Please generate the full code structure.
