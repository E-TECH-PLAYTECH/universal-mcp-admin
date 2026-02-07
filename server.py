"""
server.py - Universal MCP Admin Server

A Meta-MCP Server that acts as an "Architect" or "sysadmin" for other 
Model Context Protocol (MCP) servers. It allows inspection, debugging, 
configuration, and extension of other MCP servers.
"""

import platform
from typing import Any, Dict, List

from dotenv import load_dotenv
from fastmcp import FastMCP

import config_manager
import mcp_manager

# Load environment variables
load_dotenv()

# Initialize FastMCP server
mcp = FastMCP("universal-mcp-admin")


@mcp.tool()
def list_active_servers() -> List[Dict[str, Any]]:
    """
    Read the user's claude_desktop_config.json and return a list of all 
    registered MCP servers, their commands, and working directories.
    
    Returns:
        List of server information dictionaries containing:
        - name: Server name
        - command: Command to run the server
        - args: Command arguments
        - cwd: Working directory (if specified)
        - env: Environment variables (if specified)
        
    Example:
        [
            {
                "name": "luthier-physics",
                "command": "python",
                "args": ["server.py"],
                "cwd": "/path/to/luthier"
            }
        ]
    """
    try:
        servers = config_manager.list_mcp_servers()
        return servers
    except Exception as e:
        raise RuntimeError(f"Failed to list active servers: {str(e)}")


@mcp.tool()
def inspect_mcp_source(server_name: str) -> Dict[str, str]:
    """
    Locate the source code file for an MCP server and return its content.
    This essentially "reads the mind" of another agent.
    
    Args:
        server_name: Name of the server from the config list
        
    Returns:
        Dictionary containing:
        - server_name: Name of the server
        - file_path: Path to the source file
        - content: Source code content (truncated if huge)
        
    Example:
        {
            "server_name": "luthier-physics",
            "file_path": "/path/to/luthier/server.py",
            "content": "import fastmcp\\n..."
        }
    """
    try:
        source_code, file_path = mcp_manager.read_source_file(server_name)
        return {
            "server_name": server_name,
            "file_path": str(file_path),
            "content": source_code
        }
    except Exception as e:
        raise RuntimeError(f"Failed to inspect MCP source: {str(e)}")


@mcp.tool()
def inject_tool_capability(
    server_name: str, 
    tool_name: str, 
    python_code: str
) -> Dict[str, Any]:
    """
    HOT-PATCHING: Inject a new tool capability into a Python MCP server.
    
    This tool:
    1. Reads the target server's Python file
    2. Checks if tool_name already exists
    3. Validates the Python code syntax using AST
    4. Creates a .bak backup copy
    5. Appends the new @mcp.tool() function code to the end of the file
    
    This allows the AI to write new abilities for itself or its peers.
    
    Args:
        server_name: Name of the server to modify (from config list)
        tool_name: Name of the tool to inject
        python_code: Python code for the tool (should include @mcp.tool() decorator)
        
    Returns:
        Dictionary containing:
        - success: Whether the operation succeeded
        - message: Success or error message
        - backup_path: Path to backup file (if created)
        
    Safety:
        - Creates backup before modification
        - Validates syntax with ast.parse()
        - Checks if tool already exists
        - Respects ALLOWED_ROOT_DIR restriction
        
    Example:
        inject_tool_capability(
            "luthier-physics",
            "calculate_volume",
            '''@mcp.tool()
def calculate_volume(length: float, width: float, height: float) -> float:
    """Calculate volume of a rectangular solid."""
    return length * width * height
'''
        )
    """
    try:
        success, message = mcp_manager.inject_tool_into_python_file(
            server_name, tool_name, python_code
        )
        return {
            "success": success,
            "message": message
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"Failed to inject tool: {str(e)}"
        }


@mcp.tool()
def patch_knowledge_file(
    file_path: str,
    search_pattern: str,
    replacement_text: str
) -> Dict[str, Any]:
    """
    Modify data files (JSON/Markdown/etc.) that drive other agents using 
    regex pattern matching and replacement.
    
    Args:
        file_path: Path to the file to modify
        search_pattern: Regex pattern to search for
        replacement_text: Text to replace matches with
        
    Returns:
        Dictionary containing:
        - success: Whether the operation succeeded
        - message: Success or error message
        - backup_path: Path to backup file (if created)
        
    Safety:
        - Creates .bak backup before modification
        - Validates regex pattern before applying
        - Respects ALLOWED_ROOT_DIR restriction
        
    Example:
        Update a wood_database.json:
        patch_knowledge_file(
            "/path/to/wood_database.json",
            '"density": 450',
            '"density": 455'
        )
        
        Update a system_prompt.md:
        patch_knowledge_file(
            "/path/to/system_prompt.md",
            "You are a helpful assistant",
            "You are an expert luthier assistant"
        )
    """
    try:
        success, message = mcp_manager.patch_file_with_regex(
            file_path, search_pattern, replacement_text
        )
        return {
            "success": success,
            "message": message
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"Failed to patch file: {str(e)}"
        }


@mcp.tool()
def restart_claude_instructions() -> Dict[str, str]:
    """
    Returns the exact text instructions for the user on how to restart 
    Claude Desktop to apply changes.
    
    Returns:
        Dictionary containing:
        - platform: Operating system (Darwin/Windows/Linux)
        - instructions: Step-by-step restart instructions
        
    Example:
        {
            "platform": "Darwin",
            "instructions": "To apply changes:\\n1. Quit Claude Desktop...\\n2. Relaunch..."
        }
    """
    system = platform.system()
    
    if system == "Darwin":  # macOS
        instructions = """To apply changes to your MCP servers:

1. Quit Claude Desktop completely:
   - Click 'Claude' in the menu bar
   - Select 'Quit Claude' (or press Cmd+Q)
   
2. Relaunch Claude Desktop from Applications

3. Your changes will be loaded automatically

Note: Simply closing the window is not enough - you must fully quit the application."""

    elif system == "Windows":
        instructions = """To apply changes to your MCP servers:

1. Quit Claude Desktop completely:
   - Right-click the Claude icon in the system tray
   - Select 'Quit' (or press Alt+F4 when focused)
   
2. Relaunch Claude Desktop from the Start Menu

3. Your changes will be loaded automatically

Note: Simply closing the window is not enough - you must fully quit the application."""

    else:  # Linux
        instructions = """To apply changes to your MCP servers:

1. Quit Claude Desktop completely:
   - Close all Claude windows
   - Ensure no Claude processes are running (check with: ps aux | grep -i claude)
   
2. Relaunch Claude Desktop from your application menu or terminal

3. Your changes will be loaded automatically

Note: You may need to kill the process if it doesn't quit cleanly."""

    return {
        "platform": system,
        "instructions": instructions
    }


if __name__ == "__main__":
    # Run the MCP server
    mcp.run()
