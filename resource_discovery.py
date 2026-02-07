"""
resource_discovery.py - MCP resource introspection by parsing server source code
"""

import ast
import re
from typing import Any, Dict, List, Optional


def list_mcp_resources(source_code: str, language: str) -> List[Dict[str, Any]]:
    """
    Parse server source code for MCP resource definitions.
    
    Supports:
    - Python FastMCP: @mcp.resource("uri") decorators
    - JavaScript: server.resource("uri", ...) or addResource(...)
    """
    if language == '.py':
        return _extract_python_resources(source_code)
    elif language in ('.js', '.ts'):
        return _extract_js_resources(source_code)
    else:
        return _extract_generic_resources(source_code)


def _extract_python_resources(source_code: str) -> List[Dict[str, Any]]:
    """Extract MCP resources from Python FastMCP source."""
    resources: List[Dict[str, Any]] = []
    try:
        tree = ast.parse(source_code)
    except SyntaxError:
        return resources

    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        for dec in node.decorator_list:
            dec_str = ast.dump(dec)
            if "resource" in dec_str.lower():
                uri = ""
                # Try to extract URI from decorator arguments
                if isinstance(dec, ast.Call):
                    if dec.args:
                        if isinstance(dec.args[0], ast.Constant):
                            uri = str(dec.args[0].value)
                resources.append({
                    "name": node.name,
                    "uri": uri,
                    "docstring": ast.get_docstring(node) or "",
                    "line_start": node.lineno,
                    "type": "resource",
                })
    return resources


def _extract_js_resources(source_code: str) -> List[Dict[str, Any]]:
    """Extract MCP resources from JavaScript/TypeScript source."""
    resources: List[Dict[str, Any]] = []
    # Patterns for resource definitions
    patterns = [
        r'\.resource\(\s*["\']([^"\']+)["\']',
        r'addResource\(\s*["\']([^"\']+)["\']',
        r'server\.addResource\(\s*\{[^}]*uri:\s*["\']([^"\']+)["\']',
    ]
    seen = set()
    for pattern in patterns:
        for m in re.finditer(pattern, source_code):
            uri = m.group(1)
            if uri not in seen:
                seen.add(uri)
                line = source_code[:m.start()].count('\n') + 1
                resources.append({
                    "name": uri.split('/')[-1] or uri,
                    "uri": uri,
                    "docstring": "",
                    "line_start": line,
                    "type": "resource",
                })
    return resources


def _extract_generic_resources(source_code: str) -> List[Dict[str, Any]]:
    """Generic resource extraction using regex patterns."""
    resources: List[Dict[str, Any]] = []
    for m in re.finditer(r'resource[_\s]*\(\s*["\']([^"\']+)["\']', source_code, re.IGNORECASE):
        uri = m.group(1)
        line = source_code[:m.start()].count('\n') + 1
        resources.append({
            "name": uri.split('/')[-1] or uri,
            "uri": uri,
            "docstring": "",
            "line_start": line,
            "type": "resource",
        })
    return resources


def inspect_resource(
    source_code: str,
    resource_uri: str,
    language: str,
) -> Optional[Dict[str, Any]]:
    """Get detailed info about a specific resource."""
    resources = list_mcp_resources(source_code, language)
    for r in resources:
        if r.get("uri") == resource_uri:
            return r
    return None


def list_mcp_prompts(source_code: str, language: str) -> List[Dict[str, Any]]:
    """Parse source code for MCP prompt definitions."""
    prompts: List[Dict[str, Any]] = []
    if language == '.py':
        try:
            tree = ast.parse(source_code)
            for node in ast.walk(tree):
                if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    continue
                for dec in node.decorator_list:
                    dec_str = ast.dump(dec)
                    if "prompt" in dec_str.lower():
                        prompts.append({
                            "name": node.name,
                            "docstring": ast.get_docstring(node) or "",
                            "line_start": node.lineno,
                            "type": "prompt",
                        })
        except SyntaxError:
            pass
    elif language in ('.js', '.ts'):
        for m in re.finditer(r'\.prompt\(\s*["\']([^"\']+)["\']', source_code):
            prompts.append({
                "name": m.group(1),
                "docstring": "",
                "line_start": source_code[:m.start()].count('\n') + 1,
                "type": "prompt",
            })
    return prompts
