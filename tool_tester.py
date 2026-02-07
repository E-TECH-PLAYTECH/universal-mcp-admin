"""
tool_tester.py - Tool validation, dry-run injection testing, and compatibility checking
"""

import ast
import os
import re
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


def validate_tool_signature(tool_code: str, language: str) -> Dict[str, Any]:
    """
    Validate tool structure for the given language.
    Checks decorator/annotation presence, function signature, return type, etc.
    """
    result: Dict[str, Any] = {
        "valid": True,
        "warnings": [],
        "errors": [],
        "details": {},
    }

    if language == '.py':
        _validate_python_tool(tool_code, result)
    elif language in ('.js', '.ts'):
        _validate_js_tool(tool_code, result)
    elif language == '.rs':
        _validate_rust_tool(tool_code, result)
    elif language == '.go':
        _validate_go_tool(tool_code, result)
    elif language in ('.c', '.cpp', '.cc', '.cxx'):
        _validate_c_tool(tool_code, result)
    elif language == '.zig':
        _validate_zig_tool(tool_code, result)
    elif language == '.java':
        _validate_java_tool(tool_code, result)
    elif language == '.rb':
        _validate_ruby_tool(tool_code, result)
    else:
        result["warnings"].append(f"No specific validation for language '{language}'")

    result["valid"] = len(result["errors"]) == 0
    return result


