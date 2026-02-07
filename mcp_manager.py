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
    source_extensions = (
        '.py', '.js', '.rs', '.c', '.cpp', '.cc', '.cxx', '.go', '.ts', '.zig', '.java', '.rb',
        '.kt', '.kts', '.swift', '.cs', '.php', '.lua', '.scala', '.ex', '.exs', '.dart',
        '.hs', '.ml', '.mli', '.nim', '.d', '.cr', '.raku', '.rakumod', '.pm6', '.jl',
    )
    
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
    elif command == "zig":
        # Look for .zig file in args
        for arg in args:
            if arg.endswith(".zig"):
                source_file = arg
                break
    elif command in ("java", "javac", "mvn", "gradle"):
        # Look for .java file in args
        for arg in args:
            if arg.endswith(".java"):
                source_file = arg
                break
    elif command == "ruby":
        # Look for .rb file in args
        for arg in args:
            if arg.endswith(".rb"):
                source_file = arg
                break
    elif command in ("kotlin", "kotlinc"):
        for arg in args:
            if arg.endswith((".kt", ".kts")):
                source_file = arg
                break
    elif command in ("swift", "swiftc"):
        for arg in args:
            if arg.endswith(".swift"):
                source_file = arg
                break
    elif command in ("dotnet", "csc", "mcs"):
        for arg in args:
            if arg.endswith(".cs"):
                source_file = arg
                break
    elif command == "php":
        for arg in args:
            if arg.endswith(".php"):
                source_file = arg
                break
    elif command in ("lua", "luajit"):
        for arg in args:
            if arg.endswith(".lua"):
                source_file = arg
                break
    elif command in ("scala", "scalac"):
        for arg in args:
            if arg.endswith(".scala"):
                source_file = arg
                break
    elif command in ("elixir", "elixirc", "mix"):
        for arg in args:
            if arg.endswith((".ex", ".exs")):
                source_file = arg
                break
    elif command == "dart":
        for arg in args:
            if arg.endswith(".dart"):
                source_file = arg
                break
    elif command in ("ghc", "runhaskell", "cabal", "stack"):
        for arg in args:
            if arg.endswith(".hs"):
                source_file = arg
                break
    elif command in ("ocamlc", "ocamlopt", "dune"):
        for arg in args:
            if arg.endswith((".ml", ".mli")):
                source_file = arg
                break
    elif command in ("nim", "nimble"):
        for arg in args:
            if arg.endswith(".nim"):
                source_file = arg
                break
    elif command in ("dmd", "ldc2", "gdc", "dub"):
        for arg in args:
            if arg.endswith(".d"):
                source_file = arg
                break
    elif command == "crystal":
        for arg in args:
            if arg.endswith(".cr"):
                source_file = arg
                break
    elif command in ("raku", "perl6"):
        for arg in args:
            if arg.endswith((".raku", ".rakumod", ".pm6")):
                source_file = arg
                break
    elif command == "julia":
        for arg in args:
            if arg.endswith(".jl"):
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
# Zig Language Handlers
# ============================================================================

def validate_zig_code(code: str) -> Tuple[bool, str]:
    """
    Validate Zig code using zig ast-check.
    
    Args:
        code: Zig code to validate
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    try:
        with tempfile.NamedTemporaryFile(mode='w', suffix='.zig', delete=False, encoding='utf-8') as f:
            f.write(code)
            temp_path = f.name
        
        try:
            process = subprocess.run(
                ["zig", "ast-check", temp_path],
                capture_output=True,
                text=True,
                timeout=10
            )
            os.unlink(temp_path)
            
            if process.returncode == 0:
                return True, ""
            else:
                error_msg = process.stderr.strip() or process.stdout.strip()
                return False, f"Zig syntax error: {error_msg}"
        except Exception:
            if os.path.exists(temp_path):
                os.unlink(temp_path)
            raise
    except FileNotFoundError:
        return False, "zig not found. Install Zig (https://ziglang.org/download/) to validate Zig code."
    except subprocess.TimeoutExpired:
        return False, "Zig validation timed out"
    except Exception as e:
        return False, f"Failed to validate Zig: {str(e)}"


def check_tool_exists_zig(source_code: str, tool_name: str) -> bool:
    """
    Check if a tool with the given name already exists in Zig source code.
    
    Args:
        source_code: Zig source code to check
        tool_name: Name of the tool to look for
        
    Returns:
        True if tool exists, False otherwise
    """
    patterns = [
        rf'pub\s+fn\s+{re.escape(tool_name)}\s*\(',  # pub fn tool_name(
        rf'fn\s+{re.escape(tool_name)}\s*\(',  # fn tool_name(
        rf'const\s+{re.escape(tool_name)}\s*=',  # const tool_name =
        rf'var\s+{re.escape(tool_name)}\s*=',  # var tool_name =
    ]
    
    for pattern in patterns:
        if re.search(pattern, source_code):
            return True
    
    return False


def inject_tool_into_zig_file(
    server_name: str,
    tool_name: str,
    tool_code: str
) -> Tuple[bool, str]:
    """
    Inject a new tool capability into a Zig MCP server.
    
    Args:
        server_name: Name of the server to modify
        tool_name: Name of the tool to inject
        tool_code: Zig code for the tool
        
    Returns:
        Tuple of (success, message)
    """
    try:
        source_code, source_path = read_source_file(server_name, max_chars=100000)
        
        if check_tool_exists_zig(source_code, tool_name):
            return False, f"Tool '{tool_name}' already exists in {source_path}"
        
        is_valid, error_msg = validate_zig_code(tool_code)
        if not is_valid:
            return False, f"Invalid Zig code: {error_msg}"
        
        combined_code = source_code + "\n\n" + tool_code
        is_valid, error_msg = validate_zig_code(combined_code)
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
# Java Language Handlers
# ============================================================================

def validate_java_code(code: str) -> Tuple[bool, str]:
    """
    Validate Java code using javac syntax checking.
    
    Args:
        code: Java code to validate
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            # Attempt to extract public class name for file naming
            class_match = re.search(r'public\s+class\s+(\w+)', code)
            filename = (class_match.group(1) + ".java") if class_match else "Tool.java"
            test_file = tmp_path / filename
            test_file.write_text(code, encoding='utf-8')
            
            process = subprocess.run(
                ["javac", "-d", str(tmp_path), str(test_file)],
                capture_output=True,
                text=True,
                timeout=15,
                cwd=tmpdir
            )
            
            if process.returncode == 0:
                return True, ""
            else:
                error_msg = process.stderr.strip() or process.stdout.strip()
                return False, f"Java syntax error: {error_msg}"
    except FileNotFoundError:
        return False, "javac not found. Install a JDK to validate Java code."
    except subprocess.TimeoutExpired:
        return False, "Java validation timed out"
    except Exception as e:
        return False, f"Failed to validate Java: {str(e)}"


def check_tool_exists_java(source_code: str, tool_name: str) -> bool:
    """
    Check if a tool with the given name already exists in Java source code.
    
    Args:
        source_code: Java source code to check
        tool_name: Name of the tool to look for
        
    Returns:
        True if tool exists, False otherwise
    """
    patterns = [
        rf'(?:public|private|protected)\s+.*\s+{re.escape(tool_name)}\s*\(',  # public Type tool_name(
        rf'static\s+.*\s+{re.escape(tool_name)}\s*\(',  # static Type tool_name(
        rf'class\s+{re.escape(tool_name)}\s',  # class tool_name
        rf'interface\s+{re.escape(tool_name)}\s',  # interface tool_name
    ]
    
    for pattern in patterns:
        if re.search(pattern, source_code):
            return True
    
    return False


def inject_tool_into_java_file(
    server_name: str,
    tool_name: str,
    tool_code: str
) -> Tuple[bool, str]:
    """
    Inject a new tool capability into a Java MCP server.
    
    Args:
        server_name: Name of the server to modify
        tool_name: Name of the tool to inject
        tool_code: Java code for the tool
        
    Returns:
        Tuple of (success, message)
    """
    try:
        source_code, source_path = read_source_file(server_name, max_chars=100000)
        
        if check_tool_exists_java(source_code, tool_name):
            return False, f"Tool '{tool_name}' already exists in {source_path}"
        
        is_valid, error_msg = validate_java_code(tool_code)
        if not is_valid:
            return False, f"Invalid Java code: {error_msg}"
        
        combined_code = source_code + "\n\n" + tool_code
        is_valid, error_msg = validate_java_code(combined_code)
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
# Ruby Language Handlers
# ============================================================================

