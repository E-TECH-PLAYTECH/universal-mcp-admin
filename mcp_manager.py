"""
mcp_manager.py - Logic for parsing and modifying other MCP servers
"""

import ast
import os
import re
import shutil
from pathlib import Path
from typing import Optional, Tuple

from config_manager import get_server_config


def get_allowed_root_dir() -> Optional[Path]:
    """
    Get the allowed root directory for operations from environment.
    
    Returns:
        Path to allowed root directory, or None if not restricted
    """
    allowed_dir = os.getenv("ALLOWED_ROOT_DIR", "")
    if allowed_dir:
        return Path(allowed_dir).resolve()
    return None


def check_path_allowed(file_path: Path) -> None:
    """
    Check if a file path is within the allowed root directory.
    
    Args:
        file_path: Path to check
        
    Raises:
        PermissionError: If path is outside allowed root directory
    """
    allowed_root = get_allowed_root_dir()
    if allowed_root is None:
        return  # No restriction
    
    resolved_path = file_path.resolve()
    try:
        resolved_path.relative_to(allowed_root)
    except ValueError:
        raise PermissionError(
            f"Path '{file_path}' is outside allowed root directory '{allowed_root}'"
        )


def find_server_source_file(server_name: str) -> Path:
    """
    Locate the source code file for an MCP server.
    
    Args:
        server_name: Name of the server from config
        
    Returns:
        Path to the server's main source file
        
    Raises:
        ValueError: If server not found or source file cannot be determined
        FileNotFoundError: If source file doesn't exist
    """
    server_config = get_server_config(server_name)
    
    # Get the command and working directory
    command = server_config.get("command", "")
    args = server_config.get("args", [])
    cwd = server_config.get("cwd", "")
    
    # Determine the source file
    source_file = None
    
    if command == "python" or command == "python3":
        # Look for .py file in args
        for arg in args:
            if arg.endswith(".py"):
                source_file = arg
                break
    elif command == "node":
        # Look for .js file in args
        for arg in args:
            if arg.endswith(".js"):
                source_file = arg
                break
    elif command == "uvx" or command == "npx":
        # For package managers, check if there's a direct file reference
        for arg in args:
            if arg.endswith((".py", ".js")):
                source_file = arg
                break
    else:
        # Try to find any .py or .js file in args
        for arg in args:
            if arg.endswith((".py", ".js")):
                source_file = arg
                break
    
    if not source_file:
        raise ValueError(
            f"Cannot determine source file for server '{server_name}'. "
            f"Command: {command}, Args: {args}"
        )
    
    # Resolve the full path
    if cwd:
        base_path = Path(cwd)
    else:
        base_path = Path.cwd()
    
    full_path = (base_path / source_file).resolve()
    
    if not full_path.exists():
        raise FileNotFoundError(f"Source file not found: {full_path}")
    
    check_path_allowed(full_path)
    return full_path


