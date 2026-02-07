"""
tool_analyzer.py - Tool discovery, introspection, and comparison
"""

import ast
import re
from typing import Any, Dict, List, Optional, Tuple


# ============================================================================
# Python tool extraction
# ============================================================================

def _extract_python_tools(source_code: str) -> List[Dict[str, Any]]:
    """Extract tool definitions from Python source using AST."""
    tools: List[Dict[str, Any]] = []
    try:
        tree = ast.parse(source_code)
    except SyntaxError:
        return tools

    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        # Check for @*.tool() decorator
        is_tool = False
        for dec in node.decorator_list:
            dec_str = ast.dump(dec)
            if "tool" in dec_str.lower():
                is_tool = True
                break
        if not is_tool:
            continue

        params = []
        for arg in node.args.args:
            p: Dict[str, Any] = {"name": arg.arg}
            if arg.annotation:
                p["type"] = ast.get_source_segment(source_code, arg.annotation) or ""
            params.append(p)

        return_type = ""
        if node.returns:
            return_type = ast.get_source_segment(source_code, node.returns) or ""

        docstring = ast.get_docstring(node) or ""

        tools.append({
            "name": node.name,
            "parameters": params,
            "return_type": return_type,
            "docstring": docstring,
            "line_start": node.lineno,
            "line_end": node.end_lineno or node.lineno,
        })
    return tools


# ============================================================================
# Regex-based tool extraction for other languages
# ============================================================================

def _extract_js_tools(source_code: str) -> List[Dict[str, Any]]:
    """Extract tool definitions from JavaScript/TypeScript source."""
    tools: List[Dict[str, Any]] = []
    patterns = [
        # .tool("name", ...) or addTool({name: ...})
        r'\.tool\(\s*["\'](\w+)["\']',
        r'name:\s*["\'](\w+)["\']',
    ]
    seen = set()
    for pattern in patterns:
        for m in re.finditer(pattern, source_code):
            name = m.group(1)
            if name not in seen:
                seen.add(name)
                line = source_code[:m.start()].count('\n') + 1
                tools.append({
                    "name": name,
                    "parameters": [],
                    "return_type": "",
                    "docstring": "",
                    "line_start": line,
                    "line_end": line,
                })
    # Also find exported/named functions
    for m in re.finditer(r'(?:export\s+)?(?:async\s+)?function\s+(\w+)\s*\(([^)]*)\)', source_code):
        name = m.group(1)
        if name not in seen:
            seen.add(name)
            line = source_code[:m.start()].count('\n') + 1
            params = [{"name": p.strip().split(':')[0].strip()} for p in m.group(2).split(',') if p.strip()]
            tools.append({
                "name": name,
                "parameters": params,
                "return_type": "",
                "docstring": "",
                "line_start": line,
                "line_end": line,
            })
    return tools


def _extract_rust_tools(source_code: str) -> List[Dict[str, Any]]:
    tools: List[Dict[str, Any]] = []
    for m in re.finditer(r'(?:pub\s+)?(?:async\s+)?fn\s+(\w+)\s*\(([^)]*)\)(?:\s*->\s*(\S+))?', source_code):
        name = m.group(1)
        line = source_code[:m.start()].count('\n') + 1
        params = [{"name": p.strip().split(':')[0].strip()} for p in m.group(2).split(',') if p.strip() and p.strip() != '&self']
        tools.append({
            "name": name,
            "parameters": params,
            "return_type": m.group(3) or "",
            "docstring": "",
            "line_start": line,
            "line_end": line,
        })
    return tools


def _extract_go_tools(source_code: str) -> List[Dict[str, Any]]:
    tools: List[Dict[str, Any]] = []
    for m in re.finditer(r'func\s+(?:\([^)]*\)\s+)?(\w+)\s*\(([^)]*)\)', source_code):
        name = m.group(1)
        line = source_code[:m.start()].count('\n') + 1
        params = [{"name": p.strip().split()[0] if p.strip().split() else p.strip()} for p in m.group(2).split(',') if p.strip()]
        tools.append({
            "name": name,
            "parameters": params,
            "return_type": "",
            "docstring": "",
            "line_start": line,
            "line_end": line,
        })
    return tools