def validate_ruby_code(code: str) -> Tuple[bool, str]:
    """
    Validate Ruby code using ruby -c syntax checking.
    
    Args:
        code: Ruby code to validate
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    try:
        with tempfile.NamedTemporaryFile(mode='w', suffix='.rb', delete=False, encoding='utf-8') as f:
            f.write(code)
            temp_path = f.name
        
        try:
            process = subprocess.run(
                ["ruby", "-c", temp_path],
                capture_output=True,
                text=True,
                timeout=10
            )
            os.unlink(temp_path)
            
            if process.returncode == 0:
                return True, ""
            else:
                error_msg = process.stderr.strip() or process.stdout.strip()
                return False, f"Ruby syntax error: {error_msg}"
        except Exception:
            if os.path.exists(temp_path):
                os.unlink(temp_path)
            raise
    except FileNotFoundError:
        return False, "ruby not found. Install Ruby to validate Ruby code."
    except subprocess.TimeoutExpired:
        return False, "Ruby validation timed out"
    except Exception as e:
        return False, f"Failed to validate Ruby: {str(e)}"


def check_tool_exists_ruby(source_code: str, tool_name: str) -> bool:
    """
    Check if a tool with the given name already exists in Ruby source code.
    
    Args:
        source_code: Ruby source code to check
        tool_name: Name of the tool to look for
        
    Returns:
        True if tool exists, False otherwise
    """
    patterns = [
        rf'def\s+{re.escape(tool_name)}\s*[\((\n]',  # def tool_name( or def tool_name\n
        rf'def\s+self\.{re.escape(tool_name)}\s*[\((\n]',  # def self.tool_name(
        rf'class\s+{re.escape(tool_name)}\s',  # class tool_name
        rf'module\s+{re.escape(tool_name)}\s',  # module tool_name
    ]
    
    for pattern in patterns:
        if re.search(pattern, source_code):
            return True
    
    return False


def inject_tool_into_ruby_file(
    server_name: str,
    tool_name: str,
    tool_code: str
) -> Tuple[bool, str]:
    """
    Inject a new tool capability into a Ruby MCP server.
    
    Args:
        server_name: Name of the server to modify
        tool_name: Name of the tool to inject
        tool_code: Ruby code for the tool
        
    Returns:
        Tuple of (success, message)
    """
    try:
        source_code, source_path = read_source_file(server_name, max_chars=100000)
        
        if check_tool_exists_ruby(source_code, tool_name):
            return False, f"Tool '{tool_name}' already exists in {source_path}"
        
        is_valid, error_msg = validate_ruby_code(tool_code)
        if not is_valid:
            return False, f"Invalid Ruby code: {error_msg}"
        
        combined_code = source_code + "\n\n" + tool_code
        is_valid, error_msg = validate_ruby_code(combined_code)
        if not is_valid:
            return False, f"Adding tool would break file syntax: {error_msg}"
        
        backup_path = create_backup(source_path)
        
        with open(source_path, "a", encoding="utf-8") as f:
            f.write("\n\n")
            f.write(f"# Tool injected by universal-mcp-admin\n")
            f.write(tool_code)
            f.write("\n")
        
        return True, f"Tool '{tool_name}' injected successfully. Backup created at {backup_path}"
        
    except Exception as e:
        return False, f"Failed to inject tool: {str(e)}"


# ============================================================================
# Kotlin Language Handlers
# ============================================================================

def validate_kotlin_code(code: str) -> Tuple[bool, str]:
    """Validate Kotlin code using kotlinc."""
    try:
        with tempfile.NamedTemporaryFile(mode='w', suffix='.kt', delete=False, encoding='utf-8') as f:
            f.write(code)
            temp_path = f.name
        try:
            process = subprocess.run(
                ["kotlinc", "-script", temp_path],
                capture_output=True, text=True, timeout=15
            )
            os.unlink(temp_path)
            if process.returncode == 0:
                return True, ""
            error_msg = process.stderr.strip() or process.stdout.strip()
            return False, f"Kotlin syntax error: {error_msg}"
        except Exception:
            if os.path.exists(temp_path):
                os.unlink(temp_path)
            raise
    except FileNotFoundError:
        return False, "kotlinc not found. Install Kotlin to validate Kotlin code."
    except subprocess.TimeoutExpired:
        return False, "Kotlin validation timed out"
    except Exception as e:
        return False, f"Failed to validate Kotlin: {str(e)}"


def check_tool_exists_kotlin(source_code: str, tool_name: str) -> bool:
    """Check if a tool exists in Kotlin source code."""
    patterns = [
        rf'fun\s+{re.escape(tool_name)}\s*\(',
        rf'class\s+{re.escape(tool_name)}\s',
        rf'val\s+{re.escape(tool_name)}\s*[=:]',
        rf'var\s+{re.escape(tool_name)}\s*[=:]',
    ]
    return any(re.search(p, source_code) for p in patterns)


def inject_tool_into_kotlin_file(server_name: str, tool_name: str, tool_code: str) -> Tuple[bool, str]:
    """Inject a new tool into a Kotlin MCP server."""
    try:
        source_code, source_path = read_source_file(server_name, max_chars=100000)
        if check_tool_exists_kotlin(source_code, tool_name):
            return False, f"Tool '{tool_name}' already exists in {source_path}"
        is_valid, error_msg = validate_kotlin_code(tool_code)
        if not is_valid:
            return False, f"Invalid Kotlin code: {error_msg}"
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
# Swift Language Handlers
# ============================================================================

def validate_swift_code(code: str) -> Tuple[bool, str]:
    """Validate Swift code using swiftc -parse."""
    try:
        with tempfile.NamedTemporaryFile(mode='w', suffix='.swift', delete=False, encoding='utf-8') as f:
            f.write(code)
            temp_path = f.name
        try:
            process = subprocess.run(
                ["swiftc", "-parse", temp_path],
                capture_output=True, text=True, timeout=15
            )
            os.unlink(temp_path)
            if process.returncode == 0:
                return True, ""
            error_msg = process.stderr.strip() or process.stdout.strip()
            return False, f"Swift syntax error: {error_msg}"
        except Exception:
            if os.path.exists(temp_path):
                os.unlink(temp_path)
            raise
    except FileNotFoundError:
        return False, "swiftc not found. Install Swift to validate Swift code."
    except subprocess.TimeoutExpired:
        return False, "Swift validation timed out"
    except Exception as e:
        return False, f"Failed to validate Swift: {str(e)}"


def check_tool_exists_swift(source_code: str, tool_name: str) -> bool:
    """Check if a tool exists in Swift source code."""
    patterns = [
        rf'func\s+{re.escape(tool_name)}\s*\(',
        rf'class\s+{re.escape(tool_name)}\s',
        rf'struct\s+{re.escape(tool_name)}\s',
        rf'let\s+{re.escape(tool_name)}\s*[=:]',
        rf'var\s+{re.escape(tool_name)}\s*[=:]',
    ]
    return any(re.search(p, source_code) for p in patterns)


def inject_tool_into_swift_file(server_name: str, tool_name: str, tool_code: str) -> Tuple[bool, str]:
    """Inject a new tool into a Swift MCP server."""
    try:
        source_code, source_path = read_source_file(server_name, max_chars=100000)
        if check_tool_exists_swift(source_code, tool_name):
            return False, f"Tool '{tool_name}' already exists in {source_path}"
        is_valid, error_msg = validate_swift_code(tool_code)
        if not is_valid:
            return False, f"Invalid Swift code: {error_msg}"
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
# C# Language Handlers
# ============================================================================

def validate_csharp_code(code: str) -> Tuple[bool, str]:
    """Validate C# code using dotnet build or csc."""
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            test_file = tmp_path / "Tool.cs"
            test_file.write_text(code, encoding='utf-8')
            for compiler in [["dotnet", "build"], ["csc", "/nologo", "/t:library"]]:
                try:
                    process = subprocess.run(
                        compiler + [str(test_file)] if compiler[0] == "csc" else compiler,
                        capture_output=True, text=True, timeout=15, cwd=tmpdir
                    )
                    if process.returncode == 0:
                        return True, ""
                    error_msg = process.stderr.strip() or process.stdout.strip()
                    return False, f"C# syntax error: {error_msg}"
                except FileNotFoundError:
                    continue
            return False, "Neither dotnet nor csc found. Install .NET SDK to validate C# code."
    except subprocess.TimeoutExpired:
        return False, "C# validation timed out"
    except Exception as e:
        return False, f"Failed to validate C#: {str(e)}"


def check_tool_exists_csharp(source_code: str, tool_name: str) -> bool:
    """Check if a tool exists in C# source code."""
    patterns = [
        rf'(?:public|private|protected|internal)\s+.*\s+{re.escape(tool_name)}\s*\(',
        rf'static\s+.*\s+{re.escape(tool_name)}\s*\(',
        rf'class\s+{re.escape(tool_name)}\s',
        rf'interface\s+{re.escape(tool_name)}\s',
    ]
    return any(re.search(p, source_code) for p in patterns)