def _validate_python_tool(code: str, result: Dict[str, Any]) -> None:
    """Validate a Python tool."""
    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        result["errors"].append(f"Syntax error: {e}")
        return

    funcs = [n for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
    if not funcs:
        result["errors"].append("No function definition found")
        return

    func = funcs[0]
    result["details"]["function_name"] = func.name
    result["details"]["param_count"] = len(func.args.args)

    # Check for decorator
    has_tool_decorator = False
    for dec in func.decorator_list:
        dec_str = ast.dump(dec)
        if "tool" in dec_str.lower():
            has_tool_decorator = True
    if not has_tool_decorator:
        result["warnings"].append("No @mcp.tool() decorator found")

    # Check return type
    if func.returns is None:
        result["warnings"].append("No return type annotation")

    # Check docstring
    docstring = ast.get_docstring(func)
    if not docstring:
        result["warnings"].append("No docstring found")
    else:
        result["details"]["docstring"] = docstring[:200]

    # Check type annotations on parameters
    for arg in func.args.args:
        if arg.annotation is None and arg.arg != 'self':
            result["warnings"].append(f"Parameter '{arg.arg}' has no type annotation")


def _validate_js_tool(code: str, result: Dict[str, Any]) -> None:
    """Validate a JavaScript/TypeScript tool."""
    # Check for function definition
    if not re.search(r'(function\s+\w+|(?:const|let|var)\s+\w+\s*=|server\.\w+)', code):
        result["warnings"].append("No clear function/tool definition found")
    # Basic syntax: try node --check
    with tempfile.NamedTemporaryFile(suffix='.js', mode='w', delete=False) as f:
        f.write(code)
        f.flush()
        try:
            proc = subprocess.run(
                ['node', '--check', f.name],
                capture_output=True, text=True, timeout=10
            )
            if proc.returncode != 0:
                result["errors"].append(f"JS syntax error: {proc.stderr.strip()}")
        except FileNotFoundError:
            result["warnings"].append("Node.js not available for syntax checking")
        except subprocess.TimeoutExpired:
            result["warnings"].append("Syntax check timed out")
        finally:
            os.unlink(f.name)


def _validate_rust_tool(code: str, result: Dict[str, Any]) -> None:
    if not re.search(r'fn\s+\w+', code):
        result["errors"].append("No function definition found in Rust code")


def _validate_go_tool(code: str, result: Dict[str, Any]) -> None:
    if not re.search(r'func\s+', code):
        result["errors"].append("No function definition found in Go code")


def _validate_c_tool(code: str, result: Dict[str, Any]) -> None:
    if not re.search(r'\w+\s+\w+\s*\([^)]*\)\s*\{', code):
        result["warnings"].append("No function definition pattern found in C/C++ code")


def _validate_zig_tool(code: str, result: Dict[str, Any]) -> None:
    """Validate a Zig tool."""
    if not re.search(r'fn\s+\w+', code):
        result["errors"].append("No function definition found in Zig code")
    # Try zig ast-check if available
    with tempfile.NamedTemporaryFile(suffix='.zig', mode='w', delete=False) as f:
        f.write(code)
        f.flush()
        try:
            proc = subprocess.run(
                ['zig', 'ast-check', f.name],
                capture_output=True, text=True, timeout=10
            )
            if proc.returncode != 0:
                result["errors"].append(f"Zig syntax error: {proc.stderr.strip()}")
        except FileNotFoundError:
            result["warnings"].append("Zig not available for syntax checking")
        except subprocess.TimeoutExpired:
            result["warnings"].append("Zig syntax check timed out")
        finally:
            os.unlink(f.name)


def _validate_java_tool(code: str, result: Dict[str, Any]) -> None:
    """Validate a Java tool."""
    if not re.search(r'(?:public|private|protected)\s+.*\s+\w+\s*\(', code) and not re.search(r'class\s+\w+', code):
        result["errors"].append("No method or class definition found in Java code")
    # Try javac syntax check if available
    with tempfile.TemporaryDirectory() as tmpdir:
        # Attempt to extract class name for proper file naming
        class_match = re.search(r'public\s+class\s+(\w+)', code)
        filename = (class_match.group(1) + ".java") if class_match else "Tool.java"
        filepath = os.path.join(tmpdir, filename)
        with open(filepath, 'w') as f:
            f.write(code)
        try:
            proc = subprocess.run(
                ['javac', '-d', tmpdir, filepath],
                capture_output=True, text=True, timeout=15
            )
            if proc.returncode != 0:
                result["errors"].append(f"Java syntax error: {proc.stderr.strip()}")
        except FileNotFoundError:
            result["warnings"].append("javac not available for syntax checking")
        except subprocess.TimeoutExpired:
            result["warnings"].append("Java syntax check timed out")


def _validate_ruby_tool(code: str, result: Dict[str, Any]) -> None:
    """Validate a Ruby tool."""
    if not re.search(r'def\s+\w+', code):
        result["errors"].append("No method definition found in Ruby code")
    # Try ruby -c syntax check if available
    with tempfile.NamedTemporaryFile(suffix='.rb', mode='w', delete=False) as f:
        f.write(code)
        f.flush()
        try:
            proc = subprocess.run(
                ['ruby', '-c', f.name],
                capture_output=True, text=True, timeout=10
            )
            if proc.returncode != 0:
                result["errors"].append(f"Ruby syntax error: {proc.stderr.strip()}")
        except FileNotFoundError:
            result["warnings"].append("Ruby not available for syntax checking")
        except subprocess.TimeoutExpired:
            result["warnings"].append("Ruby syntax check timed out")
        finally:
            os.unlink(f.name)


def dry_run_injection(
    source_code: str,
    tool_name: str,
    tool_code: str,
    language: str,
) -> Dict[str, Any]:
    """
    Simulate injection without applying it.
    Returns validation result and preview of the combined code.
    """
    result: Dict[str, Any] = {
        "valid": True,
        "errors": [],
        "warnings": [],
        "preview_lines": 0,
        "tool_would_be_at_line": 0,
    }

    # Check if tool already exists
    if tool_name in source_code:
        result["errors"].append(f"Tool '{tool_name}' already exists in source")
        result["valid"] = False
        return result

    # Simulate the combined code
    combined = source_code.rstrip() + "\n\n\n" + tool_code.rstrip() + "\n"
    result["preview_lines"] = combined.count('\n') + 1
    result["tool_would_be_at_line"] = source_code.count('\n') + 3

    # Validate combined code
    if language == '.py':
        try:
            ast.parse(combined)
        except SyntaxError as e:
            result["errors"].append(f"Combined code syntax error: {e}")
            result["valid"] = False
    elif language in ('.js', '.ts'):
        with tempfile.NamedTemporaryFile(suffix='.js', mode='w', delete=False) as f:
            f.write(combined)
            f.flush()
            try:
                proc = subprocess.run(
                    ['node', '--check', f.name],
                    capture_output=True, text=True, timeout=10
                )
                if proc.returncode != 0:
                    result["errors"].append(f"Combined code error: {proc.stderr.strip()}")
                    result["valid"] = False
            except FileNotFoundError:
                result["warnings"].append("Node.js not available")
            except subprocess.TimeoutExpired:
                result["warnings"].append("Syntax check timed out")
            finally:
                os.unlink(f.name)

    # Validate the tool code itself
    sig_result = validate_tool_signature(tool_code, language)
    result["signature_valid"] = sig_result["valid"]
    result["signature_warnings"] = sig_result.get("warnings", [])

    result["valid"] = result["valid"] and len(result["errors"]) == 0
    return result


def check_tool_compatibility(
    source_code: str,
    tool_code: str,
    language: str,
) -> Dict[str, Any]:
    """
    Check compatibility of tool code with the existing source.
    Verifies imports, function dependencies, and naming conflicts.
    """
    result: Dict[str, Any] = {
        "compatible": True,
        "issues": [],
        "suggestions": [],
    }

    if language == '.py':
        _check_python_compat(source_code, tool_code, result)
    elif language in ('.js', '.ts'):
        _check_js_compat(source_code, tool_code, result)

    result["compatible"] = len([i for i in result["issues"] if i.get("severity") == "error"]) == 0
    return result


def _check_python_compat(source: str, tool: str, result: Dict[str, Any]) -> None:
    """Check Python-specific compatibility."""
    try:
        tool_tree = ast.parse(tool)
    except SyntaxError:
        result["issues"].append({"severity": "error", "message": "Tool code has syntax errors"})
        return

    # Check for name conflicts
    try:
        source_tree = ast.parse(source)
        source_names = set()
        for node in ast.walk(source_tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                source_names.add(node.name)

        for node in ast.walk(tool_tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if node.name in source_names:
                    result["issues"].append({
                        "severity": "warning",
                        "message": f"Function '{node.name}' already exists in source"
                    })
    except SyntaxError:
        pass

    # Check imports
    from import_manager import check_missing_imports
    missing = check_missing_imports(source, tool, '.py')
    if missing:
        result["suggestions"].append(f"Missing imports: {', '.join(missing)}")


def _check_js_compat(source: str, tool: str, result: Dict[str, Any]) -> None:
    """Check JavaScript compatibility."""
    from import_manager import check_missing_imports
    missing = check_missing_imports(source, tool, '.js')
    if missing:
        result["suggestions"].append(f"Missing imports/requires: {', '.join(missing)}")