def _extract_c_tools(source_code: str) -> List[Dict[str, Any]]:
    tools: List[Dict[str, Any]] = []
    for m in re.finditer(r'(?:static\s+)?(?:\w+\s+)+(\w+)\s*\(([^)]*)\)\s*\{', source_code):
        name = m.group(1)
        if name in ('if', 'for', 'while', 'switch', 'return', 'main'):
            continue
        line = source_code[:m.start()].count('\n') + 1
        params = [{"name": p.strip().split()[-1] if p.strip().split() else ""} for p in m.group(2).split(',') if p.strip() and p.strip() != 'void']
        tools.append({
            "name": name,
            "parameters": params,
            "return_type": "",
            "docstring": "",
            "line_start": line,
            "line_end": line,
        })
    return tools


def _extract_zig_tools(source_code: str) -> List[Dict[str, Any]]:
    """Extract function definitions from Zig source."""
    tools: List[Dict[str, Any]] = []
    for m in re.finditer(r'(?:pub\s+)?fn\s+(\w+)\s*\(([^)]*)\)(?:\s*(\w+))?\s*\{', source_code):
        name = m.group(1)
        line = source_code[:m.start()].count('\n') + 1
        params = [{"name": p.strip().split(':')[0].strip()} for p in m.group(2).split(',') if p.strip()]
        tools.append({
            "name": name,
            "parameters": params,
            "return_type": m.group(3) or "",
            "docstring": "",
            "line_start": line,
            "line_end": line,
        })
    return tools


def _extract_java_tools(source_code: str) -> List[Dict[str, Any]]:
    """Extract method definitions from Java source."""
    tools: List[Dict[str, Any]] = []
    for m in re.finditer(
        r'(?:(?:public|private|protected)\s+)?(?:static\s+)?(?:(?:final|abstract|synchronized)\s+)?(\w+)\s+(\w+)\s*\(([^)]*)\)\s*(?:throws\s+[\w,\s]+)?\s*\{',
        source_code
    ):
        return_type = m.group(1)
        name = m.group(2)
        # Skip control-flow keywords and class/interface declarations
        if name in ('if', 'for', 'while', 'switch', 'return', 'catch', 'class', 'interface', 'new'):
            continue
        if return_type in ('class', 'interface', 'enum', 'new', 'return'):
            continue
        line = source_code[:m.start()].count('\n') + 1
        params = [{"name": p.strip().split()[-1] if p.strip().split() else ""} for p in m.group(3).split(',') if p.strip()]
        tools.append({
            "name": name,
            "parameters": params,
            "return_type": return_type,
            "docstring": "",
            "line_start": line,
            "line_end": line,
        })
    return tools


def _extract_ruby_tools(source_code: str) -> List[Dict[str, Any]]:
    """Extract method definitions from Ruby source."""
    tools: List[Dict[str, Any]] = []
    for m in re.finditer(r'def\s+(?:self\.)?(\w+[?!=]?)\s*(?:\(([^)]*)\))?', source_code):
        name = m.group(1)
        line = source_code[:m.start()].count('\n') + 1
        params = []
        if m.group(2):
            params = [{"name": p.strip().lstrip('*&')} for p in m.group(2).split(',') if p.strip()]
        tools.append({
            "name": name,
            "parameters": params,
            "return_type": "",
            "docstring": "",
            "line_start": line,
            "line_end": line,
        })
    return tools


def _extract_kotlin_tools(source_code: str) -> List[Dict[str, Any]]:
    """Extract function definitions from Kotlin source."""
    tools: List[Dict[str, Any]] = []
    for m in re.finditer(r'(?:(?:private|public|internal|protected)\s+)?(?:suspend\s+)?fun\s+(\w+)\s*\(([^)]*)\)(?:\s*:\s*(\w+))?', source_code):
        name = m.group(1)
        line = source_code[:m.start()].count('\n') + 1
        params = [{"name": p.strip().split(':')[0].strip()} for p in m.group(2).split(',') if p.strip()]
        tools.append({"name": name, "parameters": params, "return_type": m.group(3) or "", "docstring": "", "line_start": line, "line_end": line})
    return tools


def _extract_swift_tools(source_code: str) -> List[Dict[str, Any]]:
    """Extract function definitions from Swift source."""
    tools: List[Dict[str, Any]] = []
    for m in re.finditer(r'(?:(?:private|public|internal|open|fileprivate)\s+)?(?:static\s+)?func\s+(\w+)\s*\(([^)]*)\)(?:\s*->\s*(\S+))?', source_code):
        name = m.group(1)
        line = source_code[:m.start()].count('\n') + 1
        params = [{"name": p.strip().split(':')[0].strip()} for p in m.group(2).split(',') if p.strip()]
        tools.append({"name": name, "parameters": params, "return_type": m.group(3) or "", "docstring": "", "line_start": line, "line_end": line})
    return tools