def inject_tool_into_csharp_file(server_name: str, tool_name: str, tool_code: str) -> Tuple[bool, str]:
    """Inject a new tool into a C# MCP server."""
    try:
        source_code, source_path = read_source_file(server_name, max_chars=100000)
        if check_tool_exists_csharp(source_code, tool_name):
            return False, f"Tool '{tool_name}' already exists in {source_path}"
        is_valid, error_msg = validate_csharp_code(tool_code)
        if not is_valid:
            return False, f"Invalid C# code: {error_msg}"
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
# PHP Language Handlers
# ============================================================================

def validate_php_code(code: str) -> Tuple[bool, str]:
    """Validate PHP code using php -l."""
    try:
        with tempfile.NamedTemporaryFile(mode='w', suffix='.php', delete=False, encoding='utf-8') as f:
            f.write(code)
            temp_path = f.name
        try:
            process = subprocess.run(
                ["php", "-l", temp_path],
                capture_output=True, text=True, timeout=10
            )
            os.unlink(temp_path)
            if process.returncode == 0:
                return True, ""
            error_msg = process.stderr.strip() or process.stdout.strip()
            return False, f"PHP syntax error: {error_msg}"
        except Exception:
            if os.path.exists(temp_path):
                os.unlink(temp_path)
            raise
    except FileNotFoundError:
        return False, "php not found. Install PHP to validate PHP code."
    except subprocess.TimeoutExpired:
        return False, "PHP validation timed out"
    except Exception as e:
        return False, f"Failed to validate PHP: {str(e)}"


def check_tool_exists_php(source_code: str, tool_name: str) -> bool:
    """Check if a tool exists in PHP source code."""
    patterns = [
        rf'function\s+{re.escape(tool_name)}\s*\(',
        rf'class\s+{re.escape(tool_name)}\s',
    ]
    return any(re.search(p, source_code) for p in patterns)


def inject_tool_into_php_file(server_name: str, tool_name: str, tool_code: str) -> Tuple[bool, str]:
    """Inject a new tool into a PHP MCP server."""
    try:
        source_code, source_path = read_source_file(server_name, max_chars=100000)
        if check_tool_exists_php(source_code, tool_name):
            return False, f"Tool '{tool_name}' already exists in {source_path}"
        is_valid, error_msg = validate_php_code(tool_code)
        if not is_valid:
            return False, f"Invalid PHP code: {error_msg}"
        backup_path = create_backup(source_path)
        with open(source_path, "a", encoding="utf-8") as f:
            f.write("\n\n")
            f.write(f"// Tool injected by universal-mcp-admin\n")
            f.write(tool_code)
            f.write("\n")
        return True, f"Tool '{tool_name}' injected successfully. Backup created at {backup_path}"
    except Exception as e:
        return False, f"Failed to inject tool: {str(e)}"


# ============================================================================
# Lua Language Handlers
# ============================================================================

def validate_lua_code(code: str) -> Tuple[bool, str]:
    """Validate Lua code using luac -p."""
    try:
        with tempfile.NamedTemporaryFile(mode='w', suffix='.lua', delete=False, encoding='utf-8') as f:
            f.write(code)
            temp_path = f.name
        try:
            process = subprocess.run(
                ["luac", "-p", temp_path],
                capture_output=True, text=True, timeout=10
            )
            os.unlink(temp_path)
            if process.returncode == 0:
                return True, ""
            error_msg = process.stderr.strip() or process.stdout.strip()
            return False, f"Lua syntax error: {error_msg}"
        except Exception:
            if os.path.exists(temp_path):
                os.unlink(temp_path)
            raise
    except FileNotFoundError:
        return False, "luac not found. Install Lua to validate Lua code."
    except subprocess.TimeoutExpired:
        return False, "Lua validation timed out"
    except Exception as e:
        return False, f"Failed to validate Lua: {str(e)}"


def check_tool_exists_lua(source_code: str, tool_name: str) -> bool:
    """Check if a tool exists in Lua source code."""
    patterns = [
        rf'function\s+{re.escape(tool_name)}\s*\(',
        rf'local\s+function\s+{re.escape(tool_name)}\s*\(',
        rf'{re.escape(tool_name)}\s*=\s*function\s*\(',
    ]
    return any(re.search(p, source_code) for p in patterns)


def inject_tool_into_lua_file(server_name: str, tool_name: str, tool_code: str) -> Tuple[bool, str]:
    """Inject a new tool into a Lua MCP server."""
    try:
        source_code, source_path = read_source_file(server_name, max_chars=100000)
        if check_tool_exists_lua(source_code, tool_name):
            return False, f"Tool '{tool_name}' already exists in {source_path}"
        is_valid, error_msg = validate_lua_code(tool_code)
        if not is_valid:
            return False, f"Invalid Lua code: {error_msg}"
        backup_path = create_backup(source_path)
        with open(source_path, "a", encoding="utf-8") as f:
            f.write("\n\n")
            f.write(f"-- Tool injected by universal-mcp-admin\n")
            f.write(tool_code)
            f.write("\n")
        return True, f"Tool '{tool_name}' injected successfully. Backup created at {backup_path}"
    except Exception as e:
        return False, f"Failed to inject tool: {str(e)}"


# ============================================================================
# Scala Language Handlers
# ============================================================================

def validate_scala_code(code: str) -> Tuple[bool, str]:
    """Validate Scala code using scalac."""
    try:
        with tempfile.NamedTemporaryFile(mode='w', suffix='.scala', delete=False, encoding='utf-8') as f:
            f.write(code)
            temp_path = f.name
        try:
            process = subprocess.run(
                ["scalac", temp_path],
                capture_output=True, text=True, timeout=30
            )
            os.unlink(temp_path)
            if process.returncode == 0:
                return True, ""
            error_msg = process.stderr.strip() or process.stdout.strip()
            return False, f"Scala syntax error: {error_msg}"
        except Exception:
            if os.path.exists(temp_path):
                os.unlink(temp_path)
            raise
    except FileNotFoundError:
        return False, "scalac not found. Install Scala to validate Scala code."
    except subprocess.TimeoutExpired:
        return False, "Scala validation timed out"
    except Exception as e:
        return False, f"Failed to validate Scala: {str(e)}"


def check_tool_exists_scala(source_code: str, tool_name: str) -> bool:
    """Check if a tool exists in Scala source code."""
    patterns = [
        rf'def\s+{re.escape(tool_name)}\s*[\(\[]',
        rf'class\s+{re.escape(tool_name)}\s',
        rf'object\s+{re.escape(tool_name)}\s',
        rf'val\s+{re.escape(tool_name)}\s*[=:]',
    ]
    return any(re.search(p, source_code) for p in patterns)


def inject_tool_into_scala_file(server_name: str, tool_name: str, tool_code: str) -> Tuple[bool, str]:
    """Inject a new tool into a Scala MCP server."""
    try:
        source_code, source_path = read_source_file(server_name, max_chars=100000)
        if check_tool_exists_scala(source_code, tool_name):
            return False, f"Tool '{tool_name}' already exists in {source_path}"
        is_valid, error_msg = validate_scala_code(tool_code)
        if not is_valid:
            return False, f"Invalid Scala code: {error_msg}"
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
# Elixir Language Handlers
# ============================================================================

def validate_elixir_code(code: str) -> Tuple[bool, str]:
    """Validate Elixir code using elixir compiler."""
    try:
        with tempfile.NamedTemporaryFile(mode='w', suffix='.exs', delete=False, encoding='utf-8') as f:
            f.write(code)
            temp_path = f.name
        try:
            process = subprocess.run(
                ["elixir", "-e", f"Code.compile_file(\"{temp_path}\")"],
                capture_output=True, text=True, timeout=15
            )
            os.unlink(temp_path)
            if process.returncode == 0:
                return True, ""
            error_msg = process.stderr.strip() or process.stdout.strip()
            return False, f"Elixir syntax error: {error_msg}"
        except Exception:
            if os.path.exists(temp_path):
                os.unlink(temp_path)
            raise
    except FileNotFoundError:
        return False, "elixir not found. Install Elixir to validate Elixir code."
    except subprocess.TimeoutExpired:
        return False, "Elixir validation timed out"
    except Exception as e:
        return False, f"Failed to validate Elixir: {str(e)}"


