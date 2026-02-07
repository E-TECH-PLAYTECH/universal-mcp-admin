"""
mcp_manager.py - Logic for parsing and modifying other MCP servers
"""

import ast
import json
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Callable, Dict, Optional, Tuple

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
    
    # Extended file extensions for all supported languages
    source_extensions = ('.py', '.js', '.rs', '.c', '.cpp', '.cc', '.cxx', '.go', '.ts')
    
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
    elif command in ("cargo", "rustc"):
        # Look for .rs file in args
        for arg in args:
            if arg.endswith(".rs"):
                source_file = arg
                break
    elif command in ("gcc", "clang"):
        # Look for .c file in args
        for arg in args:
            if arg.endswith(".c"):
                source_file = arg
                break
    elif command in ("g++", "clang++"):
        # Look for .cpp, .cc, .cxx files in args
        for arg in args:
            if arg.endswith((".cpp", ".cc", ".cxx")):
                source_file = arg
                break
    elif command == "go":
        # Look for .go file in args
        for arg in args:
            if arg.endswith(".go"):
                source_file = arg
                break
    elif command in ("tsc", "ts-node"):
        # Look for .ts file in args
        for arg in args:
            if arg.endswith(".ts"):
                source_file = arg
                break
    elif command == "uvx" or command == "npx":
        # For package managers, check if there's a direct file reference
        for arg in args:
            if arg.endswith(source_extensions):
                source_file = arg
                break
    else:
        # Try to find any supported source file in args
        for arg in args:
            if arg.endswith(source_extensions):
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
        rf'@\w+\.tool\(\)\s*\n\s*def\s+{re.escape(tool_name)}\s*\(',  # @mcp.tool()\ndef tool_name(
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


def validate_javascript_code(code: str) -> Tuple[bool, str]:
    """
    Validate JavaScript code using Node.js syntax checking.
    
    Args:
        code: JavaScript code to validate
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    try:
        # Use Node.js --check flag with a temporary file
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', suffix='.js', delete=False, encoding='utf-8') as f:
            f.write(code)
            temp_path = f.name
        
        try:
            process = subprocess.run(
                ["node", "--check", temp_path],
                capture_output=True,
                text=True,
                timeout=5
            )
            os.unlink(temp_path)
            
            if process.returncode == 0:
                return True, ""
            else:
                error_msg = process.stderr.strip() or process.stdout.strip()
                return False, f"JavaScript syntax error: {error_msg}"
        except Exception:
            if os.path.exists(temp_path):
                os.unlink(temp_path)
            raise
    except FileNotFoundError:
        return False, "Node.js not found. Please install Node.js to validate JavaScript code."
    except subprocess.TimeoutExpired:
        return False, "JavaScript validation timed out"
    except Exception as e:
        return False, f"Failed to validate JavaScript: {str(e)}"


def check_tool_exists_javascript(source_code: str, tool_name: str) -> bool:
    """
    Check if a tool with the given name already exists in JavaScript source code.
    
    Args:
        source_code: JavaScript source code to check
        tool_name: Name of the tool to look for
        
    Returns:
        True if tool exists, False otherwise
    """
    # Look for common patterns of tool definition in JavaScript
    patterns = [
        rf'\.tool\(["\']?{re.escape(tool_name)}["\']?',  # .tool("tool_name")
        rf'name:\s*["\']{re.escape(tool_name)}["\']',  # name: "tool_name"
        rf'function\s+{re.escape(tool_name)}\s*\(',  # function tool_name(
        rf'const\s+{re.escape(tool_name)}\s*=',  # const tool_name =
        rf'async\s+function\s+{re.escape(tool_name)}\s*\(',  # async function tool_name(
    ]
    
    for pattern in patterns:
        if re.search(pattern, source_code):
            return True
    
    return False


def inject_tool_into_javascript_file(
    server_name: str, 
    tool_name: str, 
    tool_code: str
) -> Tuple[bool, str]:
    """
    Inject a new tool capability into a JavaScript MCP server.
    
    This performs hot-patching by:
    1. Reading the target server's JavaScript file
    2. Checking if tool already exists
    3. Validating the new tool code
    4. Creating a backup
    5. Appending the new tool to the file
    
    Args:
        server_name: Name of the server to modify
        tool_name: Name of the tool to inject
        tool_code: JavaScript code for the tool
        
    Returns:
        Tuple of (success, message)
    """
    try:
        # Read the source file (limit to reasonable size for duplicate check)
        source_code, source_path = read_source_file(server_name, max_chars=100000)
        
        # Check if tool already exists
        if check_tool_exists_javascript(source_code, tool_name):
            return False, f"Tool '{tool_name}' already exists in {source_path}"
        
        # Validate the tool code syntax
        is_valid, error_msg = validate_javascript_code(tool_code)
        if not is_valid:
            return False, f"Invalid JavaScript code: {error_msg}"
        
        # Also validate that adding it won't break the file
        combined_code = source_code + "\n\n" + tool_code
        is_valid, error_msg = validate_javascript_code(combined_code)
        if not is_valid:
            return False, f"Adding tool would break file syntax: {error_msg}"
        
        # Create backup
        backup_path = create_backup(source_path)
        
        # Append the tool code
        with open(source_path, "a", encoding="utf-8") as f:
            f.write("\n\n")
            f.write(f"// Tool injected by universal-mcp-admin\n")
            f.write(tool_code)
            f.write("\n")
        
        return True, f"Tool '{tool_name}' injected successfully. Backup created at {backup_path}"
        
    except Exception as e:
        return False, f"Failed to inject tool: {str(e)}"


# ============================================================================
# Rust Language Handlers
# ============================================================================

def validate_rust_code(code: str) -> Tuple[bool, str]:
    """
    Validate Rust code using rustc --check.
    
    Args:
        code: Rust code to validate
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    try:
        with tempfile.NamedTemporaryFile(mode='w', suffix='.rs', delete=False, encoding='utf-8') as f:
            f.write(code)
            temp_path = f.name
        
        try:
            process = subprocess.run(
                ["rustc", "--check", temp_path],
                capture_output=True,
                text=True,
                timeout=10
            )
            os.unlink(temp_path)
            
            if process.returncode == 0:
                return True, ""
            else:
                error_msg = process.stderr.strip() or process.stdout.strip()
                return False, f"Rust syntax error: {error_msg}"
        except Exception:
            if os.path.exists(temp_path):
                os.unlink(temp_path)
            raise
    except FileNotFoundError:
        return False, "rustc not found. Install Rust toolchain to validate Rust code."
    except subprocess.TimeoutExpired:
        return False, "Rust validation timed out"
    except Exception as e:
        return False, f"Failed to validate Rust: {str(e)}"