def _extract_csharp_tools(source_code: str) -> List[Dict[str, Any]]:
    """Extract method definitions from C# source."""
    tools: List[Dict[str, Any]] = []
    for m in re.finditer(
        r'(?:(?:public|private|protected|internal)\s+)?(?:static\s+)?(?:async\s+)?(\w+(?:<[^>]+>)?)\s+(\w+)\s*\(([^)]*)\)\s*\{',
        source_code
    ):
        return_type = m.group(1)
        name = m.group(2)
        if name in ('if', 'for', 'while', 'switch', 'return', 'catch', 'class', 'new'):
            continue
        if return_type in ('class', 'interface', 'enum', 'namespace', 'new', 'return'):
            continue
        line = source_code[:m.start()].count('\n') + 1
        params = [{"name": p.strip().split()[-1] if p.strip().split() else ""} for p in m.group(3).split(',') if p.strip()]
        tools.append({"name": name, "parameters": params, "return_type": return_type, "docstring": "", "line_start": line, "line_end": line})
    return tools


def _extract_php_tools(source_code: str) -> List[Dict[str, Any]]:
    """Extract function definitions from PHP source."""
    tools: List[Dict[str, Any]] = []
    for m in re.finditer(r'(?:(?:public|private|protected)\s+)?(?:static\s+)?function\s+(\w+)\s*\(([^)]*)\)', source_code):
        name = m.group(1)
        line = source_code[:m.start()].count('\n') + 1
        params = [{"name": p.strip().split('=')[0].strip().split()[-1] if p.strip() else ""} for p in m.group(2).split(',') if p.strip()]
        tools.append({"name": name, "parameters": params, "return_type": "", "docstring": "", "line_start": line, "line_end": line})
    return tools


def _extract_lua_tools(source_code: str) -> List[Dict[str, Any]]:
    """Extract function definitions from Lua source."""
    tools: List[Dict[str, Any]] = []
    for m in re.finditer(r'(?:local\s+)?function\s+(\w+(?:\.\w+)?)\s*\(([^)]*)\)', source_code):
        name = m.group(1)
        line = source_code[:m.start()].count('\n') + 1
        params = [{"name": p.strip()} for p in m.group(2).split(',') if p.strip()]
        tools.append({"name": name, "parameters": params, "return_type": "", "docstring": "", "line_start": line, "line_end": line})
    return tools


def _extract_scala_tools(source_code: str) -> List[Dict[str, Any]]:
    """Extract function definitions from Scala source."""
    tools: List[Dict[str, Any]] = []
    for m in re.finditer(r'def\s+(\w+)\s*(?:\[.*?\])?\s*\(([^)]*)\)\s*(?::\s*(\w+(?:\[.*?\])?))?', source_code):
        name = m.group(1)
        line = source_code[:m.start()].count('\n') + 1
        params = [{"name": p.strip().split(':')[0].strip()} for p in m.group(2).split(',') if p.strip()]
        tools.append({"name": name, "parameters": params, "return_type": m.group(3) or "", "docstring": "", "line_start": line, "line_end": line})
    return tools


def _extract_elixir_tools(source_code: str) -> List[Dict[str, Any]]:
    """Extract function definitions from Elixir source."""
    tools: List[Dict[str, Any]] = []
    for m in re.finditer(r'def[p]?\s+(\w+[?!]?)\s*(?:\(([^)]*)\))?', source_code):
        name = m.group(1)
        line = source_code[:m.start()].count('\n') + 1
        params = []
        if m.group(2):
            params = [{"name": p.strip().split('\\')[0].strip()} for p in m.group(2).split(',') if p.strip()]
        tools.append({"name": name, "parameters": params, "return_type": "", "docstring": "", "line_start": line, "line_end": line})
    return tools


def _extract_dart_tools(source_code: str) -> List[Dict[str, Any]]:
    """Extract function definitions from Dart source."""
    tools: List[Dict[str, Any]] = []
    for m in re.finditer(r'(?:(?:static|abstract)\s+)?(\w+(?:<[^>]+>)?)\s+(\w+)\s*\(([^)]*)\)\s*(?:async\s*)?\{', source_code):
        return_type = m.group(1)
        name = m.group(2)
        if name in ('if', 'for', 'while', 'switch', 'return', 'catch', 'class', 'new'):
            continue
        if return_type in ('class', 'enum', 'mixin', 'extension', 'new', 'return'):
            continue
        line = source_code[:m.start()].count('\n') + 1
        params = [{"name": p.strip().split()[-1] if p.strip().split() else ""} for p in m.group(3).split(',') if p.strip()]
        tools.append({"name": name, "parameters": params, "return_type": return_type, "docstring": "", "line_start": line, "line_end": line})
    return tools