def check_tool_exists_elixir(source_code: str, tool_name: str) -> bool:
    """Check if a tool exists in Elixir source code."""
    patterns = [
        rf'def\s+{re.escape(tool_name)}\s*[\(,]',
        rf'def\s+{re.escape(tool_name)}\s+do',
        rf'defp\s+{re.escape(tool_name)}\s*[\(,]',
        rf'defmodule\s+{re.escape(tool_name)}\s',
    ]
    return any(re.search(p, source_code) for p in patterns)


def inject_tool_into_elixir_file(server_name: str, tool_name: str, tool_code: str) -> Tuple[bool, str]:
    """Inject a new tool into an Elixir MCP server."""
    try:
        source_code, source_path = read_source_file(server_name, max_chars=100000)
        if check_tool_exists_elixir(source_code, tool_name):
            return False, f"Tool '{tool_name}' already exists in {source_path}"
        is_valid, error_msg = validate_elixir_code(tool_code)
        if not is_valid:
            return False, f"Invalid Elixir code: {error_msg}"
        backup_path = create_backup(source_path)
        with open(source_path, "a", encoding="utf-8") as f:
            f.write("\n\n")
            f.write(f"# Tool injected by universal-mcp-admin\n")
            f.write(tool_code)
            f.write("\n")
        return True, f"Tool '{tool_name}' injected successfully. Backup created at {backup_path}. Note: Compilation required."
    except Exception as e:
        return False, f"Failed to inject tool: {str(e)}"


# ============================================================================
# Dart Language Handlers
# ============================================================================

def validate_dart_code(code: str) -> Tuple[bool, str]:
    """Validate Dart code using dart analyze."""
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            test_file = tmp_path / "tool.dart"
            test_file.write_text(code, encoding='utf-8')
            process = subprocess.run(
                ["dart", "analyze", "--no-fatal-infos", str(test_file)],
                capture_output=True, text=True, timeout=15, cwd=tmpdir
            )
            if process.returncode == 0:
                return True, ""
            error_msg = process.stderr.strip() or process.stdout.strip()
            return False, f"Dart syntax error: {error_msg}"
    except FileNotFoundError:
        return False, "dart not found. Install Dart SDK to validate Dart code."
    except subprocess.TimeoutExpired:
        return False, "Dart validation timed out"
    except Exception as e:
        return False, f"Failed to validate Dart: {str(e)}"


def check_tool_exists_dart(source_code: str, tool_name: str) -> bool:
    """Check if a tool exists in Dart source code."""
    patterns = [
        rf'\w+\s+{re.escape(tool_name)}\s*\(',
        rf'class\s+{re.escape(tool_name)}\s',
        rf'var\s+{re.escape(tool_name)}\s*=',
        rf'final\s+{re.escape(tool_name)}\s*=',
    ]
    return any(re.search(p, source_code) for p in patterns)


def inject_tool_into_dart_file(server_name: str, tool_name: str, tool_code: str) -> Tuple[bool, str]:
    """Inject a new tool into a Dart MCP server."""
    try:
        source_code, source_path = read_source_file(server_name, max_chars=100000)
        if check_tool_exists_dart(source_code, tool_name):
            return False, f"Tool '{tool_name}' already exists in {source_path}"
        is_valid, error_msg = validate_dart_code(tool_code)
        if not is_valid:
            return False, f"Invalid Dart code: {error_msg}"
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
# Haskell Language Handlers
# ============================================================================

def validate_haskell_code(code: str) -> Tuple[bool, str]:
    """Validate Haskell code using ghc -fno-code."""
    try:
        with tempfile.NamedTemporaryFile(mode='w', suffix='.hs', delete=False, encoding='utf-8') as f:
            f.write(code)
            temp_path = f.name
        try:
            process = subprocess.run(
                ["ghc", "-fno-code", temp_path],
                capture_output=True, text=True, timeout=15
            )
            os.unlink(temp_path)
            if process.returncode == 0:
                return True, ""
            error_msg = process.stderr.strip() or process.stdout.strip()
            return False, f"Haskell syntax error: {error_msg}"
        except Exception:
            if os.path.exists(temp_path):
                os.unlink(temp_path)
            raise
    except FileNotFoundError:
        return False, "ghc not found. Install GHC to validate Haskell code."
    except subprocess.TimeoutExpired:
        return False, "Haskell validation timed out"
    except Exception as e:
        return False, f"Failed to validate Haskell: {str(e)}"


def check_tool_exists_haskell(source_code: str, tool_name: str) -> bool:
    """Check if a tool exists in Haskell source code."""
    patterns = [
        rf'^{re.escape(tool_name)}\s+::\s+',  # type signature
        rf'^{re.escape(tool_name)}\s+',  # definition
    ]
    return any(re.search(p, source_code, re.MULTILINE) for p in patterns)


def inject_tool_into_haskell_file(server_name: str, tool_name: str, tool_code: str) -> Tuple[bool, str]:
    """Inject a new tool into a Haskell MCP server."""
    try:
        source_code, source_path = read_source_file(server_name, max_chars=100000)
        if check_tool_exists_haskell(source_code, tool_name):
            return False, f"Tool '{tool_name}' already exists in {source_path}"
        is_valid, error_msg = validate_haskell_code(tool_code)
        if not is_valid:
            return False, f"Invalid Haskell code: {error_msg}"
        backup_path = create_backup(source_path)
        with open(source_path, "a", encoding="utf-8") as f:
            f.write("\n\n")
            f.write(f"-- Tool injected by universal-mcp-admin\n")
            f.write(tool_code)
            f.write("\n")
        return True, f"Tool '{tool_name}' injected successfully. Backup created at {backup_path}. Note: Compilation required."
    except Exception as e:
        return False, f"Failed to inject tool: {str(e)}"


# ============================================================================
# OCaml Language Handlers
# ============================================================================

def validate_ocaml_code(code: str) -> Tuple[bool, str]:
    """Validate OCaml code using ocamlfind or ocamlc."""
    try:
        with tempfile.NamedTemporaryFile(mode='w', suffix='.ml', delete=False, encoding='utf-8') as f:
            f.write(code)
            temp_path = f.name
        try:
            process = subprocess.run(
                ["ocamlc", "-c", temp_path],
                capture_output=True, text=True, timeout=15
            )
            os.unlink(temp_path)
            # Clean up .cmo/.cmi files
            for ext in ('.cmo', '.cmi'):
                p = Path(temp_path).with_suffix(ext)
                if p.exists():
                    p.unlink()
            if process.returncode == 0:
                return True, ""
            error_msg = process.stderr.strip() or process.stdout.strip()
            return False, f"OCaml syntax error: {error_msg}"
        except Exception:
            if os.path.exists(temp_path):
                os.unlink(temp_path)
            raise
    except FileNotFoundError:
        return False, "ocamlc not found. Install OCaml to validate OCaml code."
    except subprocess.TimeoutExpired:
        return False, "OCaml validation timed out"
    except Exception as e:
        return False, f"Failed to validate OCaml: {str(e)}"


def check_tool_exists_ocaml(source_code: str, tool_name: str) -> bool:
    """Check if a tool exists in OCaml source code."""
    patterns = [
        rf'let\s+{re.escape(tool_name)}\s',
        rf'module\s+{re.escape(tool_name)}\s',
        rf'val\s+{re.escape(tool_name)}\s*:',
    ]
    return any(re.search(p, source_code) for p in patterns)


def inject_tool_into_ocaml_file(server_name: str, tool_name: str, tool_code: str) -> Tuple[bool, str]:
    """Inject a new tool into an OCaml MCP server."""
    try:
        source_code, source_path = read_source_file(server_name, max_chars=100000)
        if check_tool_exists_ocaml(source_code, tool_name):
            return False, f"Tool '{tool_name}' already exists in {source_path}"
        is_valid, error_msg = validate_ocaml_code(tool_code)
        if not is_valid:
            return False, f"Invalid OCaml code: {error_msg}"
        backup_path = create_backup(source_path)
        with open(source_path, "a", encoding="utf-8") as f:
            f.write("\n\n")
            f.write(f"(* Tool injected by universal-mcp-admin *)\n")
            f.write(tool_code)
            f.write("\n")
        return True, f"Tool '{tool_name}' injected successfully. Backup created at {backup_path}. Note: Compilation required."
    except Exception as e:
        return False, f"Failed to inject tool: {str(e)}"


# ============================================================================
# Nim Language Handlers
# ============================================================================

