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
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
from fastmcp import FastMCP

import backup_manager
import build_cache
import build_detector
import config_manager
import git_manager
import import_manager
import log_manager
import mcp_manager
import project_scanner
import resource_discovery
import server_monitor
import tool_analyzer
import tool_tester

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
    injection function. Supports Python, JavaScript, Rust, C, C++, Go, TypeScript, Zig, Java, Ruby, Kotlin, Swift, C#, PHP, Lua, Scala, Elixir, Dart, Haskell, OCaml, Nim, D, Crystal, Raku, and Julia.
    
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
    Compile a server that requires compilation (Rust, C, C++, Go, TypeScript, Zig, Java, Kotlin, Swift, C#, Scala, Elixir, Dart, Haskell, OCaml, Nim, D, Crystal).
    
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
                'zig': 'Install Zig: https://ziglang.org/download/',
                'maven': 'Install Maven: https://maven.apache.org/install.html',
                'gradle': 'Install Gradle: https://gradle.org/install/',
                'swift': 'Install Swift: https://swift.org/download/',
                'dotnet': 'Install .NET SDK: https://dotnet.microsoft.com/download',
                'composer': 'Install Composer: https://getcomposer.org/download/',
                'luarocks': 'Install LuaRocks: https://luarocks.org/',
                'sbt': 'Install sbt: https://www.scala-sbt.org/download.html',
                'mix': 'Install Elixir: https://elixir-lang.org/install.html',
                'dart': 'Install Dart SDK: https://dart.dev/get-dart',
                'cabal': 'Install GHC/Cabal: https://www.haskell.org/ghcup/',
                'stack': 'Install Stack: https://docs.haskellstack.org/en/stable/install_and_upgrade/',
                'dune': 'Install OCaml/Dune: https://ocaml.org/install',
                'nimble': 'Install Nim: https://nim-lang.org/install.html',
                'dub': 'Install D compiler: https://dlang.org/download.html',
                'crystal': 'Install Crystal: https://crystal-lang.org/install/',
                'raku': 'Install Raku: https://rakudo.org/star',
                'julia': 'Install Julia: https://julialang.org/downloads/',
                'bundler': 'Install Bundler: gem install bundler',
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
                common_errors = [err.get('error', '')[:100] for err in recent_errors]
            
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


# ============================================================================
# Feature 1: Configuration Management
# ============================================================================


@mcp.tool()
def add_server_config(
    server_name: str,
    command: str,
    args: Optional[List[str]] = None,
    cwd: Optional[str] = None,
    env: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    """
    Add a new MCP server to the Claude Desktop configuration.

    Args:
        server_name: Unique name for the server
        command: Command to run the server (e.g. "python", "node")
        args: Command arguments (e.g. ["server.py"])
        cwd: Working directory for the server
        env: Environment variables for the server

    Returns:
        Dictionary with success status and message
    """
    try:
        config_manager.add_server_config(server_name, command, args, cwd, env)
        return {"success": True, "message": f"Server '{server_name}' added to config"}
    except Exception as e:
        return {"success": False, "message": str(e)}


@mcp.tool()
def remove_server_config(server_name: str) -> Dict[str, Any]:
    """
    Remove an MCP server from the Claude Desktop configuration.

    Args:
        server_name: Name of the server to remove

    Returns:
        Dictionary with success status and the removed config
    """
    try:
        removed = config_manager.remove_server_config(server_name)
        return {"success": True, "message": f"Server '{server_name}' removed", "config": removed}
    except Exception as e:
        return {"success": False, "message": str(e)}


@mcp.tool()
def update_server(
    server_name: str,
    updates: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Update an existing MCP server's configuration.

    Args:
        server_name: Name of the server to update
        updates: Dictionary of fields to update (command, args, cwd, env)

    Returns:
        Dictionary with success status
    """
    try:
        config_manager.update_server_config(server_name, updates)
        return {"success": True, "message": f"Server '{server_name}' config updated"}
    except Exception as e:
        return {"success": False, "message": str(e)}


# ============================================================================
# Feature 2: Tool Removal and Modification
# ============================================================================


@mcp.tool()
def remove_tool(server_name: str, tool_name: str) -> Dict[str, Any]:
    """
    Remove a tool from an MCP server's source code.

    Args:
        server_name: Name of the server to modify
        tool_name: Name of the tool to remove

    Returns:
        Dictionary with success status and message
    """
    try:
        success, message = mcp_manager.remove_tool(server_name, tool_name)
        return {"success": success, "message": message}
    except Exception as e:
        return {"success": False, "message": str(e)}


@mcp.tool()
def modify_tool(
    server_name: str,
    tool_name: str,
    new_code: str,
) -> Dict[str, Any]:
    """
    Replace an existing tool's code in an MCP server.

    Args:
        server_name: Name of the server to modify
        tool_name: Name of the tool to replace
        new_code: Complete new code for the tool

    Returns:
        Dictionary with success status and message
    """
    try:
        success, message = mcp_manager.replace_tool(server_name, tool_name, new_code)
        return {"success": success, "message": message}
    except Exception as e:
        return {"success": False, "message": str(e)}


# ============================================================================
# Feature 3: Rollback / Backup Management
# ============================================================================


@mcp.tool()
def list_backups(
    server_name: Optional[str] = None,
    file_path: Optional[str] = None,
) -> Dict[str, Any]:
    """
    List available backups, optionally filtered by server or file.

    Args:
        server_name: Filter by server name
        file_path: Filter by original file path

    Returns:
        Dictionary with list of backups
    """
    try:
        bm = backup_manager.get_backup_manager()
        backups = bm.list_backups(file_path=file_path, server_name=server_name)
        return {"success": True, "backups": backups, "count": len(backups)}
    except Exception as e:
        return {"success": False, "message": str(e)}


@mcp.tool()
def restore_backup(
    backup_id: str,
    target_path: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Restore a file from a backup.

    Args:
        backup_id: ID of the backup to restore
        target_path: Optional override path to restore to

    Returns:
        Dictionary with success status
    """
    try:
        bm = backup_manager.get_backup_manager()
        success, message = bm.restore_backup(backup_id, target_path)
        return {"success": success, "message": message}
    except Exception as e:
        return {"success": False, "message": str(e)}


@mcp.tool()
def cleanup_backups(older_than_days: int = 30) -> Dict[str, Any]:
    """
    Clean up old backup files.

    Args:
        older_than_days: Remove backups older than this many days

    Returns:
        Dictionary with cleanup results
    """
    try:
        bm = backup_manager.get_backup_manager()
        removed, kept = bm.cleanup_backups(older_than_days=older_than_days)
        return {"success": True, "removed": removed, "kept": kept}
    except Exception as e:
        return {"success": False, "message": str(e)}


# ============================================================================
# Feature 4: Import Management
# ============================================================================


@mcp.tool()
def check_dependencies(server_name: str) -> Dict[str, Any]:
    """
    Check external dependencies for a server's project.

    Args:
        server_name: Name of the server

    Returns:
        Dictionary with dependency information
    """
    try:
        source_path = mcp_manager.find_server_source_file(server_name)
        project_path = str(source_path.parent)
        extension = source_path.suffix
        deps = import_manager.detect_dependencies(project_path, extension)
        return {"success": True, "dependencies": deps, "count": len(deps)}
    except Exception as e:
        return {"success": False, "message": str(e)}


@mcp.tool()
def add_imports(
    server_name: str,
    imports: List[str],
) -> Dict[str, Any]:
    """
    Add import statements to a server's source file.

    Args:
        server_name: Name of the server
        imports: List of import statements to add

    Returns:
        Dictionary with success status
    """
    try:
        source_code, source_path = mcp_manager.read_source_file(server_name, max_chars=200000)
        extension = source_path.suffix
        missing = []
        existing = import_manager.extract_imports(source_code, extension)
        existing_set = set(existing)
        for imp in imports:
            if imp not in existing_set:
                missing.append(imp)

        if not missing:
            return {"success": True, "message": "All imports already present", "added": []}

        backup_path = mcp_manager.create_backup(source_path)
        new_source = import_manager.inject_imports(source_code, missing, extension)
        with open(source_path, 'w', encoding='utf-8') as f:
            f.write(new_source)
        return {"success": True, "message": f"Added {len(missing)} imports", "added": missing, "backup": str(backup_path)}
    except Exception as e:
        return {"success": False, "message": str(e)}


# ============================================================================
# Feature 5: Tool Discovery
# ============================================================================


@mcp.tool()
def list_server_tools(server_name: str) -> Dict[str, Any]:
    """
    List all tools/functions defined in a server's source code.

    Args:
        server_name: Name of the server

    Returns:
        Dictionary with list of tools and their metadata
    """
    try:
        source_code, source_path = mcp_manager.read_source_file(server_name, max_chars=200000)
        extension = source_path.suffix
        tools = tool_analyzer.list_tools_in_source(source_code, extension)
        return {
            "success": True,
            "server_name": server_name,
            "tools": tools,
            "count": len(tools),
            "language": extension,
        }
    except Exception as e:
        return {"success": False, "message": str(e)}


@mcp.tool()
def inspect_tool(server_name: str, tool_name: str) -> Dict[str, Any]:
    """
    Get detailed information about a specific tool in a server.

    Args:
        server_name: Name of the server
        tool_name: Name of the tool to inspect

    Returns:
        Dictionary with tool signature, parameters, docstring, etc.
    """
    try:
        source_code, source_path = mcp_manager.read_source_file(server_name, max_chars=200000)
        extension = source_path.suffix
        sig = tool_analyzer.get_tool_signature(tool_name, source_code, extension)
        if sig is None:
            return {"success": False, "message": f"Tool '{tool_name}' not found in {server_name}"}
        return {"success": True, "tool": sig}
    except Exception as e:
        return {"success": False, "message": str(e)}


@mcp.tool()
def compare_servers(server_name1: str, server_name2: str) -> Dict[str, Any]:
    """
    Compare tool sets between two MCP servers.

    Args:
        server_name1: First server name
        server_name2: Second server name

    Returns:
        Dictionary with comparison results
    """
    try:
        src1, path1 = mcp_manager.read_source_file(server_name1, max_chars=200000)
        src2, path2 = mcp_manager.read_source_file(server_name2, max_chars=200000)
        ext1 = path1.suffix
        ext2 = path2.suffix
        if ext1 != ext2:
            return {"success": False, "message": f"Language mismatch: {ext1} vs {ext2}"}
        result = tool_analyzer.compare_tools(src1, src2, ext1)
        result["success"] = True
        return result
    except Exception as e:
        return {"success": False, "message": str(e)}


# ============================================================================
# Feature 6: Multi-file Support
# ============================================================================


@mcp.tool()
def get_project_structure(server_name: str) -> Dict[str, Any]:
    """
    Detect and return the project structure for an MCP server.

    Args:
        server_name: Name of the server

    Returns:
        Dictionary with project structure information
    """
    try:
        config = config_manager.get_server_config(server_name)
        cwd = config.get("cwd", "")
        if not cwd:
            source_path = mcp_manager.find_server_source_file(server_name)
            cwd = str(source_path.parent)
        structure = project_scanner.detect_project_structure(cwd)
        structure["success"] = True
        return structure
    except Exception as e:
        return {"success": False, "message": str(e)}


@mcp.tool()
def list_source_files(server_name: str) -> Dict[str, Any]:
    """
    List all source files for an MCP server's project.

    Args:
        server_name: Name of the server

    Returns:
        Dictionary with list of source files
    """
    try:
        files = project_scanner.find_all_source_files(server_name)
        return {"success": True, "files": files, "count": len(files)}
    except Exception as e:
        return {"success": False, "message": str(e)}


@mcp.tool()
def inject_into_module(
    server_name: str,
    module_path: str,
    tool_name: str,
    code: str,
) -> Dict[str, Any]:
    """
    Inject a tool into a specific module file of a multi-file project.

    Args:
        server_name: Name of the server
        module_path: Path to the module file
        tool_name: Name of the tool
        code: Tool code to inject

    Returns:
        Dictionary with success status
    """
    try:
        source_path = mcp_manager.find_server_source_file(server_name)
        extension = source_path.suffix
        success, message = project_scanner.inject_into_module(
            module_path, tool_name, code, extension
        )
        return {"success": success, "message": message}
    except Exception as e:
        return {"success": False, "message": str(e)}


# ============================================================================
# Feature 7: Testing and Validation
# ============================================================================


@mcp.tool()
def validate_tool_code(
    server_name: str,
    tool_code: str,
) -> Dict[str, Any]:
    """
    Validate tool code before injection (signature, syntax, compatibility).

    Args:
        server_name: Target server name (used to determine language)
        tool_code: The tool code to validate

    Returns:
        Dictionary with validation results
    """
    try:
        source_path = mcp_manager.find_server_source_file(server_name)
        extension = source_path.suffix
        sig_result = tool_tester.validate_tool_signature(tool_code, extension)

        source_code, _ = mcp_manager.read_source_file(server_name, max_chars=200000)
        compat = tool_tester.check_tool_compatibility(source_code, tool_code, extension)

        return {
            "success": True,
            "signature": sig_result,
            "compatibility": compat,
        }
    except Exception as e:
        return {"success": False, "message": str(e)}


@mcp.tool()
def dry_run_injection(
    server_name: str,
    tool_name: str,
    tool_code: str,
) -> Dict[str, Any]:
    """
    Simulate tool injection without actually modifying the server.
    Returns a preview and validation results.

    Args:
        server_name: Target server name
        tool_name: Name of the tool
        tool_code: Code to test injecting

    Returns:
        Dictionary with dry-run results
    """
    try:
        source_code, source_path = mcp_manager.read_source_file(server_name, max_chars=200000)
        extension = source_path.suffix
        result = tool_tester.dry_run_injection(
            source_code, tool_name, tool_code, extension
        )
        result["success"] = True
        return result
    except Exception as e:
        return {"success": False, "message": str(e)}


# ============================================================================
# Feature 8: Enhanced Backup / Checkpoints
# ============================================================================


@mcp.tool()
def create_checkpoint(
    server_name: str,
    description: str,
) -> Dict[str, Any]:
    """
    Create a named checkpoint (snapshot of all server source files).

    Args:
        server_name: Name of the server
        description: Human-readable description of the checkpoint

    Returns:
        Dictionary with checkpoint ID
    """
    try:
        files = project_scanner.find_all_source_files(server_name)
        if not files:
            source_path = mcp_manager.find_server_source_file(server_name)
            files = [str(source_path)]
        bm = backup_manager.get_backup_manager()
        cp_id = bm.create_checkpoint(server_name, description, files)
        return {"success": True, "checkpoint_id": cp_id, "files_saved": len(files)}
    except Exception as e:
        return {"success": False, "message": str(e)}


@mcp.tool()
def list_checkpoints(
    server_name: Optional[str] = None,
) -> Dict[str, Any]:
    """
    List available checkpoints.

    Args:
        server_name: Optional filter by server name

    Returns:
        Dictionary with list of checkpoints
    """
    try:
        bm = backup_manager.get_backup_manager()
        cps = bm.list_checkpoints(server_name)
        return {"success": True, "checkpoints": cps, "count": len(cps)}
    except Exception as e:
        return {"success": False, "message": str(e)}


@mcp.tool()
def restore_from_checkpoint(checkpoint_id: str) -> Dict[str, Any]:
    """
    Restore all files from a checkpoint.

    Args:
        checkpoint_id: ID of the checkpoint to restore

    Returns:
        Dictionary with success status
    """
    try:
        bm = backup_manager.get_backup_manager()
        success, message = bm.restore_checkpoint(checkpoint_id)
        return {"success": success, "message": message}
    except Exception as e:
        return {"success": False, "message": str(e)}


@mcp.tool()
def diff_backup(backup_id: str) -> Dict[str, Any]:
    """
    Show differences between a backup and the current file.

    Args:
        backup_id: ID of the backup

    Returns:
        Dictionary with diff content
    """
    try:
        bm = backup_manager.get_backup_manager()
        success, diff = bm.diff_backup(backup_id)
        return {"success": success, "diff": diff}
    except Exception as e:
        return {"success": False, "message": str(e)}


# ============================================================================
# Feature 9: Resource Discovery
# ============================================================================


@mcp.tool()
def list_server_resources(server_name: str) -> Dict[str, Any]:
    """
    List MCP resources defined in a server's source code.

    Args:
        server_name: Name of the server

    Returns:
        Dictionary with list of resources
    """
    try:
        source_code, source_path = mcp_manager.read_source_file(server_name, max_chars=200000)
        extension = source_path.suffix
        resources = resource_discovery.list_mcp_resources(source_code, extension)
        prompts = resource_discovery.list_mcp_prompts(source_code, extension)
        return {
            "success": True,
            "resources": resources,
            "prompts": prompts,
            "resource_count": len(resources),
            "prompt_count": len(prompts),
        }
    except Exception as e:
        return {"success": False, "message": str(e)}


@mcp.tool()
def inspect_resource(
    server_name: str,
    resource_uri: str,
) -> Dict[str, Any]:
    """
    Inspect a specific MCP resource in a server.

    Args:
        server_name: Name of the server
        resource_uri: URI of the resource to inspect

    Returns:
        Dictionary with resource details
    """
    try:
        source_code, source_path = mcp_manager.read_source_file(server_name, max_chars=200000)
        extension = source_path.suffix
        info = resource_discovery.inspect_resource(source_code, resource_uri, extension)
        if info is None:
            return {"success": False, "message": f"Resource '{resource_uri}' not found in {server_name}"}
        return {"success": True, "resource": info}
    except Exception as e:
        return {"success": False, "message": str(e)}


# ============================================================================
# Feature 10: Log Analysis
# ============================================================================


@mcp.tool()
def get_server_logs(
    server_name: Optional[str] = None,
    lines: int = 100,
) -> Dict[str, Any]:
    """
    Get recent server logs.

    Args:
        server_name: Optional filter by server name
        lines: Number of log lines to retrieve

    Returns:
        Dictionary with log content
    """
    return log_manager.get_server_logs(server_name, lines)


@mcp.tool()
def analyze_errors(
    server_name: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Analyze server logs for errors and patterns.

    Args:
        server_name: Optional filter by server name

    Returns:
        Dictionary with error analysis
    """
    return log_manager.analyze_logs(server_name)


@mcp.tool()
def search_logs(
    server_name: Optional[str] = None,
    pattern: str = "",
) -> Dict[str, Any]:
    """
    Search server logs for a specific pattern.

    Args:
        server_name: Optional filter by server name
        pattern: Regex pattern to search for

    Returns:
        Dictionary with matching log lines
    """
    return log_manager.search_logs(server_name, pattern)


# ============================================================================
# Feature 11: Server Lifecycle Management
# ============================================================================


@mcp.tool()
def check_server_status(server_name: str) -> Dict[str, Any]:
    """
    Check if a specific MCP server is currently running.

    Args:
        server_name: Name of the server to check

    Returns:
        Dictionary with status information
    """
    return server_monitor.check_server_status(server_name)


@mcp.tool()
def list_server_statuses() -> List[Dict[str, Any]]:
    """
    Check status of all configured MCP servers.

    Returns:
        List of status dictionaries for each server
    """
    return server_monitor.list_server_statuses()


@mcp.tool()
def enable_server(server_name: str) -> Dict[str, Any]:
    """
    Enable a disabled MCP server in the configuration.

    Args:
        server_name: Name of the server to enable

    Returns:
        Dictionary with success status
    """
    return server_monitor.enable_server(server_name)


@mcp.tool()
def disable_server(server_name: str) -> Dict[str, Any]:
    """
    Disable an MCP server (preserves config for re-enabling).

    Args:
        server_name: Name of the server to disable

    Returns:
        Dictionary with success status
    """
    return server_monitor.disable_server(server_name)


@mcp.tool()
def get_server_info(server_name: str) -> Dict[str, Any]:
    """
    Get comprehensive information about a server (config, status, paths).

    Args:
        server_name: Name of the server

    Returns:
        Dictionary with detailed server information
    """
    return server_monitor.get_server_info(server_name)


# ============================================================================
# Feature 12: Version Control Integration
# ============================================================================


@mcp.tool()
def init_git_repo(server_name: str) -> Dict[str, Any]:
    """
    Initialize a git repository for a server's project.

    Args:
        server_name: Name of the server

    Returns:
        Dictionary with success status
    """
    return git_manager.init_repo(server_name)


@mcp.tool()
def commit_changes(
    server_name: str,
    message: str,
    files: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Stage and commit changes in a server's project.

    Args:
        server_name: Name of the server
        message: Commit message
        files: Optional list of specific files to commit (None = all)

    Returns:
        Dictionary with commit hash and status
    """
    return git_manager.commit_changes(server_name, message, files)


@mcp.tool()
def get_git_status(server_name: str) -> Dict[str, Any]:
    """
    Get git status for a server's project.

    Args:
        server_name: Name of the server

    Returns:
        Dictionary with git status information
    """
    return git_manager.get_git_status(server_name)


@mcp.tool()
def view_git_history(
    server_name: str,
    limit: int = 10,
) -> Dict[str, Any]:
    """
    View recent commit history for a server's project.

    Args:
        server_name: Name of the server
        limit: Maximum number of commits to return

    Returns:
        Dictionary with commit history
    """
    return git_manager.view_git_history(server_name, limit)


@mcp.tool()
def revert_commit(
    server_name: str,
    commit_hash: str,
) -> Dict[str, Any]:
    """
    Revert a specific commit in a server's project.

    Args:
        server_name: Name of the server
        commit_hash: Hash of the commit to revert

    Returns:
        Dictionary with revert status
    """
    return git_manager.revert_commit(server_name, commit_hash)


@mcp.tool()
def create_branch(
    server_name: str,
    branch_name: str,
) -> Dict[str, Any]:
    """
    Create and checkout a new branch in a server's project.

    Args:
        server_name: Name of the server
        branch_name: Name for the new branch

    Returns:
        Dictionary with success status
    """
    return git_manager.create_branch(server_name, branch_name)


if __name__ == "__main__":
    # Run the MCP server
    mcp.run()