def _extract_haskell_tools(source_code: str) -> List[Dict[str, Any]]:
    """Extract function definitions from Haskell source."""
    tools: List[Dict[str, Any]] = []
    seen = set()
    # Type signatures
    for m in re.finditer(r'^(\w+)\s+::\s+(.+)$', source_code, re.MULTILINE):
        name = m.group(1)
        if name not in seen and name not in ('module', 'import', 'type', 'data', 'class', 'instance'):
            seen.add(name)
            line = source_code[:m.start()].count('\n') + 1
            tools.append({"name": name, "parameters": [], "return_type": m.group(2).strip(), "docstring": "", "line_start": line, "line_end": line})
    return tools


def _extract_ocaml_tools(source_code: str) -> List[Dict[str, Any]]:
    """Extract let bindings from OCaml source."""
    tools: List[Dict[str, Any]] = []
    for m in re.finditer(r'let\s+(?:rec\s+)?(\w+)\s+([^=]*?)=', source_code):
        name = m.group(1)
        if name in ('_', 'open', 'module', 'type'):
            continue
        line = source_code[:m.start()].count('\n') + 1
        params = [{"name": p.strip()} for p in m.group(2).split() if p.strip() and p.strip() != '()']
        tools.append({"name": name, "parameters": params, "return_type": "", "docstring": "", "line_start": line, "line_end": line})
    return tools


def _extract_nim_tools(source_code: str) -> List[Dict[str, Any]]:
    """Extract proc/func definitions from Nim source."""
    tools: List[Dict[str, Any]] = []
    for m in re.finditer(r'(?:proc|func)\s+(\w+)\s*(?:\*\s*)?\(([^)]*)\)(?:\s*:\s*(\w+))?', source_code):
        name = m.group(1)
        line = source_code[:m.start()].count('\n') + 1
        params = [{"name": p.strip().split(':')[0].strip()} for p in m.group(2).split(',') if p.strip()]
        tools.append({"name": name, "parameters": params, "return_type": m.group(3) or "", "docstring": "", "line_start": line, "line_end": line})
    return tools


def _extract_d_tools(source_code: str) -> List[Dict[str, Any]]:
    """Extract function definitions from D source."""
    tools: List[Dict[str, Any]] = []
    for m in re.finditer(r'(?:(?:public|private|protected|package)\s+)?(?:static\s+)?(\w+)\s+(\w+)\s*\(([^)]*)\)\s*\{', source_code):
        return_type = m.group(1)
        name = m.group(2)
        if name in ('if', 'for', 'while', 'switch', 'return', 'catch', 'class', 'struct', 'new'):
            continue
        if return_type in ('class', 'struct', 'interface', 'enum', 'new', 'return', 'import'):
            continue
        line = source_code[:m.start()].count('\n') + 1
        params = [{"name": p.strip().split()[-1] if p.strip().split() else ""} for p in m.group(3).split(',') if p.strip()]
        tools.append({"name": name, "parameters": params, "return_type": return_type, "docstring": "", "line_start": line, "line_end": line})
    return tools


def _extract_crystal_tools(source_code: str) -> List[Dict[str, Any]]:
    """Extract method definitions from Crystal source."""
    tools: List[Dict[str, Any]] = []
    for m in re.finditer(r'def\s+(?:self\.)?(\w+[?!=]?)\s*(?:\(([^)]*)\))?', source_code):
        name = m.group(1)
        line = source_code[:m.start()].count('\n') + 1
        params = []
        if m.group(2):
            params = [{"name": p.strip().split(':')[0].strip().lstrip('*&')} for p in m.group(2).split(',') if p.strip()]
        tools.append({"name": name, "parameters": params, "return_type": "", "docstring": "", "line_start": line, "line_end": line})
    return tools