def validate_nim_code(code: str) -> Tuple[bool, str]:
    """Validate Nim code using nim check."""
    try:
        with tempfile.NamedTemporaryFile(mode='w', suffix='.nim', delete=False, encoding='utf-8') as f:
            f.write(code)
            temp_path = f.name
        try:
            process = subprocess.run(
                ["nim", "check", temp_path],
                capture_output=True, text=True, timeout=15
            )
            os.unlink(temp_path)
            if process.returncode == 0:
                return True, ""
            error_msg = process.stderr.strip() or process.stdout.strip()
            return False, f"Nim syntax error: {error_msg}"
        except Exception:
            if os.path.exists(temp_path):
                os.unlink(temp_path)
            raise
    except FileNotFoundError:
        return False, "nim not found. Install Nim to validate Nim code."
    except subprocess.TimeoutExpired:
        return False, "Nim validation timed out"
    except Exception as e:
        return False, f"Failed to validate Nim: {str(e)}"


def check_tool_exists_nim(source_code: str, tool_name: str) -> bool:
    """Check if a tool exists in Nim source code."""
    patterns = [
        rf'proc\s+{re.escape(tool_name)}\s*[\(\*]',
        rf'func\s+{re.escape(tool_name)}\s*[\(\*]',
        rf'type\s+{re.escape(tool_name)}\s',
    ]
    return any(re.search(p, source_code) for p in patterns)


def inject_tool_into_nim_file(server_name: str, tool_name: str, tool_code: str) -> Tuple[bool, str]:
    """Inject a new tool into a Nim MCP server."""
    try:
        source_code, source_path = read_source_file(server_name, max_chars=100000)
        if check_tool_exists_nim(source_code, tool_name):
            return False, f"Tool '{tool_name}' already exists in {source_path}"
        is_valid, error_msg = validate_nim_code(tool_code)
        if not is_valid:
            return False, f"Invalid Nim code: {error_msg}"
        backup_path = create_backup(source_path)
        with open(source_path, "a", encoding="utf-8") as f:
            f.write("\n\n")
            f.write(f"# Tool injected by universal-mcp-admin\n")
            f.write(tool_code)
            f.write("\n")
        return True, f"Tool '{tool_name}' injected successfully. Backup created at {backup_path}. Note: Compilation required."
    except Exception as e:
        return False, f"Failed to inject tool: {str(e)}"


# ============================================================================
# D Language Handlers
# ============================================================================

def validate_d_code(code: str) -> Tuple[bool, str]:
    """Validate D code using dmd."""
    try:
        with tempfile.NamedTemporaryFile(mode='w', suffix='.d', delete=False, encoding='utf-8') as f:
            f.write(code)
            temp_path = f.name
        try:
            process = subprocess.run(
                ["dmd", "-o-", temp_path],
                capture_output=True, text=True, timeout=15
            )
            os.unlink(temp_path)
            if process.returncode == 0:
                return True, ""
            error_msg = process.stderr.strip() or process.stdout.strip()
            return False, f"D syntax error: {error_msg}"
        except Exception:
            if os.path.exists(temp_path):
                os.unlink(temp_path)
            raise
    except FileNotFoundError:
        return False, "dmd not found. Install D compiler to validate D code."
    except subprocess.TimeoutExpired:
        return False, "D validation timed out"
    except Exception as e:
        return False, f"Failed to validate D: {str(e)}"


def check_tool_exists_d(source_code: str, tool_name: str) -> bool:
    """Check if a tool exists in D source code."""
    patterns = [
        rf'\w+\s+{re.escape(tool_name)}\s*\(',
        rf'class\s+{re.escape(tool_name)}\s',
        rf'struct\s+{re.escape(tool_name)}\s',
    ]
    return any(re.search(p, source_code) for p in patterns)


def inject_tool_into_d_file(server_name: str, tool_name: str, tool_code: str) -> Tuple[bool, str]:
    """Inject a new tool into a D MCP server."""
    try:
        source_code, source_path = read_source_file(server_name, max_chars=100000)
        if check_tool_exists_d(source_code, tool_name):
            return False, f"Tool '{tool_name}' already exists in {source_path}"
        is_valid, error_msg = validate_d_code(tool_code)
        if not is_valid:
            return False, f"Invalid D code: {error_msg}"
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
# Crystal Language Handlers
# ============================================================================

def validate_crystal_code(code: str) -> Tuple[bool, str]:
    """Validate Crystal code using crystal tool format --check."""
    try:
        with tempfile.NamedTemporaryFile(mode='w', suffix='.cr', delete=False, encoding='utf-8') as f:
            f.write(code)
            temp_path = f.name
        try:
            process = subprocess.run(
                ["crystal", "tool", "format", "--check", temp_path],
                capture_output=True, text=True, timeout=15
            )
            os.unlink(temp_path)
            if process.returncode == 0:
                return True, ""
            error_msg = process.stderr.strip() or process.stdout.strip()
            return False, f"Crystal syntax error: {error_msg}"
        except Exception:
            if os.path.exists(temp_path):
                os.unlink(temp_path)
            raise
    except FileNotFoundError:
        return False, "crystal not found. Install Crystal to validate Crystal code."
    except subprocess.TimeoutExpired:
        return False, "Crystal validation timed out"
    except Exception as e:
        return False, f"Failed to validate Crystal: {str(e)}"


def check_tool_exists_crystal(source_code: str, tool_name: str) -> bool:
    """Check if a tool exists in Crystal source code."""
    patterns = [
        rf'def\s+{re.escape(tool_name)}\s*[\((\n]',
        rf'class\s+{re.escape(tool_name)}\s',
        rf'module\s+{re.escape(tool_name)}\s',
    ]
    return any(re.search(p, source_code) for p in patterns)


def inject_tool_into_crystal_file(server_name: str, tool_name: str, tool_code: str) -> Tuple[bool, str]:
    """Inject a new tool into a Crystal MCP server."""
    try:
        source_code, source_path = read_source_file(server_name, max_chars=100000)
        if check_tool_exists_crystal(source_code, tool_name):
            return False, f"Tool '{tool_name}' already exists in {source_path}"
        is_valid, error_msg = validate_crystal_code(tool_code)
        if not is_valid:
            return False, f"Invalid Crystal code: {error_msg}"
        backup_path = create_backup(source_path)
        with open(source_path, "a", encoding="utf-8") as f:
            f.write("\n\n")
            f.write(f"# Tool injected by universal-mcp-admin\n")
            f.write(tool_code)
            f.write("\n")
        return True, f"Tool '{tool_name}' injected successfully. Backup created at {backup_path}. Note: Compilation required."
    except Exception as e:
        return False, f"Failed to inject tool: {str(e)}"


# ============================================================================
# Raku Language Handlers
# ============================================================================

def validate_raku_code(code: str) -> Tuple[bool, str]:
    """Validate Raku code using raku -c."""
    try:
        with tempfile.NamedTemporaryFile(mode='w', suffix='.raku', delete=False, encoding='utf-8') as f:
            f.write(code)
            temp_path = f.name
        try:
            process = subprocess.run(
                ["raku", "-c", temp_path],
                capture_output=True, text=True, timeout=15
            )
            os.unlink(temp_path)
            if process.returncode == 0:
                return True, ""
            error_msg = process.stderr.strip() or process.stdout.strip()
            return False, f"Raku syntax error: {error_msg}"
        except Exception:
            if os.path.exists(temp_path):
                os.unlink(temp_path)
            raise
    except FileNotFoundError:
        return False, "raku not found. Install Raku to validate Raku code."
    except subprocess.TimeoutExpired:
        return False, "Raku validation timed out"
    except Exception as e:
        return False, f"Failed to validate Raku: {str(e)}"


def check_tool_exists_raku(source_code: str, tool_name: str) -> bool:
    """Check if a tool exists in Raku source code."""
    patterns = [
        rf'sub\s+{re.escape(tool_name)}\s*[\((\s]',
        rf'method\s+{re.escape(tool_name)}\s*[\((\s]',
        rf'class\s+{re.escape(tool_name)}\s',
        rf'module\s+{re.escape(tool_name)}\s',
    ]
    return any(re.search(p, source_code) for p in patterns)


def inject_tool_into_raku_file(server_name: str, tool_name: str, tool_code: str) -> Tuple[bool, str]:
    """Inject a new tool into a Raku MCP server."""
    try:
        source_code, source_path = read_source_file(server_name, max_chars=100000)
        if check_tool_exists_raku(source_code, tool_name):
            return False, f"Tool '{tool_name}' already exists in {source_path}"
        is_valid, error_msg = validate_raku_code(tool_code)
        if not is_valid:
            return False, f"Invalid Raku code: {error_msg}"
        backup_path = create_backup(source_path)
        with open(source_path, "a", encoding="utf-8") as f:
            f.write("\n\n")
            f.write(f"# Tool injected by universal-mcp-admin\n")
            f.write(tool_code)
            f.write("\n")
        return True, f"Tool '{tool_name}' injected successfully. Backup created at {backup_path}"
    except Exception as e:
        return False, f"Failed to inject tool: {str(e)}"