def check_tool_exists_rust(source_code: str, tool_name: str) -> bool:
    """
    Check if a tool with the given name already exists in Rust source code.
    
    Args:
        source_code: Rust source code to check
        tool_name: Name of the tool to look for
        
    Returns:
        True if tool exists, False otherwise
    """
    patterns = [
        rf'#\[mcp::tool\(name\s*=\s*["\']{re.escape(tool_name)}["\']',  # #[mcp::tool(name = "tool_name")]
        rf'pub\s+fn\s+{re.escape(tool_name)}\s*\(',  # pub fn tool_name(
        rf'async\s+fn\s+{re.escape(tool_name)}\s*\(',  # async fn tool_name(
        rf'fn\s+{re.escape(tool_name)}\s*\(',  # fn tool_name(
    ]
    
    for pattern in patterns:
        if re.search(pattern, source_code):
            return True
    
    return False


def inject_tool_into_rust_file(
    server_name: str,
    tool_name: str,
    tool_code: str
) -> Tuple[bool, str]:
    """
    Inject a new tool capability into a Rust MCP server.
    
    Args:
        server_name: Name of the server to modify
        tool_name: Name of the tool to inject
        tool_code: Rust code for the tool
        
    Returns:
        Tuple of (success, message)
    """
    try:
        source_code, source_path = read_source_file(server_name, max_chars=100000)
        
        if check_tool_exists_rust(source_code, tool_name):
            return False, f"Tool '{tool_name}' already exists in {source_path}"
        
        is_valid, error_msg = validate_rust_code(tool_code)
        if not is_valid:
            return False, f"Invalid Rust code: {error_msg}"
        
        combined_code = source_code + "\n\n" + tool_code
        is_valid, error_msg = validate_rust_code(combined_code)
        if not is_valid:
            return False, f"Adding tool would break file syntax: {error_msg}"
        
        backup_path = create_backup(source_path)
        
        with open(source_path, "a", encoding="utf-8") as f:
            f.write("\n\n")
            f.write(f"// Tool injected by universal-mcp-admin\n")
            f.write(tool_code)
            f.write("\n")
        
        return True, f"Tool '{tool_name}' injected successfully. Backup created at {backup_path}. Note: Compilation required."
        
    except Exception as e:
        return False, f"Failed to inject tool: {str(e)}"