def _extract_raku_tools(source_code: str) -> List[Dict[str, Any]]:
    """Extract sub/method definitions from Raku source."""
    tools: List[Dict[str, Any]] = []
    for m in re.finditer(r'(?:multi\s+)?(?:sub|method)\s+(\w+)\s*\(([^)]*)\)', source_code):
        name = m.group(1)
        line = source_code[:m.start()].count('\n') + 1
        params = [{"name": p.strip().split()[-1] if p.strip().split() else p.strip()} for p in m.group(2).split(',') if p.strip()]
        tools.append({"name": name, "parameters": params, "return_type": "", "docstring": "", "line_start": line, "line_end": line})
    return tools


def _extract_julia_tools(source_code: str) -> List[Dict[str, Any]]:
    """Extract function definitions from Julia source."""
    tools: List[Dict[str, Any]] = []
    for m in re.finditer(r'function\s+(\w+)\s*\(([^)]*)\)', source_code):
        name = m.group(1)
        line = source_code[:m.start()].count('\n') + 1
        params = [{"name": p.strip().split(':')[0].strip()} for p in m.group(2).split(',') if p.strip()]
        tools.append({"name": name, "parameters": params, "return_type": "", "docstring": "", "line_start": line, "line_end": line})
    # Short form: name(params) = ...
    for m in re.finditer(r'^(\w+)\s*\(([^)]*)\)\s*=', source_code, re.MULTILINE):
        name = m.group(1)
        if name not in ('if', 'for', 'while', 'function'):
            line = source_code[:m.start()].count('\n') + 1
            params = [{"name": p.strip().split(':')[0].strip()} for p in m.group(2).split(',') if p.strip()]
            tools.append({"name": name, "parameters": params, "return_type": "", "docstring": "", "line_start": line, "line_end": line})
    return tools


_TOOL_EXTRACTORS = {
    '.py': _extract_python_tools,
    '.js': _extract_js_tools,
    '.ts': _extract_js_tools,
    '.rs': _extract_rust_tools,
    '.go': _extract_go_tools,
    '.c': _extract_c_tools,
    '.cpp': _extract_c_tools,
    '.cc': _extract_c_tools,
    '.cxx': _extract_c_tools,
    '.zig': _extract_zig_tools,
    '.java': _extract_java_tools,
    '.rb': _extract_ruby_tools,
    '.kt': _extract_kotlin_tools,
    '.kts': _extract_kotlin_tools,
    '.swift': _extract_swift_tools,
    '.cs': _extract_csharp_tools,
    '.php': _extract_php_tools,
    '.lua': _extract_lua_tools,
    '.scala': _extract_scala_tools,
    '.ex': _extract_elixir_tools,
    '.exs': _extract_elixir_tools,
    '.dart': _extract_dart_tools,
    '.hs': _extract_haskell_tools,
    '.ml': _extract_ocaml_tools,
    '.mli': _extract_ocaml_tools,
    '.nim': _extract_nim_tools,
    '.d': _extract_d_tools,
    '.cr': _extract_crystal_tools,
    '.raku': _extract_raku_tools,
    '.rakumod': _extract_raku_tools,
    '.pm6': _extract_raku_tools,
    '.jl': _extract_julia_tools,
}


# ============================================================================
# Public API
# ============================================================================

def list_tools_in_source(source_code: str, language: str) -> List[Dict[str, Any]]:
    """Extract all tool/function definitions from source code."""
    extractor = _TOOL_EXTRACTORS.get(language, _extract_c_tools)
    return extractor(source_code)


def get_tool_signature(
    tool_name: str, source_code: str, language: str
) -> Optional[Dict[str, Any]]:
    """Get the signature of a specific tool."""
    tools = list_tools_in_source(source_code, language)
    for t in tools:
        if t["name"] == tool_name:
            return t
    return None


def get_tool_documentation(
    tool_name: str, source_code: str, language: str
) -> Optional[str]:
    """Get the docstring/documentation of a specific tool."""
    sig = get_tool_signature(tool_name, source_code, language)
    if sig:
        return sig.get("docstring", "")
    return None


def compare_tools(
    source1: str, source2: str, language: str
) -> Dict[str, Any]:
    """Compare tool sets between two source files."""
    tools1 = {t["name"]: t for t in list_tools_in_source(source1, language)}
    tools2 = {t["name"]: t for t in list_tools_in_source(source2, language)}

    names1 = set(tools1.keys())
    names2 = set(tools2.keys())

    return {
        "only_in_first": sorted(names1 - names2),
        "only_in_second": sorted(names2 - names1),
        "in_both": sorted(names1 & names2),
        "first_count": len(names1),
        "second_count": len(names2),
    }
