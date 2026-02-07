"""
server.py - Universal MCP Admin Server

A Meta-MCP Server that acts as an "Architect" or "sysadmin" for other 
Model Context Protocol (MCP) servers. It allows inspection, debugging, 
configuration, and extension of other MCP servers.
"""

import os
import platform
import subprocess
from pathlib import Path
from typing import Any, Dict, List

from dotenv import load_dotenv
from fastmcp import FastMCP

import build_cache
import build_detector
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
    code: str,
    auto_compile: bool = False
) -> Dict[str, Any]:
    """
    HOT-PATCHING: Inject a new tool capability into an MCP server (supports multiple languages).
    
    This tool automatically detects the server's language and routes to the appropriate
    injection function. Supports Python, JavaScript, Rust, C, C++, Go, and TypeScript.
    
    It:
    1. Detects the file type and language
    2. Reads the target server's source file
    3. Checks if tool_name already exists
    4. Validates the code syntax
    5. Creates a .bak backup copy
    6. Appends the new tool code to the end of the file
    7. Optionally compiles if auto_compile=True and language requires compilation
    
    This allows the AI to write new abilities for itself or its peers, including
    recursive self-modification (modifying universal-mcp-admin itself).
    
    Args:
        server_name: Name of the server to modify (from config list)
        tool_name: Name of the tool to inject
        code: Code for the tool (language-specific format)
        auto_compile: If True and language requires compilation, automatically compile after injection
        
    Returns:
        Dictionary containing:
        - success: Whether the operation succeeded
        - message: Success or error message
        - needs_compilation: Whether compilation is needed (if not auto-compiled)
        - is_self_modification: Whether this is modifying universal-mcp-admin itself
        
    Safety:
        - Creates backup before modification
        - Validates syntax before injection
        - Checks if tool already exists
        - Respects ALLOWED_ROOT_DIR restriction
        - Warns on self-modification but allows it (enables recursive capabilities)
        
    Example (Python):
        inject_tool_capability(
            "luthier-physics",
            "calculate_volume",
            "@mcp.tool()\\n" +
            "def calculate_volume(length: float, width: float, height: float) -> float:\\n" +
            "    return length * width * height"
        )
    
    Example (Rust):
        inject_tool_capability(
            "my-rust-server",
            "calculate_area",
            "#[mcp::tool(name = \"calculate_area\")]\\n" +
            "pub fn calculate_area(width: f64, height: f64) -> f64 {\\n" +
            "    width * height\\n" +
            "}",
            auto_compile=True
        )
    """
    try:
        # Check for self-modification (recursive capability)
        is_self_modification = server_name == "universal-mcp-admin"
        
        if is_self_modification:
            # Allow but note - this enables recursive self-improvement
            pass
        
        # Use generic injection dispatcher
        success, message = mcp_manager.inject_tool_generic(
            server_name, tool_name, code
        )
        
        if not success:
            return {
                "success": False,
                "message": message,
                "is_self_modification": is_self_modification
            }
        
        # Check if compilation is needed
        source_path = mcp_manager.find_server_source_file(server_name)
        extension = source_path.suffix
        handler = mcp_manager.LANGUAGE_HANDLERS.get(extension, {})
        needs_compilation = handler.get('needs_compilation', False)
        
        result = {
            "success": True,
            "message": message,
            "needs_compilation": needs_compilation and not auto_compile,
            "is_self_modification": is_self_modification
        }
        
        # Auto-compile if requested and needed
        if auto_compile and needs_compilation:
            compile_result = compile_server(server_name, force=False)
            result["compilation"] = compile_result
            if not compile_result.get("success", False):
                result["message"] += f" Warning: Compilation failed: {compile_result.get('message', 'Unknown error')}"
        
        return result
        
    except Exception as e:
        return {
            "success": False,
            "message": f"Failed to inject tool: {str(e)}",
            "is_self_modification": server_name == "universal-mcp-admin"
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
def compile_server(
    server_name: str,
    force: bool = False
) -> Dict[str, Any]:
    """
    Compile a server that requires compilation (Rust, C, C++, Go, TypeScript).
    
    This tool:
    1. Detects the build system (Cargo, Make, CMake, Go, npm/tsc, etc.)
    2. Runs the appropriate build command
    3. Returns compilation status with detailed output
    
    This enables recursive compilation - the admin tool can compile itself or other servers.
    
    Args:
        server_name: Name of server to compile (from config list)
        force: Force recompilation even if already compiled (ignores timestamps)
        
    Returns:
        Dictionary containing:
        - success: Whether compilation succeeded
        - message: Success or error message
        - build_type: Detected build system type
        - command: Build command that was executed
        - output: Build output (stdout)
        - errors: Build errors (stderr)
        - project_path: Path to project that was compiled
        
    Example:
        compile_server("my-rust-server", force=False)
        
    Note:
        - Compilation may take time for large projects
        - Errors are returned but don't prevent the tool from completing
        - Build commands are cached for future use
    """
    try:
        # Find source file to determine project path
        source_path = mcp_manager.find_server_source_file(server_name)
        project_path = build_detector.get_project_path_from_source_file(source_path)
        
        # Detect build system
        build_info = build_detector.detect_build_system(project_path)
        
        if not build_info.get('needs_compilation'):
            return {
                "success": False,
                "message": f"Server '{server_name}' does not require compilation (interpreted language or no build system detected)",
                "build_type": None,
                "project_path": str(project_path)
            }
        
        if build_info.get('type') is None:
            return {
                "success": False,
                "message": f"Could not detect build system for '{server_name}'. No build configuration files found.",
                "build_type": None,
                "project_path": str(project_path)
            }
        
        build_type = build_info['type']
        build_command = build_info['command']
        build_args = build_info['args']
        
        # Check cache for successful build command
        cache = build_cache.get_build_cache()
        cached_command = cache.get_build_command(project_path, build_type)
        
        if cached_command and not force:
            # Use cached command
            command = cached_command
        else:
            # Use detected or suggested command
            suggested = cache.suggest_build_command(project_path, build_type)
            command = suggested or [build_command] + build_args
        
        # Execute build command
        try:
            process = subprocess.run(
                command,
                cwd=project_path,
                capture_output=True,
                text=True,
                timeout=300,  # 5 minute timeout
                check=False
            )
            
            success = process.returncode == 0
            output = process.stdout.strip()
            errors = process.stderr.strip()
            
            # Cache the result
            cache.cache_build_command(
                project_path,
                command,
                success,
                build_type
            )
            
            if not success:
                # Record error for learning
                cache.record_error(
                    project_path,
                    command,
                    errors or output,
                    build_type
                )
            
            return {
                "success": success,
                "message": f"Compilation {'succeeded' if success else 'failed'}",
                "build_type": build_type,
                "command": command,
                "output": output,
                "errors": errors,
                "project_path": str(project_path)
            }
            
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "message": "Compilation timed out after 5 minutes",
                "build_type": build_type,
                "command": command,
                "project_path": str(project_path)
            }
        except FileNotFoundError as e:
            # Provide helpful suggestions based on build type
            suggestions = {
                'cargo': 'Install Rust: https://rustup.rs/',
                'make': 'Install make (usually pre-installed on Unix systems)',
                'cmake': 'Install CMake: https://cmake.org/install/',
                'go': 'Install Go: https://go.dev/dl/',
                'typescript': 'Install Node.js and TypeScript: npm install -g typescript',
                'meson': 'Install Meson: pip install meson',
                'zig': 'Install Zig: https://ziglang.org/download/'
            }
            suggestion = suggestions.get(build_type, f"Install {command[0]}")
            
            return {
                "success": False,
                "message": f"Build command not found: {command[0]}. {suggestion}",
                "build_type": build_type,
                "command": command,
                "project_path": str(project_path),
                "suggestion": suggestion
            }
        except Exception as e:
            # Check error history for patterns
            error_history = cache.get_error_history(project_path)
            common_errors = []
            if error_history:
                # Look for common error patterns
                recent_errors = error_history[-3:]  # Last 3 errors
                common_errors = [e.get('error', '')[:100] for e in recent_errors]
            
            return {
                "success": False,
                "message": f"Compilation failed: {str(e)}",
                "build_type": build_type,
                "command": command,
                "project_path": str(project_path),
                "recent_errors": common_errors if common_errors else None
            }
            
    except Exception as e:
        return {
            "success": False,
            "message": f"Failed to compile server: {str(e)}",
            "build_type": None,
            "project_path": None
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