# ============================================================================
# C Language Handlers
# ============================================================================

def validate_c_code(code: str) -> Tuple[bool, str]:
    """
    Validate C code using gcc or clang syntax checking.
    
    Args:
        code: C code to validate
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    try:
        with tempfile.NamedTemporaryFile(mode='w', suffix='.c', delete=False, encoding='utf-8') as f:
            f.write(code)
            temp_path = f.name
        
        # Try gcc first, then clang
        for compiler in ['gcc', 'clang']:
            try:
                process = subprocess.run(
                    [compiler, "-fsyntax-only", temp_path],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                os.unlink(temp_path)
                
                if process.returncode == 0:
                    return True, ""
                else:
                    error_msg = process.stderr.strip() or process.stdout.strip()
                    return False, f"C syntax error ({compiler}): {error_msg}"
            except FileNotFoundError:
                continue
        
        os.unlink(temp_path)
        return False, "Neither gcc nor clang found. Install a C compiler to validate C code."
    except subprocess.TimeoutExpired:
        if os.path.exists(temp_path):
            os.unlink(temp_path)
        return False, "C validation timed out"
    except Exception as e:
        if os.path.exists(temp_path):
            os.unlink(temp_path)
        return False, f"Failed to validate C: {str(e)}"


def check_tool_exists_c(source_code: str, tool_name: str) -> bool:
    """
    Check if a tool with the given name already exists in C source code.
    
    Args:
        source_code: C source code to check
        tool_name: Name of the tool to look for
        
    Returns:
        True if tool exists, False otherwise
    """
    patterns = [
        rf'void\s+{re.escape(tool_name)}\s*\(',  # void tool_name(
        rf'int\s+{re.escape(tool_name)}\s*\(',  # int tool_name(
        rf'static\s+.*\s+{re.escape(tool_name)}\s*\(',  # static ... tool_name(
        rf'{re.escape(tool_name)}\s*\(',  # tool_name(
    ]
    
    for pattern in patterns:
        if re.search(pattern, source_code):
            return True
    
    return False


def inject_tool_into_c_file(
    server_name: str,
    tool_name: str,
    tool_code: str
) -> Tuple[bool, str]:
    """
    Inject a new tool capability into a C MCP server.
    
    Args:
        server_name: Name of the server to modify
        tool_name: Name of the tool to inject
        tool_code: C code for the tool
        
    Returns:
        Tuple of (success, message)
    """
    try:
        source_code, source_path = read_source_file(server_name, max_chars=100000)
        
        if check_tool_exists_c(source_code, tool_name):
            return False, f"Tool '{tool_name}' already exists in {source_path}"
        
        is_valid, error_msg = validate_c_code(tool_code)
        if not is_valid:
            return False, f"Invalid C code: {error_msg}"
        
        combined_code = source_code + "\n\n" + tool_code
        is_valid, error_msg = validate_c_code(combined_code)
        if not is_valid:
            return False, f"Adding tool would break file syntax: {error_msg}"
        
        backup_path = create_backup(source_path)
        
        with open(source_path, "a", encoding="utf-8") as f:
            f.write("\n\n")
            f.write(f"/* Tool injected by universal-mcp-admin */\n")
            f.write(tool_code)
            f.write("\n")
        
        return True, f"Tool '{tool_name}' injected successfully. Backup created at {backup_path}. Note: Compilation required."
        
    except Exception as e:
        return False, f"Failed to inject tool: {str(e)}"


# ============================================================================
# C++ Language Handlers
# ============================================================================

def validate_cpp_code(code: str) -> Tuple[bool, str]:
    """
    Validate C++ code using g++ or clang++ syntax checking.
    
    Args:
        code: C++ code to validate
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    try:
        with tempfile.NamedTemporaryFile(mode='w', suffix='.cpp', delete=False, encoding='utf-8') as f:
            f.write(code)
            temp_path = f.name
        
        # Try g++ first, then clang++
        for compiler in ['g++', 'clang++']:
            try:
                process = subprocess.run(
                    [compiler, "-fsyntax-only", "-std=c++17", temp_path],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                os.unlink(temp_path)
                
                if process.returncode == 0:
                    return True, ""
                else:
                    error_msg = process.stderr.strip() or process.stdout.strip()
                    return False, f"C++ syntax error ({compiler}): {error_msg}"
            except FileNotFoundError:
                continue
        
        os.unlink(temp_path)
        return False, "Neither g++ nor clang++ found. Install a C++ compiler to validate C++ code."
    except subprocess.TimeoutExpired:
        if os.path.exists(temp_path):
            os.unlink(temp_path)
        return False, "C++ validation timed out"
    except Exception as e:
        if os.path.exists(temp_path):
            os.unlink(temp_path)
        return False, f"Failed to validate C++: {str(e)}"


def check_tool_exists_cpp(source_code: str, tool_name: str) -> bool:
    """
    Check if a tool with the given name already exists in C++ source code.
    
    Args:
        source_code: C++ source code to check
        tool_name: Name of the tool to look for
        
    Returns:
        True if tool exists, False otherwise
    """
    patterns = [
        rf'void\s+{re.escape(tool_name)}\s*\(',  # void tool_name(
        rf'int\s+{re.escape(tool_name)}\s*\(',  # int tool_name(
        rf'auto\s+{re.escape(tool_name)}\s*\(',  # auto tool_name(
        rf'std::.*\s+{re.escape(tool_name)}\s*\(',  # std::... tool_name(
        rf'class\s+{re.escape(tool_name)}',  # class tool_name
    ]
    
    for pattern in patterns:
        if re.search(pattern, source_code):
            return True
    
    return False


def inject_tool_into_cpp_file(
    server_name: str,
    tool_name: str,
    tool_code: str
) -> Tuple[bool, str]:
    """
    Inject a new tool capability into a C++ MCP server.
    
    Args:
        server_name: Name of the server to modify
        tool_name: Name of the tool to inject
        tool_code: C++ code for the tool
        
    Returns:
        Tuple of (success, message)
    """
    try:
        source_code, source_path = read_source_file(server_name, max_chars=100000)
        
        if check_tool_exists_cpp(source_code, tool_name):
            return False, f"Tool '{tool_name}' already exists in {source_path}"
        
        is_valid, error_msg = validate_cpp_code(tool_code)
        if not is_valid:
            return False, f"Invalid C++ code: {error_msg}"
        
        combined_code = source_code + "\n\n" + tool_code
        is_valid, error_msg = validate_cpp_code(combined_code)
        if not is_valid:
            return False, f"Adding tool would break file syntax: {error_msg}"
        
        backup_path = create_backup(source_path)
        
        with open(source_path, "a", encoding="utf-8") as f:
            f.write("\n\n")
            f.write(f"// Tool injected by universal-mcp-admin\n")
            f.write(tool_code)
            f.write("\n")
        
        return True, f"Tool '{tool_name}' injected successfully. Backup created at {backup_path}. Note: Compilation required."
        
    except Exception as e:
        return False, f"Failed to inject tool: {str(e)}"


# ============================================================================
# Go Language Handlers
# ============================================================================

def validate_go_code(code: str) -> Tuple[bool, str]:
    """
    Validate Go code using go build syntax checking.
    
    Args:
        code: Go code to validate
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            test_file = tmp_path / "test.go"
            test_file.write_text(code, encoding='utf-8')
            
            process = subprocess.run(
                ["go", "build", "-o", str(tmp_path / "test"), str(test_file)],
                capture_output=True,
                text=True,
                timeout=10,
                cwd=tmpdir
            )
            
            if process.returncode == 0:
                return True, ""
            else:
                error_msg = process.stderr.strip() or process.stdout.strip()
                return False, f"Go syntax error: {error_msg}"
    except FileNotFoundError:
        return False, "go not found. Install Go toolchain to validate Go code."
    except subprocess.TimeoutExpired:
        return False, "Go validation timed out"
    except Exception as e:
        return False, f"Failed to validate Go: {str(e)}"


def check_tool_exists_go(source_code: str, tool_name: str) -> bool:
    """
    Check if a tool with the given name already exists in Go source code.
    
    Args:
        source_code: Go source code to check
        tool_name: Name of the tool to look for
        
    Returns:
        True if tool exists, False otherwise
    """
    patterns = [
        rf'func\s+{re.escape(tool_name)}\s*\(',  # func tool_name(
        rf'func\s+\(.*\)\s+{re.escape(tool_name)}\s*\(',  # func (receiver) tool_name(
        rf'var\s+{re.escape(tool_name)}\s*=',  # var tool_name =
        rf'const\s+{re.escape(tool_name)}\s*=',  # const tool_name =
    ]
    
    for pattern in patterns:
        if re.search(pattern, source_code):
            return True
    
    return False


def inject_tool_into_go_file(
    server_name: str,
    tool_name: str,
    tool_code: str
) -> Tuple[bool, str]:
    """
    Inject a new tool capability into a Go MCP server.
    
    Args:
        server_name: Name of the server to modify
        tool_name: Name of the tool to inject
        tool_code: Go code for the tool
        
    Returns:
        Tuple of (success, message)
    """
    try:
        source_code, source_path = read_source_file(server_name, max_chars=100000)
        
        if check_tool_exists_go(source_code, tool_name):
            return False, f"Tool '{tool_name}' already exists in {source_path}"
        
        is_valid, error_msg = validate_go_code(tool_code)
        if not is_valid:
            return False, f"Invalid Go code: {error_msg}"
        
        combined_code = source_code + "\n\n" + tool_code
        is_valid, error_msg = validate_go_code(combined_code)
        if not is_valid:
            return False, f"Adding tool would break file syntax: {error_msg}"
        
        backup_path = create_backup(source_path)
        
        with open(source_path, "a", encoding="utf-8") as f:
            f.write("\n\n")
            f.write(f"// Tool injected by universal-mcp-admin\n")
            f.write(tool_code)
            f.write("\n")
        
        return True, f"Tool '{tool_name}' injected successfully. Backup created at {backup_path}. Note: Compilation required."
        
    except Exception as e:
        return False, f"Failed to inject tool: {str(e)}"


# ============================================================================
# TypeScript Language Handlers
# ============================================================================

def validate_typescript_code(code: str) -> Tuple[bool, str]:
    """
    Validate TypeScript code using tsc syntax checking.
    
    Args:
        code: TypeScript code to validate
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            test_file = tmp_path / "test.ts"
            test_file.write_text(code, encoding='utf-8')
            
            # Create minimal tsconfig.json
            tsconfig = tmp_path / "tsconfig.json"
            tsconfig.write_text('{"compilerOptions": {"noEmit": true, "skipLibCheck": true}}', encoding='utf-8')
            
            process = subprocess.run(
                ["tsc", "--noEmit", str(test_file)],
                capture_output=True,
                text=True,
                timeout=10,
                cwd=tmpdir
            )
            
            if process.returncode == 0:
                return True, ""
            else:
                error_msg = process.stderr.strip() or process.stdout.strip()
                return False, f"TypeScript syntax error: {error_msg}"
    except FileNotFoundError:
        return False, "tsc not found. Install TypeScript (npm install -g typescript) to validate TypeScript code."
    except subprocess.TimeoutExpired:
        return False, "TypeScript validation timed out"
    except Exception as e:
        return False, f"Failed to validate TypeScript: {str(e)}"


def check_tool_exists_typescript(source_code: str, tool_name: str) -> bool:
    """
    Check if a tool with the given name already exists in TypeScript source code.
    
    Args:
        source_code: TypeScript source code to check
        tool_name: Name of the tool to look for
        
    Returns:
        True if tool exists, False otherwise
    """
    patterns = [
        rf'\.tool\(["\']?{re.escape(tool_name)}["\']?',  # .tool("tool_name")
        rf'name:\s*["\']{re.escape(tool_name)}["\']',  # name: "tool_name"
        rf'function\s+{re.escape(tool_name)}\s*\(',  # function tool_name(
        rf'const\s+{re.escape(tool_name)}\s*[:=]',  # const tool_name: or =
        rf'async\s+function\s+{re.escape(tool_name)}\s*\(',  # async function tool_name(
        rf'export\s+function\s+{re.escape(tool_name)}\s*\(',  # export function tool_name(
    ]
    
    for pattern in patterns:
        if re.search(pattern, source_code):
            return True
    
    return False


def inject_tool_into_typescript_file(
    server_name: str,
    tool_name: str,
    tool_code: str
) -> Tuple[bool, str]:
    """
    Inject a new tool capability into a TypeScript MCP server.
    
    Args:
        server_name: Name of the server to modify
        tool_name: Name of the tool to inject
        tool_code: TypeScript code for the tool
        
    Returns:
        Tuple of (success, message)
    """
    try:
        source_code, source_path = read_source_file(server_name, max_chars=100000)
        
        if check_tool_exists_typescript(source_code, tool_name):
            return False, f"Tool '{tool_name}' already exists in {source_path}"
        
        is_valid, error_msg = validate_typescript_code(tool_code)
        if not is_valid:
            return False, f"Invalid TypeScript code: {error_msg}"
        
        combined_code = source_code + "\n\n" + tool_code
        is_valid, error_msg = validate_typescript_code(combined_code)
        if not is_valid:
            return False, f"Adding tool would break file syntax: {error_msg}"
        
        backup_path = create_backup(source_path)
        
        with open(source_path, "a", encoding="utf-8") as f:
            f.write("\n\n")
            f.write(f"// Tool injected by universal-mcp-admin\n")
            f.write(tool_code)
            f.write("\n")
        
        return True, f"Tool '{tool_name}' injected successfully. Backup created at {backup_path}. Note: Compilation required."
        
    except Exception as e:
        return False, f"Failed to inject tool: {str(e)}"


# ============================================================================
# Language Registry and Generic Dispatcher
# ============================================================================

# Language handler registry mapping file extensions to handler functions
LANGUAGE_HANDLERS: Dict[str, Dict[str, Any]] = {
    '.py': {
        'validate': validate_python_code,
        'check_tool_exists': check_tool_exists,
        'inject': inject_tool_into_python_file,
        'needs_compilation': False,
        'comment_prefix': '#'
    },
    '.js': {
        'validate': validate_javascript_code,
        'check_tool_exists': check_tool_exists_javascript,
        'inject': inject_tool_into_javascript_file,
        'needs_compilation': False,
        'comment_prefix': '//'
    },
    '.rs': {
        'validate': validate_rust_code,
        'check_tool_exists': check_tool_exists_rust,
        'inject': inject_tool_into_rust_file,
        'needs_compilation': True,
        'comment_prefix': '//'
    },
    '.c': {
        'validate': validate_c_code,
        'check_tool_exists': check_tool_exists_c,
        'inject': inject_tool_into_c_file,
        'needs_compilation': True,
        'comment_prefix': '//'
    },
    '.cpp': {
        'validate': validate_cpp_code,
        'check_tool_exists': check_tool_exists_cpp,
        'inject': inject_tool_into_cpp_file,
        'needs_compilation': True,
        'comment_prefix': '//'
    },
    '.cc': {
        'validate': validate_cpp_code,
        'check_tool_exists': check_tool_exists_cpp,
        'inject': inject_tool_into_cpp_file,
        'needs_compilation': True,
        'comment_prefix': '//'
    },
    '.cxx': {
        'validate': validate_cpp_code,
        'check_tool_exists': check_tool_exists_cpp,
        'inject': inject_tool_into_cpp_file,
        'needs_compilation': True,
        'comment_prefix': '//'
    },
    '.go': {
        'validate': validate_go_code,
        'check_tool_exists': check_tool_exists_go,
        'inject': inject_tool_into_go_file,
        'needs_compilation': True,
        'comment_prefix': '//'
    },
    '.ts': {
        'validate': validate_typescript_code,
        'check_tool_exists': check_tool_exists_typescript,
        'inject': inject_tool_into_typescript_file,
        'needs_compilation': True,
        'comment_prefix': '//'
    }
}


def inject_tool_generic(
    server_name: str,
    tool_name: str,
    tool_code: str
) -> Tuple[bool, str]:
    """
    Generic tool injection that routes to language-specific handlers.
    
    Args:
        server_name: Name of the server to modify
        tool_name: Name of the tool to inject
        tool_code: Code for the tool
        
    Returns:
        Tuple of (success, message)
    """
    try:
        source_path = find_server_source_file(server_name)
        extension = source_path.suffix
        
        if extension not in LANGUAGE_HANDLERS:
            return False, f"Unsupported language: {extension}. Supported: {', '.join(LANGUAGE_HANDLERS.keys())}"
        
        handler = LANGUAGE_HANDLERS[extension]
        return handler['inject'](server_name, tool_name, tool_code)
    except Exception as e:
        return False, f"Failed to inject tool: {str(e)}"
