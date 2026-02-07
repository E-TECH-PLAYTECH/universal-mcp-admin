"""
project_scanner.py - Multi-file project support: structure detection, file discovery, module injection
"""

import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from config_manager import get_server_config

# Common source extensions grouped by language
SOURCE_EXTENSIONS = {
    'python': ['.py'],
    'javascript': ['.js', '.mjs', '.cjs'],
    'typescript': ['.ts', '.tsx'],
    'rust': ['.rs'],
    'go': ['.go'],
    'c': ['.c', '.h'],
    'cpp': ['.cpp', '.cc', '.cxx', '.hpp', '.h'],
}

ALL_EXTENSIONS = set()
for exts in SOURCE_EXTENSIONS.values():
    ALL_EXTENSIONS.update(exts)

# Directories to skip
SKIP_DIRS = {
    'node_modules', '.git', '__pycache__', '.venv', 'venv', 'env',
    'target', 'build', 'dist', '.next', '.nuxt', 'vendor',
}


def detect_project_structure(project_path: str) -> Dict[str, Any]:
    """Detect project layout: source files, entry point, module structure."""
    pp = Path(project_path)
    if not pp.is_dir():
        return {"error": f"Not a directory: {project_path}"}

    structure: Dict[str, Any] = {
        "project_root": str(pp),
        "language": _detect_language(pp),
        "entry_point": None,
        "source_files": [],
        "modules": [],
        "build_files": [],
    }

    # Walk and collect source files
    for root, dirs, files in os.walk(pp):
        # Prune skipped directories
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        rel_root = Path(root).relative_to(pp)
        for f in sorted(files):
            fp = Path(root) / f
            if fp.suffix in ALL_EXTENSIONS:
                structure["source_files"].append(str(fp.relative_to(pp)))
            # Build files
            if f in ('Makefile', 'CMakeLists.txt', 'Cargo.toml', 'go.mod',
                      'package.json', 'pyproject.toml', 'setup.py',
                      'meson.build', 'build.zig'):
                structure["build_files"].append(str(fp.relative_to(pp)))

        # Detect modules (directories with __init__.py or index.*)
        for d in dirs:
            dp = Path(root) / d
            init_py = dp / "__init__.py"
            index_js = dp / "index.js"
            index_ts = dp / "index.ts"
            if init_py.exists() or index_js.exists() or index_ts.exists():
                structure["modules"].append(str(dp.relative_to(pp)))

    # Detect entry point
    structure["entry_point"] = _detect_entry_point(pp, structure["language"])

    return structure


def _detect_language(project_path: Path) -> str:
    """Detect primary project language."""
    if (project_path / "Cargo.toml").exists():
        return "rust"
    if (project_path / "go.mod").exists():
        return "go"
    if (project_path / "pyproject.toml").exists() or (project_path / "setup.py").exists():
        return "python"
    if (project_path / "package.json").exists():
        pkg_json = project_path / "package.json"
        try:
            import json
            data = json.loads(pkg_json.read_text(encoding='utf-8'))
            # Check if TypeScript
            deps = data.get("devDependencies", {})
            deps.update(data.get("dependencies", {}))
            if "typescript" in deps:
                return "typescript"
        except Exception:
            pass
        return "javascript"
    # Count files by extension
    ext_counts: Dict[str, int] = {}
    for root, dirs, files in os.walk(project_path):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for f in files:
            ext = Path(f).suffix
            for lang, exts in SOURCE_EXTENSIONS.items():
                if ext in exts:
                    ext_counts[lang] = ext_counts.get(lang, 0) + 1
    if ext_counts:
        return max(ext_counts, key=ext_counts.get)
    return "unknown"


def _detect_entry_point(project_path: Path, language: str) -> Optional[str]:
    """Detect the main entry point file."""
    candidates = {
        'python': ['server.py', 'main.py', 'app.py', '__main__.py', 'run.py'],
        'javascript': ['server.js', 'index.js', 'main.js', 'app.js'],
        'typescript': ['server.ts', 'index.ts', 'main.ts', 'app.ts'],
        'rust': ['src/main.rs', 'src/lib.rs', 'main.rs'],
        'go': ['main.go', 'cmd/main.go'],
        'c': ['main.c', 'src/main.c'],
        'cpp': ['main.cpp', 'src/main.cpp', 'main.cc'],
    }
    for candidate in candidates.get(language, []):
        if (project_path / candidate).exists():
            return candidate
    return None


def find_all_source_files(
    server_name: str,
    extensions: Optional[List[str]] = None,
) -> List[str]:
    """Find all source files for a server by examining its config."""
    try:
        config = get_server_config(server_name)
    except Exception:
        return []

    args = config.get("args", [])
    cwd = config.get("cwd", "")
    if not cwd:
        # Try to infer from args (e.g. full path to source file)
        for arg in args:
            p = Path(arg)
            if p.is_file():
                cwd = str(p.parent)
                break
            elif p.is_dir():
                cwd = str(p)
                break
    if not cwd:
        return []

    project_path = Path(cwd)
    if not project_path.is_dir():
        return []

    exts = set(extensions or ALL_EXTENSIONS)
    found: List[str] = []
    for root, dirs, files in os.walk(project_path):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for f in sorted(files):
            if Path(f).suffix in exts:
                found.append(str(Path(root) / f))
    return found


def find_best_injection_target(
    server_name: str, tool_name: str
) -> Optional[str]:
    """Find the best file to inject a tool into for a multi-file project."""
    try:
        config = get_server_config(server_name)
    except Exception:
        return None

    cwd = config.get("cwd", "")
    if not cwd:
        return None

    structure = detect_project_structure(cwd)
    entry = structure.get("entry_point")
    if entry:
        return str(Path(cwd) / entry)

    # If no entry point, return the first source file
    files = structure.get("source_files", [])
    if files:
        return str(Path(cwd) / files[0])

    return None


def inject_into_module(
    module_path: str,
    tool_name: str,
    tool_code: str,
    language: str,
) -> tuple:
    """Inject a tool into a specific module file."""
    p = Path(module_path)
    if not p.exists():
        return False, f"Module file not found: {module_path}"

    source = p.read_text(encoding='utf-8')

    # Check if tool already exists
    if tool_name in source:
        return False, f"Tool '{tool_name}' already exists in {module_path}"

    # Append tool code
    new_source = source.rstrip() + "\n\n\n" + tool_code.rstrip() + "\n"
    p.write_text(new_source, encoding='utf-8')
    return True, f"Injected '{tool_name}' into {module_path}"