def read_source_file(server_name: str, max_chars: int = 50000) -> Tuple[str, Path]:
    """
    Read the source code of an MCP server.
    
    Args:
        server_name: Name of the server from config
        max_chars: Maximum characters to return (truncate if larger)
        
    Returns:
        Tuple of (source_code, file_path)
    """
    source_path = find_server_source_file(server_name)
    
    with open(source_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    original_length = len(content)
    if original_length > max_chars:
        content = content[:max_chars] + f"\n\n... (truncated, total size: {original_length} chars)"
    
    return content, source_path


def validate_python_code(code: str) -> Tuple[bool, str]:
    """
    Validate Python code using AST parsing.
    
    Args:
        code: Python code to validate
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    try:
        ast.parse(code)
        return True, ""
    except SyntaxError as e:
        return False, f"Syntax error at line {e.lineno}: {e.msg}"
    except Exception as e:
        return False, f"Parse error: {str(e)}"


def create_backup(file_path: Path) -> Path:
    """
    Create a backup of a file before modifying it.
    
    Args:
        file_path: Path to the file to backup
        
    Returns:
        Path to the backup file
    """
    backup_path = file_path.with_suffix(file_path.suffix + ".bak")
    shutil.copy2(file_path, backup_path)
    return backup_path


def check_tool_exists(source_code: str, tool_name: str) -> bool:
    """
    Check if a tool with the given name already exists in the source code.
    
    Args:
        source_code: Source code to check
        tool_name: Name of the tool to look for
        
    Returns:
        True if tool exists, False otherwise
    """
    # Look for common patterns of tool definition
    patterns = [
        rf'@\w+\.tool\(\s*["\']?{re.escape(tool_name)}["\']?',  # @mcp.tool("tool_name")
        rf'@\w+\.tool\s*\n\s*def\s+{re.escape(tool_name)}\s*\(',  # @mcp.tool\ndef tool_name(
        rf'def\s+{re.escape(tool_name)}\s*\([^)]*\)\s*->',  # def tool_name(...) ->
    ]
    
    for pattern in patterns:
        if re.search(pattern, source_code):
            return True
    
    return False


def inject_tool_into_python_file(
    server_name: str, 
    tool_name: str, 
    tool_code: str
) -> Tuple[bool, str]:
    """
    Inject a new tool capability into a Python MCP server.
    
    This performs hot-patching by:
    1. Reading the target server's Python file
    2. Checking if tool already exists
    3. Validating the new tool code
    4. Creating a backup
    5. Appending the new tool to the file
    
    Args:
        server_name: Name of the server to modify
        tool_name: Name of the tool to inject
        tool_code: Python code for the tool (should include @mcp.tool decorator)
        
    Returns:
        Tuple of (success, message)
    """
    try:
        # Read the source file (limit to reasonable size for duplicate check)
        source_code, source_path = read_source_file(server_name, max_chars=100000)
        
        # Check if tool already exists
        if check_tool_exists(source_code, tool_name):
            return False, f"Tool '{tool_name}' already exists in {source_path}"
        
        # Validate the tool code syntax
        is_valid, error_msg = validate_python_code(tool_code)
        if not is_valid:
            return False, f"Invalid Python code: {error_msg}"
        
        # Also validate that adding it won't break the file
        combined_code = source_code + "\n\n" + tool_code
        is_valid, error_msg = validate_python_code(combined_code)
        if not is_valid:
            return False, f"Adding tool would break file syntax: {error_msg}"
        
        # Create backup
        backup_path = create_backup(source_path)
        
        # Append the tool code
        with open(source_path, "a", encoding="utf-8") as f:
            f.write("\n\n")
            f.write(f"# Tool injected by universal-mcp-admin\n")
            f.write(tool_code)
            f.write("\n")
        
        return True, f"Tool '{tool_name}' injected successfully. Backup created at {backup_path}"
        
    except Exception as e:
        return False, f"Failed to inject tool: {str(e)}"


def patch_file_with_regex(
    file_path: str,
    search_pattern: str,
    replacement_text: str
) -> Tuple[bool, str]:
    """
    Modify a file using regex pattern matching and replacement.
    
    Args:
        file_path: Path to the file to modify
        search_pattern: Regex pattern to search for
        replacement_text: Text to replace matches with
        
    Returns:
        Tuple of (success, message)
    """
    try:
        path = Path(file_path).resolve()
        check_path_allowed(path)
        
        if not path.exists():
            return False, f"File not found: {file_path}"
        
        # Read the file
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        
        # Try to compile the regex pattern
        try:
            pattern = re.compile(search_pattern)
        except re.error as e:
            return False, f"Invalid regex pattern: {str(e)}"
        
        # Check if pattern matches anything
        if not pattern.search(content):
            return False, f"Pattern '{search_pattern}' not found in file"
        
        # Create backup
        backup_path = create_backup(path)
        
        # Perform replacement
        new_content = pattern.sub(replacement_text, content)
        
        # Write the modified content
        with open(path, "w", encoding="utf-8") as f:
            f.write(new_content)
        
        return True, f"File patched successfully. Backup created at {backup_path}"
        
    except Exception as e:
        return False, f"Failed to patch file: {str(e)}"