# ============================================================================
# Julia Language Handlers
# ============================================================================

def validate_julia_code(code: str) -> Tuple[bool, str]:
    """Validate Julia code using julia --startup-file=no."""
    try:
        with tempfile.NamedTemporaryFile(mode='w', suffix='.jl', delete=False, encoding='utf-8') as f:
            f.write(code)
            temp_path = f.name
        try:
            process = subprocess.run(
                ["julia", "--startup-file=no", "-e", f'include("{temp_path}")'],
                capture_output=True, text=True, timeout=30
            )
            os.unlink(temp_path)
            if process.returncode == 0:
                return True, ""
            error_msg = process.stderr.strip() or process.stdout.strip()
            return False, f"Julia syntax error: {error_msg}"
        except Exception:
            if os.path.exists(temp_path):
                os.unlink(temp_path)
            raise
    except FileNotFoundError:
        return False, "julia not found. Install Julia to validate Julia code."
    except subprocess.TimeoutExpired:
        return False, "Julia validation timed out"
    except Exception as e:
        return False, f"Failed to validate Julia: {str(e)}"


def check_tool_exists_julia(source_code: str, tool_name: str) -> bool:
    """Check if a tool exists in Julia source code."""
    patterns = [
        rf'function\s+{re.escape(tool_name)}\s*[\((\n]',
        rf'{re.escape(tool_name)}\s*\([^)]*\)\s*=',  # short-form
        rf'struct\s+{re.escape(tool_name)}\s',
        rf'module\s+{re.escape(tool_name)}\s',
    ]
    return any(re.search(p, source_code) for p in patterns)


def inject_tool_into_julia_file(server_name: str, tool_name: str, tool_code: str) -> Tuple[bool, str]:
    """Inject a new tool into a Julia MCP server."""
    try:
        source_code, source_path = read_source_file(server_name, max_chars=100000)
        if check_tool_exists_julia(source_code, tool_name):
            return False, f"Tool '{tool_name}' already exists in {source_path}"
        is_valid, error_msg = validate_julia_code(tool_code)
        if not is_valid:
            return False, f"Invalid Julia code: {error_msg}"
        backup_path = create_backup(source_path)
        with open(source_path, "a", encoding="utf-8") as f:
            f.write("\n\n")
            f.write(f"# Tool injected by universal-mcp-admin\n")
            f.write(tool_code)
            f.write("\n")
        return True, f"Tool '{tool_name}' injected successfully. Backup created at {backup_path}"
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
        'comment_prefix': '/*'
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
    },
    '.zig': {
        'validate': validate_zig_code,
        'check_tool_exists': check_tool_exists_zig,
        'inject': inject_tool_into_zig_file,
        'needs_compilation': True,
        'comment_prefix': '//'
    },
    '.java': {
        'validate': validate_java_code,
        'check_tool_exists': check_tool_exists_java,
        'inject': inject_tool_into_java_file,
        'needs_compilation': True,
        'comment_prefix': '//'
    },
    '.rb': {
        'validate': validate_ruby_code,
        'check_tool_exists': check_tool_exists_ruby,
        'inject': inject_tool_into_ruby_file,
        'needs_compilation': False,
        'comment_prefix': '#'
    },
    '.kt': {
        'validate': validate_kotlin_code,
        'check_tool_exists': check_tool_exists_kotlin,
        'inject': inject_tool_into_kotlin_file,
        'needs_compilation': True,
        'comment_prefix': '//'
    },
    '.kts': {
        'validate': validate_kotlin_code,
        'check_tool_exists': check_tool_exists_kotlin,
        'inject': inject_tool_into_kotlin_file,
        'needs_compilation': True,
        'comment_prefix': '//'
    },
    '.swift': {
        'validate': validate_swift_code,
        'check_tool_exists': check_tool_exists_swift,
        'inject': inject_tool_into_swift_file,
        'needs_compilation': True,
        'comment_prefix': '//'
    },
    '.cs': {
        'validate': validate_csharp_code,
        'check_tool_exists': check_tool_exists_csharp,
        'inject': inject_tool_into_csharp_file,
        'needs_compilation': True,
        'comment_prefix': '//'
    },
    '.php': {
        'validate': validate_php_code,
        'check_tool_exists': check_tool_exists_php,
        'inject': inject_tool_into_php_file,
        'needs_compilation': False,
        'comment_prefix': '//'
    },
    '.lua': {
        'validate': validate_lua_code,
        'check_tool_exists': check_tool_exists_lua,
        'inject': inject_tool_into_lua_file,
        'needs_compilation': False,
        'comment_prefix': '--'
    },
    '.scala': {
        'validate': validate_scala_code,
        'check_tool_exists': check_tool_exists_scala,
        'inject': inject_tool_into_scala_file,
        'needs_compilation': True,
        'comment_prefix': '//'
    },
    '.ex': {
        'validate': validate_elixir_code,
        'check_tool_exists': check_tool_exists_elixir,
        'inject': inject_tool_into_elixir_file,
        'needs_compilation': True,
        'comment_prefix': '#'
    },
    '.exs': {
        'validate': validate_elixir_code,
        'check_tool_exists': check_tool_exists_elixir,
        'inject': inject_tool_into_elixir_file,
        'needs_compilation': True,
        'comment_prefix': '#'
    },
    '.dart': {
        'validate': validate_dart_code,
        'check_tool_exists': check_tool_exists_dart,
        'inject': inject_tool_into_dart_file,
        'needs_compilation': True,
        'comment_prefix': '//'
    },
    '.hs': {
        'validate': validate_haskell_code,
        'check_tool_exists': check_tool_exists_haskell,
        'inject': inject_tool_into_haskell_file,
        'needs_compilation': True,
        'comment_prefix': '--'
    },
    '.ml': {
        'validate': validate_ocaml_code,
        'check_tool_exists': check_tool_exists_ocaml,
        'inject': inject_tool_into_ocaml_file,
        'needs_compilation': True,
        'comment_prefix': '(*'
    },
    '.mli': {
        'validate': validate_ocaml_code,
        'check_tool_exists': check_tool_exists_ocaml,
        'inject': inject_tool_into_ocaml_file,
        'needs_compilation': True,
        'comment_prefix': '(*'
    },
    '.nim': {
        'validate': validate_nim_code,
        'check_tool_exists': check_tool_exists_nim,
        'inject': inject_tool_into_nim_file,
        'needs_compilation': True,
        'comment_prefix': '#'
    },
    '.d': {
        'validate': validate_d_code,
        'check_tool_exists': check_tool_exists_d,
        'inject': inject_tool_into_d_file,
        'needs_compilation': True,
        'comment_prefix': '//'
    },
    '.cr': {
        'validate': validate_crystal_code,
        'check_tool_exists': check_tool_exists_crystal,
        'inject': inject_tool_into_crystal_file,
        'needs_compilation': True,
        'comment_prefix': '#'
    },
    '.raku': {
        'validate': validate_raku_code,
        'check_tool_exists': check_tool_exists_raku,
        'inject': inject_tool_into_raku_file,
        'needs_compilation': False,
        'comment_prefix': '#'
    },
    '.rakumod': {
        'validate': validate_raku_code,
        'check_tool_exists': check_tool_exists_raku,
        'inject': inject_tool_into_raku_file,
        'needs_compilation': False,
        'comment_prefix': '#'
    },
    '.pm6': {
        'validate': validate_raku_code,
        'check_tool_exists': check_tool_exists_raku,
        'inject': inject_tool_into_raku_file,
        'needs_compilation': False,
        'comment_prefix': '#'
    },
    '.jl': {
        'validate': validate_julia_code,
        'check_tool_exists': check_tool_exists_julia,
        'inject': inject_tool_into_julia_file,
        'needs_compilation': False,
        'comment_prefix': '#'
    }
}


def inject_tool_generic(
    server_name: str,
    tool_name: str,
    tool_code: str,
    auto_import: bool = False,
) -> Tuple[bool, str]:
    """
    Generic tool injection that routes to language-specific handlers.
    Optionally auto-injects missing imports.
    
    Args:
        server_name: Name of the server to modify
        tool_name: Name of the tool to inject
        tool_code: Code for the tool
        auto_import: If True, automatically inject missing imports
        
    Returns:
        Tuple of (success, message)
    """
    try:
        source_path = find_server_source_file(server_name)
        extension = source_path.suffix
        
        if extension not in LANGUAGE_HANDLERS:
            return False, f"Unsupported language: {extension}. Supported: {', '.join(LANGUAGE_HANDLERS.keys())}"
        
        # Auto-import handling
        import_message = ""
        if auto_import:
            try:
                from import_manager import check_missing_imports, inject_imports
                source_code, _ = read_source_file(server_name, max_chars=200000)
                missing = check_missing_imports(source_code, tool_code, extension)
                if missing:
                    new_source = inject_imports(source_code, missing, extension)
                    with open(source_path, 'w', encoding='utf-8') as f:
                        f.write(new_source)
                    import_message = f" Auto-injected imports: {', '.join(missing)}."
            except Exception as e:
                import_message = f" Import auto-injection failed: {e}."
        
        handler = LANGUAGE_HANDLERS[extension]
        success, message = handler['inject'](server_name, tool_name, tool_code)
        
        # Register backup with BackupManager
        if success:
            try:
                from backup_manager import get_backup_manager
                bm = get_backup_manager()
                backup_path = source_path.with_suffix(source_path.suffix + ".bak")
                if backup_path.exists():
                    bm.register_backup(
                        file_path=str(source_path),
                        backup_path=str(backup_path),
                        operation="inject_tool",
                        server_name=server_name,
                        tool_name=tool_name,
                    )
            except Exception:
                pass
        
        return success, message + import_message
    except Exception as e:
        return False, f"Failed to inject tool: {str(e)}"


# ============================================================================
# Tool Removal and Modification
# ============================================================================

def find_tool_in_source(
    source_code: str, tool_name: str, language: str
) -> Optional[Tuple[int, int, str]]:
    """
    Locate a tool definition in source code.
    Returns (start_line, end_line, full_definition) or None if not found.
    Lines are 0-indexed.
    """
    lines = source_code.splitlines()

    if language == '.py':
        return _find_python_tool(lines, tool_name)
    elif language in ('.js', '.ts'):
        return _find_js_tool(lines, tool_name)
    elif language == '.rs':
        return _find_brace_tool(lines, tool_name, r'(?:pub\s+)?(?:async\s+)?fn\s+' + re.escape(tool_name) + r'\s*\(')
    elif language in ('.c', '.cpp', '.cc', '.cxx'):
        return _find_brace_tool(lines, tool_name, r'(?:\w+\s+)+' + re.escape(tool_name) + r'\s*\(')
    elif language == '.go':
        return _find_brace_tool(lines, tool_name, r'func\s+(?:\([^)]*\)\s+)?' + re.escape(tool_name) + r'\s*\(')
    elif language == '.zig':
        return _find_brace_tool(lines, tool_name, r'(?:pub\s+)?fn\s+' + re.escape(tool_name) + r'\s*\(')
    elif language == '.java':
        return _find_brace_tool(lines, tool_name, r'(?:(?:public|private|protected)\s+)?(?:static\s+)?(?:\w+\s+)' + re.escape(tool_name) + r'\s*\(')
    elif language == '.rb':
        return _find_ruby_tool(lines, tool_name)
    elif language in ('.kt', '.kts'):
        return _find_brace_tool(lines, tool_name, r'fun\s+' + re.escape(tool_name) + r'\s*\(')
    elif language == '.swift':
        return _find_brace_tool(lines, tool_name, r'func\s+' + re.escape(tool_name) + r'\s*\(')
    elif language == '.cs':
        return _find_brace_tool(lines, tool_name, r'(?:(?:public|private|protected|internal)\s+)?(?:static\s+)?(?:\w+\s+)' + re.escape(tool_name) + r'\s*\(')
    elif language == '.php':
        return _find_brace_tool(lines, tool_name, r'function\s+' + re.escape(tool_name) + r'\s*\(')
    elif language == '.lua':
        return _find_lua_tool(lines, tool_name)
    elif language == '.scala':
        return _find_brace_tool(lines, tool_name, r'def\s+' + re.escape(tool_name) + r'\s*[\(\[]')
    elif language in ('.ex', '.exs'):
        return _find_elixir_tool(lines, tool_name)
    elif language == '.dart':
        return _find_brace_tool(lines, tool_name, r'\w+\s+' + re.escape(tool_name) + r'\s*\(')
    elif language == '.hs':
        return _find_haskell_tool(lines, tool_name)
    elif language in ('.ml', '.mli'):
        return _find_ocaml_tool(lines, tool_name)
    elif language == '.nim':
        return _find_nim_tool(lines, tool_name)
    elif language == '.d':
        return _find_brace_tool(lines, tool_name, r'\w+\s+' + re.escape(tool_name) + r'\s*\(')
    elif language == '.cr':
        return _find_ruby_tool(lines, tool_name)  # Crystal uses same def/end syntax
    elif language in ('.raku', '.rakumod', '.pm6'):
        return _find_brace_tool(lines, tool_name, r'(?:sub|method)\s+' + re.escape(tool_name) + r'\s*[\(\s]')
    elif language == '.jl':
        return _find_julia_tool(lines, tool_name)
    return None


def _find_python_tool(lines: list, tool_name: str) -> Optional[Tuple[int, int, str]]:
    """Find a Python function definition, including decorators."""
    func_pattern = re.compile(rf'def\s+{re.escape(tool_name)}\s*\(')
    for i, line in enumerate(lines):
        if func_pattern.search(line):
            # Walk backwards for decorators
            start = i
            while start > 0 and lines[start - 1].strip().startswith('@'):
                start -= 1
            # Also capture preceding comment block
            while start > 0 and lines[start - 1].strip().startswith('#'):
                start -= 1

            # Walk forward to find the end of the function
            indent = len(line) - len(line.lstrip())
            end = i + 1
            while end < len(lines):
                l = lines[end]
                if l.strip() == '':
                    end += 1
                    continue
                current_indent = len(l) - len(l.lstrip())
                if current_indent <= indent and l.strip():
                    break
                end += 1
            # Trim trailing blank lines
            while end > i + 1 and not lines[end - 1].strip():
                end -= 1
            return start, end, '\n'.join(lines[start:end])
    return None


def _find_js_tool(lines: list, tool_name: str) -> Optional[Tuple[int, int, str]]:
    """Find a JavaScript/TypeScript function or tool definition."""
    patterns = [
        re.compile(rf'(?:export\s+)?(?:async\s+)?function\s+{re.escape(tool_name)}\s*\('),
        re.compile(rf'(?:const|let|var)\s+{re.escape(tool_name)}\s*='),
    ]
    for pat in patterns:
        for i, line in enumerate(lines):
            if pat.search(line):
                start = i
                # Check for preceding comments
                while start > 0 and (lines[start - 1].strip().startswith('//') or lines[start - 1].strip().startswith('/*')):
                    start -= 1
                # Find matching brace end
                end = _find_brace_end(lines, i)
                return start, end, '\n'.join(lines[start:end])
    return None


def _find_brace_tool(lines: list, tool_name: str, pattern_str: str) -> Optional[Tuple[int, int, str]]:
    """Find a brace-delimited function definition (Rust, C, C++, Go)."""
    pat = re.compile(pattern_str)
    for i, line in enumerate(lines):
        if pat.search(line):
            start = i
            # Check for preceding comments/attributes
            while start > 0:
                prev = lines[start - 1].strip()
                if prev.startswith('//') or prev.startswith('#[') or prev.startswith('/*') or prev.startswith('///'):
                    start -= 1
                else:
                    break
            end = _find_brace_end(lines, i)
            return start, end, '\n'.join(lines[start:end])
    return None


def _find_ruby_tool(lines: list, tool_name: str) -> Optional[Tuple[int, int, str]]:
    """Find a Ruby method definition (uses def/end blocks)."""
    func_pattern = re.compile(rf'def\s+(?:self\.)?{re.escape(tool_name)}\s*[\((\n]')
    for i, line in enumerate(lines):
        if func_pattern.search(line):
            start = i
            # Walk backwards for preceding comments
            while start > 0 and lines[start - 1].strip().startswith('#'):
                start -= 1

            # Walk forward to find matching 'end'
            indent = len(line) - len(line.lstrip())
            end = i + 1
            while end < len(lines):
                l = lines[end]
                stripped = l.strip()
                if stripped == 'end':
                    current_indent = len(l) - len(l.lstrip())
                    if current_indent <= indent:
                        end += 1  # Include the 'end' line
                        break
                end += 1
            return start, end, '\n'.join(lines[start:end])
    return None


def _find_lua_tool(lines: list, tool_name: str) -> Optional[Tuple[int, int, str]]:
    """Find a Lua function definition (uses function/end blocks)."""
    patterns = [
        re.compile(rf'function\s+{re.escape(tool_name)}\s*\('),
        re.compile(rf'local\s+function\s+{re.escape(tool_name)}\s*\('),
    ]
    for pat in patterns:
        for i, line in enumerate(lines):
            if pat.search(line):
                start = i
                while start > 0 and lines[start - 1].strip().startswith('--'):
                    start -= 1
                end = i + 1
                depth = 1
                while end < len(lines) and depth > 0:
                    stripped = lines[end].strip()
                    # Count block openers/closers
                    for keyword in ['function', 'if', 'for', 'while', 'repeat']:
                        if re.match(rf'\b{keyword}\b', stripped):
                            depth += 1
                    if stripped == 'end' or stripped.startswith('end ') or stripped.startswith('end)'):
                        depth -= 1
                    end += 1
                return start, end, '\n'.join(lines[start:end])
    return None


def _find_elixir_tool(lines: list, tool_name: str) -> Optional[Tuple[int, int, str]]:
    """Find an Elixir function definition (uses def/end blocks)."""
    func_pattern = re.compile(rf'def[p]?\s+{re.escape(tool_name)}\s*[\(,\s]')
    for i, line in enumerate(lines):
        if func_pattern.search(line):
            start = i
            while start > 0 and lines[start - 1].strip().startswith('#'):
                start -= 1
            while start > 0 and lines[start - 1].strip().startswith('@'):
                start -= 1
            end = i + 1
            depth = 1
            while end < len(lines) and depth > 0:
                stripped = lines[end].strip()
                for keyword in ['def ', 'defp ', 'defmodule ', 'if ', 'case ', 'cond ', 'fn ']:
                    if stripped.startswith(keyword):
                        depth += 1
                        break
                if stripped == 'end' or stripped.startswith('end)'):
                    depth -= 1
                end += 1
            return start, end, '\n'.join(lines[start:end])
    return None


def _find_haskell_tool(lines: list, tool_name: str) -> Optional[Tuple[int, int, str]]:
    """Find a Haskell function definition."""
    sig_pattern = re.compile(rf'^{re.escape(tool_name)}\s+::')
    def_pattern = re.compile(rf'^{re.escape(tool_name)}\s+')
    for i, line in enumerate(lines):
        if sig_pattern.match(line) or def_pattern.match(line):
            start = i
            while start > 0 and lines[start - 1].strip().startswith('--'):
                start -= 1
            end = i + 1
            while end < len(lines):
                l = lines[end]
                if l.strip() == '' or (l[0:1] != ' ' and l[0:1] != '\t' and not l.startswith(tool_name)):
                    break
                end += 1
            while end > i + 1 and not lines[end - 1].strip():
                end -= 1
            return start, end, '\n'.join(lines[start:end])
    return None


def _find_ocaml_tool(lines: list, tool_name: str) -> Optional[Tuple[int, int, str]]:
    """Find an OCaml let binding."""
    let_pattern = re.compile(rf'let\s+{re.escape(tool_name)}\s')
    for i, line in enumerate(lines):
        if let_pattern.search(line):
            start = i
            while start > 0 and lines[start - 1].strip().startswith('(*'):
                start -= 1
            end = i + 1
            while end < len(lines):
                l = lines[end].strip()
                if l == '' or (l.startswith('let ') and not l.startswith('let ' + tool_name)):
                    break
                end += 1
            while end > i + 1 and not lines[end - 1].strip():
                end -= 1
            return start, end, '\n'.join(lines[start:end])
    return None


def _find_nim_tool(lines: list, tool_name: str) -> Optional[Tuple[int, int, str]]:
    """Find a Nim proc/func definition (indentation-based)."""
    proc_pattern = re.compile(rf'(?:proc|func)\s+{re.escape(tool_name)}\s*[\(\*]')
    for i, line in enumerate(lines):
        if proc_pattern.search(line):
            start = i
            while start > 0 and lines[start - 1].strip().startswith('#'):
                start -= 1
            indent = len(line) - len(line.lstrip())
            end = i + 1
            while end < len(lines):
                l = lines[end]
                if l.strip() == '':
                    end += 1
                    continue
                current_indent = len(l) - len(l.lstrip())
                if current_indent <= indent and l.strip():
                    break
                end += 1
            while end > i + 1 and not lines[end - 1].strip():
                end -= 1
            return start, end, '\n'.join(lines[start:end])
    return None


def _find_julia_tool(lines: list, tool_name: str) -> Optional[Tuple[int, int, str]]:
    """Find a Julia function definition (uses function/end blocks)."""
    func_pattern = re.compile(rf'function\s+{re.escape(tool_name)}\s*[\((\n]')
    for i, line in enumerate(lines):
        if func_pattern.search(line):
            start = i
            while start > 0 and lines[start - 1].strip().startswith('#'):
                start -= 1
            end = i + 1
            depth = 1
            while end < len(lines) and depth > 0:
                stripped = lines[end].strip()
                for keyword in ['function ', 'if ', 'for ', 'while ', 'begin', 'let ', 'try']:
                    if stripped.startswith(keyword):
                        depth += 1
                        break
                if stripped == 'end' or stripped.startswith('end ') or stripped.startswith('end#'):
                    depth -= 1
                end += 1
            return start, end, '\n'.join(lines[start:end])
    return None


def _find_brace_end(lines: list, start_line: int) -> int:
    """Find the end of a brace-delimited block starting from start_line."""
    depth = 0
    found_open = False
    for i in range(start_line, len(lines)):
        for ch in lines[i]:
            if ch == '{':
                depth += 1
                found_open = True
            elif ch == '}':
                depth -= 1
                if found_open and depth == 0:
                    return i + 1
    return len(lines)


def remove_tool_from_source(
    source_code: str, tool_name: str, language: str
) -> Tuple[bool, str, str]:
    """
    Remove a tool definition from source code.
    Returns (success, message, modified_source).
    """
    result = find_tool_in_source(source_code, tool_name, language)
    if result is None:
        return False, f"Tool '{tool_name}' not found in source", source_code

    start, end, _ = result
    lines = source_code.splitlines()
    new_lines = lines[:start] + lines[end:]

    # Clean up extra blank lines
    modified = '\n'.join(new_lines)
    while '\n\n\n\n' in modified:
        modified = modified.replace('\n\n\n\n', '\n\n\n')

    # Validate
    if language == '.py':
        is_valid, err = validate_python_code(modified)
        if not is_valid:
            return False, f"Removing tool would break syntax: {err}", source_code

    return True, f"Tool '{tool_name}' removed (lines {start+1}-{end})", modified


def replace_tool_in_source(
    source_code: str, tool_name: str, new_code: str, language: str
) -> Tuple[bool, str, str]:
    """
    Replace a tool definition with new code.
    Returns (success, message, modified_source).
    """
    result = find_tool_in_source(source_code, tool_name, language)
    if result is None:
        return False, f"Tool '{tool_name}' not found in source", source_code

    start, end, _ = result
    lines = source_code.splitlines()
    new_lines = lines[:start] + new_code.splitlines() + lines[end:]
    modified = '\n'.join(new_lines)

    # Validate
    if language == '.py':
        is_valid, err = validate_python_code(modified)
        if not is_valid:
            return False, f"Replacement would break syntax: {err}", source_code

    return True, f"Tool '{tool_name}' replaced (lines {start+1}-{end})", modified


def remove_tool(server_name: str, tool_name: str) -> Tuple[bool, str]:
    """Remove a tool from a server's source file."""
    try:
        source_code, source_path = read_source_file(server_name, max_chars=200000)
        extension = source_path.suffix
        backup_path = create_backup(source_path)

        success, message, modified = remove_tool_from_source(
            source_code, tool_name, extension
        )
        if not success:
            return False, message

        with open(source_path, 'w', encoding='utf-8') as f:
            f.write(modified)

        # Register backup
        try:
            from backup_manager import get_backup_manager
            get_backup_manager().register_backup(
                str(source_path), str(backup_path),
                "remove_tool", server_name, tool_name,
            )
        except Exception:
            pass

        return True, f"{message}. Backup at {backup_path}"
    except Exception as e:
        return False, f"Failed to remove tool: {e}"


def replace_tool(server_name: str, tool_name: str, new_code: str) -> Tuple[bool, str]:
    """Replace a tool in a server's source file."""
    try:
        source_code, source_path = read_source_file(server_name, max_chars=200000)
        extension = source_path.suffix
        backup_path = create_backup(source_path)

        success, message, modified = replace_tool_in_source(
            source_code, tool_name, new_code, extension
        )
        if not success:
            return False, message

        with open(source_path, 'w', encoding='utf-8') as f:
            f.write(modified)

        try:
            from backup_manager import get_backup_manager
            get_backup_manager().register_backup(
                str(source_path), str(backup_path),
                "replace_tool", server_name, tool_name,
            )
        except Exception:
            pass

        return True, f"{message}. Backup at {backup_path}"
    except Exception as e:
        return False, f"Failed to replace tool: {e}"
