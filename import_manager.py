"""
import_manager.py - Import detection, checking, and injection for multiple languages
"""

import ast
import json
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


# ============================================================================
# Import extraction per language
# ============================================================================

def extract_imports_python(code: str) -> List[str]:
    """Extract import statements from Python code."""
    imports: List[str] = []
    try:
        tree = ast.parse(code)
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(f"import {alias.name}")
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                names = ", ".join(a.name for a in node.names)
                imports.append(f"from {module} import {names}")
    except SyntaxError:
        # Fallback: regex
        for m in re.finditer(r'^(import .+|from .+ import .+)', code, re.MULTILINE):
            imports.append(m.group(0).strip())
    return imports


def extract_imports_javascript(code: str) -> List[str]:
    """Extract import/require statements from JavaScript/TypeScript."""
    imports: List[str] = []
    for m in re.finditer(r'^(import\s+.+|const\s+\w+\s*=\s*require\(.+\));?\s*$', code, re.MULTILINE):
        imports.append(m.group(0).strip().rstrip(';'))
    return imports


def extract_imports_rust(code: str) -> List[str]:
    imports: List[str] = []
    for m in re.finditer(r'^(use\s+.+);', code, re.MULTILINE):
        imports.append(m.group(0).strip())
    return imports


def extract_imports_go(code: str) -> List[str]:
    imports: List[str] = []
    # single-line: import "fmt"
    for m in re.finditer(r'^import\s+"([^"]+)"', code, re.MULTILINE):
        imports.append(f'import "{m.group(1)}"')
    # block: import ( ... )
    for m in re.finditer(r'import\s*\((.*?)\)', code, re.DOTALL):
        for line in m.group(1).strip().splitlines():
            pkg = line.strip().strip('"')
            if pkg:
                imports.append(f'import "{pkg}"')
    return imports


def extract_imports_c(code: str) -> List[str]:
    imports: List[str] = []
    for m in re.finditer(r'^(#include\s+[<"].+[>"])', code, re.MULTILINE):
        imports.append(m.group(0).strip())
    return imports


def extract_imports_zig(code: str) -> List[str]:
    """Extract @import statements from Zig code."""
    imports: List[str] = []
    for m in re.finditer(r'^(const\s+\w+\s*=\s*@import\(.+\)\s*;)', code, re.MULTILINE):
        imports.append(m.group(0).strip())
    return imports


def extract_imports_java(code: str) -> List[str]:
    """Extract import statements from Java code."""
    imports: List[str] = []
    for m in re.finditer(r'^(import\s+(?:static\s+)?.+);', code, re.MULTILINE):
        imports.append(m.group(0).strip())
    return imports


def extract_imports_ruby(code: str) -> List[str]:
    """Extract require/require_relative statements from Ruby code."""
    imports: List[str] = []
    for m in re.finditer(r'^(require(?:_relative)?\s+.+)', code, re.MULTILINE):
        imports.append(m.group(0).strip())
    return imports


def extract_imports_kotlin(code: str) -> List[str]:
    """Extract import statements from Kotlin code."""
    imports: List[str] = []
    for m in re.finditer(r'^(import\s+.+)', code, re.MULTILINE):
        imports.append(m.group(0).strip())
    return imports


def extract_imports_swift(code: str) -> List[str]:
    """Extract import statements from Swift code."""
    imports: List[str] = []
    for m in re.finditer(r'^((?:@testable\s+)?import\s+\w+)', code, re.MULTILINE):
        imports.append(m.group(0).strip())
    return imports


def extract_imports_csharp(code: str) -> List[str]:
    """Extract using statements from C# code."""
    imports: List[str] = []
    for m in re.finditer(r'^(using\s+(?:static\s+)?.+);', code, re.MULTILINE):
        imports.append(m.group(0).strip())
    return imports


def extract_imports_php(code: str) -> List[str]:
    """Extract require/use statements from PHP code."""
    imports: List[str] = []
    for m in re.finditer(r'^((?:require|require_once|include|include_once)\s+.+;)', code, re.MULTILINE):
        imports.append(m.group(0).strip())
    for m in re.finditer(r'^(use\s+.+;)', code, re.MULTILINE):
        imports.append(m.group(0).strip())
    return imports


def extract_imports_lua(code: str) -> List[str]:
    """Extract require statements from Lua code."""
    imports: List[str] = []
    for m in re.finditer(r'^((?:local\s+\w+\s*=\s*)?require\s*[\("]\s*["\']?.+["\']?\s*[\)"])', code, re.MULTILINE):
        imports.append(m.group(0).strip())
    return imports


def extract_imports_scala(code: str) -> List[str]:
    """Extract import statements from Scala code."""
    imports: List[str] = []
    for m in re.finditer(r'^(import\s+.+)', code, re.MULTILINE):
        imports.append(m.group(0).strip())
    return imports


def extract_imports_elixir(code: str) -> List[str]:
    """Extract alias/require/import/use statements from Elixir code."""
    imports: List[str] = []
    for m in re.finditer(r'^((?:alias|require|import|use)\s+.+)', code, re.MULTILINE):
        imports.append(m.group(0).strip())
    return imports


def extract_imports_dart(code: str) -> List[str]:
    """Extract import statements from Dart code."""
    imports: List[str] = []
    for m in re.finditer(r'^(import\s+.+;)', code, re.MULTILINE):
        imports.append(m.group(0).strip())
    return imports


def extract_imports_haskell(code: str) -> List[str]:
    """Extract import statements from Haskell code."""
    imports: List[str] = []
    for m in re.finditer(r'^(import\s+(?:qualified\s+)?\w+.+)', code, re.MULTILINE):
        imports.append(m.group(0).strip())
    return imports


def extract_imports_ocaml(code: str) -> List[str]:
    """Extract open/module statements from OCaml code."""
    imports: List[str] = []
    for m in re.finditer(r'^(open\s+\w+)', code, re.MULTILINE):
        imports.append(m.group(0).strip())
    return imports


def extract_imports_nim(code: str) -> List[str]:
    """Extract import/from statements from Nim code."""
    imports: List[str] = []
    for m in re.finditer(r'^((?:import|from)\s+.+)', code, re.MULTILINE):
        imports.append(m.group(0).strip())
    return imports


def extract_imports_d(code: str) -> List[str]:
    """Extract import statements from D code."""
    imports: List[str] = []
    for m in re.finditer(r'^(import\s+.+;)', code, re.MULTILINE):
        imports.append(m.group(0).strip())
    return imports


def extract_imports_crystal(code: str) -> List[str]:
    """Extract require statements from Crystal code."""
    imports: List[str] = []
    for m in re.finditer(r'^(require\s+.+)', code, re.MULTILINE):
        imports.append(m.group(0).strip())
    return imports


def extract_imports_raku(code: str) -> List[str]:
    """Extract use/need statements from Raku code."""
    imports: List[str] = []
    for m in re.finditer(r'^((?:use|need)\s+.+;)', code, re.MULTILINE):
        imports.append(m.group(0).strip())
    return imports


def extract_imports_julia(code: str) -> List[str]:
    """Extract using/import statements from Julia code."""
    imports: List[str] = []
    for m in re.finditer(r'^((?:using|import)\s+.+)', code, re.MULTILINE):
        imports.append(m.group(0).strip())
    return imports


_EXTRACTORS = {
    '.py': extract_imports_python,
    '.js': extract_imports_javascript,
    '.ts': extract_imports_javascript,
    '.rs': extract_imports_rust,
    '.go': extract_imports_go,
    '.c': extract_imports_c,
    '.cpp': extract_imports_c,
    '.cc': extract_imports_c,
    '.cxx': extract_imports_c,
    '.zig': extract_imports_zig,
    '.java': extract_imports_java,
    '.rb': extract_imports_ruby,
    '.kt': extract_imports_kotlin,
    '.kts': extract_imports_kotlin,
    '.swift': extract_imports_swift,
    '.cs': extract_imports_csharp,
    '.php': extract_imports_php,
    '.lua': extract_imports_lua,
    '.scala': extract_imports_scala,
    '.ex': extract_imports_elixir,
    '.exs': extract_imports_elixir,
    '.dart': extract_imports_dart,
    '.hs': extract_imports_haskell,
    '.ml': extract_imports_ocaml,
    '.mli': extract_imports_ocaml,
    '.nim': extract_imports_nim,
    '.d': extract_imports_d,
    '.cr': extract_imports_crystal,
    '.raku': extract_imports_raku,
    '.rakumod': extract_imports_raku,
    '.pm6': extract_imports_raku,
    '.jl': extract_imports_julia,
}


def extract_imports(code: str, language: str) -> List[str]:
    """Extract imports from code for the given language extension (e.g. '.py')."""
    extractor = _EXTRACTORS.get(language)
    if extractor:
        return extractor(code)
    return []


# ============================================================================
# Missing import detection
# ============================================================================

def check_missing_imports(
    source_code: str, tool_code: str, language: str
) -> List[str]:
    """Return imports in tool_code that are not present in source_code."""
    source_imports = set(extract_imports(source_code, language))
    tool_imports = extract_imports(tool_code, language)
    missing = [imp for imp in tool_imports if imp not in source_imports]
    return missing


# ============================================================================
# Import injection
# ============================================================================

def _find_import_insert_position_python(source_code: str) -> int:
    """Find the line index after the last import in Python source."""
    lines = source_code.splitlines(keepends=True)
    last_import_idx = -1
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("import ") or stripped.startswith("from "):
            last_import_idx = i
    return last_import_idx + 1 if last_import_idx >= 0 else 0


def _find_import_insert_position_c(source_code: str) -> int:
    lines = source_code.splitlines(keepends=True)
    last_include = -1
    for i, line in enumerate(lines):
        if line.strip().startswith("#include"):
            last_include = i
    return last_include + 1 if last_include >= 0 else 0


def inject_imports(
    source_code: str, imports: List[str], language: str
) -> str:
    """Inject import statements into source code at the correct position."""
    if not imports:
        return source_code

    lines = source_code.splitlines(keepends=True)

    if language in ('.py',):
        pos = _find_import_insert_position_python(source_code)
    elif language in ('.c', '.cpp', '.cc', '.cxx'):
        pos = _find_import_insert_position_c(source_code)
    elif language in ('.js', '.ts'):
        # Insert after last import/require
        pos = 0
        for i, line in enumerate(lines):
            if re.match(r'^\s*(import\s|const\s+\w+\s*=\s*require)', line):
                pos = i + 1
    elif language == '.rs':
        pos = 0
        for i, line in enumerate(lines):
            if line.strip().startswith("use "):
                pos = i + 1
    elif language == '.go':
        pos = 0
        for i, line in enumerate(lines):
            if line.strip().startswith("import"):
                pos = i + 1
    elif language == '.zig':
        # Insert after last @import line
        pos = 0
        for i, line in enumerate(lines):
            if '@import(' in line:
                pos = i + 1
    elif language == '.java':
        # Insert after last import statement (before class declaration)
        pos = 0
        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped.startswith("import "):
                pos = i + 1
    elif language == '.rb':
        # Insert after last require/require_relative
        pos = 0
        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped.startswith("require ") or stripped.startswith("require_relative "):
                pos = i + 1
    elif language in ('.kt', '.kts', '.scala'):
        pos = 0
        for i, line in enumerate(lines):
            if line.strip().startswith("import "):
                pos = i + 1
    elif language == '.swift':
        pos = 0
        for i, line in enumerate(lines):
            if line.strip().startswith("import ") or line.strip().startswith("@testable import "):
                pos = i + 1
    elif language == '.cs':
        pos = 0
        for i, line in enumerate(lines):
            if line.strip().startswith("using "):
                pos = i + 1
    elif language == '.php':
        pos = 0
        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped.startswith("use ") or stripped.startswith("require") or stripped.startswith("include"):
                pos = i + 1
    elif language == '.lua':
        pos = 0
        for i, line in enumerate(lines):
            if 'require' in line:
                pos = i + 1
    elif language in ('.ex', '.exs'):
        pos = 0
        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped.startswith(("alias ", "require ", "import ", "use ")):
                pos = i + 1
    elif language == '.dart':
        pos = 0
        for i, line in enumerate(lines):
            if line.strip().startswith("import "):
                pos = i + 1
    elif language == '.hs':
        pos = 0
        for i, line in enumerate(lines):
            if line.strip().startswith("import "):
                pos = i + 1
    elif language in ('.ml', '.mli'):
        pos = 0
        for i, line in enumerate(lines):
            if line.strip().startswith("open "):
                pos = i + 1
    elif language == '.nim':
        pos = 0
        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped.startswith("import ") or stripped.startswith("from "):
                pos = i + 1
    elif language == '.d':
        pos = 0
        for i, line in enumerate(lines):
            if line.strip().startswith("import "):
                pos = i + 1
    elif language == '.cr':
        pos = 0
        for i, line in enumerate(lines):
            if line.strip().startswith("require "):
                pos = i + 1
    elif language in ('.raku', '.rakumod', '.pm6'):
        pos = 0
        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped.startswith("use ") or stripped.startswith("need "):
                pos = i + 1
    elif language == '.jl':
        pos = 0
        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped.startswith("using ") or stripped.startswith("import "):
                pos = i + 1
    else:
        pos = 0

    import_block = "\n".join(imports) + "\n"
    lines.insert(pos, import_block)
    return "".join(lines)


# ============================================================================
# Dependency detection
# ============================================================================

def detect_dependencies(project_path: str, language: str) -> List[Dict[str, str]]:
    """Detect external dependencies from project manifests."""
    pp = Path(project_path)
    deps: List[Dict[str, str]] = []

    if language == '.py':
        req = pp / "requirements.txt"
        if req.exists():
            for line in req.read_text(encoding='utf-8').splitlines():
                line = line.strip()
                if line and not line.startswith('#'):
                    deps.append({"name": line, "source": "requirements.txt"})
        pyproject = pp / "pyproject.toml"
        if pyproject.exists():
            deps.append({"name": "(see pyproject.toml)", "source": "pyproject.toml"})

    elif language in ('.js', '.ts'):
        pkg = pp / "package.json"
        if pkg.exists():
            try:
                data = json.loads(pkg.read_text(encoding='utf-8'))
                for name, ver in data.get("dependencies", {}).items():
                    deps.append({"name": f"{name}@{ver}", "source": "package.json"})
                for name, ver in data.get("devDependencies", {}).items():
                    deps.append({"name": f"{name}@{ver}", "source": "package.json (dev)"})
            except Exception:
                pass

    elif language == '.rs':
        cargo = pp / "Cargo.toml"
        if cargo.exists():
            deps.append({"name": "(see Cargo.toml)", "source": "Cargo.toml"})

    elif language == '.go':
        gomod = pp / "go.mod"
        if gomod.exists():
            for line in gomod.read_text(encoding='utf-8').splitlines():
                line = line.strip()
                if line and not line.startswith("module") and not line.startswith("go ") and not line.startswith("//"):
                    if not line.startswith(("require", ")", "(")):
                        deps.append({"name": line.split()[0] if line.split() else line, "source": "go.mod"})

    elif language == '.zig':
        zon = pp / "build.zig.zon"
        if zon.exists():
            deps.append({"name": "(see build.zig.zon)", "source": "build.zig.zon"})
        build_zig = pp / "build.zig"
        if build_zig.exists():
            deps.append({"name": "(see build.zig)", "source": "build.zig"})

    elif language == '.java':
        pom = pp / "pom.xml"
        if pom.exists():
            deps.append({"name": "(see pom.xml)", "source": "pom.xml"})
        for gradle_file in ("build.gradle", "build.gradle.kts"):
            gradle = pp / gradle_file
            if gradle.exists():
                deps.append({"name": f"(see {gradle_file})", "source": gradle_file})

    elif language == '.rb':
        gemfile = pp / "Gemfile"
        if gemfile.exists():
            for line in gemfile.read_text(encoding='utf-8').splitlines():
                line = line.strip()
                if line.startswith("gem "):
                    gem_match = re.match(r'gem\s+["\']([^"\']+)["\']', line)
                    if gem_match:
                        deps.append({"name": gem_match.group(1), "source": "Gemfile"})

    elif language in ('.kt', '.kts'):
        for gradle_file in ("build.gradle.kts", "build.gradle"):
            gradle = pp / gradle_file
            if gradle.exists():
                deps.append({"name": f"(see {gradle_file})", "source": gradle_file})

    elif language == '.swift':
        pkg = pp / "Package.swift"
        if pkg.exists():
            deps.append({"name": "(see Package.swift)", "source": "Package.swift"})

    elif language == '.cs':
        for f in pp.glob("*.csproj"):
            deps.append({"name": f"(see {f.name})", "source": f.name})
        for f in pp.glob("*.sln"):
            deps.append({"name": f"(see {f.name})", "source": f.name})

    elif language == '.php':
        composer = pp / "composer.json"
        if composer.exists():
            try:
                data = json.loads(composer.read_text(encoding='utf-8'))
                for name, ver in data.get("require", {}).items():
                    deps.append({"name": f"{name}@{ver}", "source": "composer.json"})
            except Exception:
                deps.append({"name": "(see composer.json)", "source": "composer.json"})

    elif language == '.lua':
        for f in pp.glob("*.rockspec"):
            deps.append({"name": f"(see {f.name})", "source": f.name})

    elif language == '.scala':
        sbt = pp / "build.sbt"
        if sbt.exists():
            deps.append({"name": "(see build.sbt)", "source": "build.sbt"})

    elif language in ('.ex', '.exs'):
        mix = pp / "mix.exs"
        if mix.exists():
            deps.append({"name": "(see mix.exs)", "source": "mix.exs"})

    elif language == '.dart':
        pubspec = pp / "pubspec.yaml"
        if pubspec.exists():
            deps.append({"name": "(see pubspec.yaml)", "source": "pubspec.yaml"})

    elif language == '.hs':
        for f in pp.glob("*.cabal"):
            deps.append({"name": f"(see {f.name})", "source": f.name})
        stack = pp / "stack.yaml"
        if stack.exists():
            deps.append({"name": "(see stack.yaml)", "source": "stack.yaml"})

    elif language in ('.ml', '.mli'):
        dune = pp / "dune-project"
        if dune.exists():
            deps.append({"name": "(see dune-project)", "source": "dune-project"})
        for f in pp.glob("*.opam"):
            deps.append({"name": f"(see {f.name})", "source": f.name})

    elif language == '.nim':
        for f in pp.glob("*.nimble"):
            deps.append({"name": f"(see {f.name})", "source": f.name})

    elif language == '.d':
        for dub_file in ("dub.json", "dub.sdl"):
            dub = pp / dub_file
            if dub.exists():
                deps.append({"name": f"(see {dub_file})", "source": dub_file})

    elif language == '.cr':
        shard = pp / "shard.yml"
        if shard.exists():
            deps.append({"name": "(see shard.yml)", "source": "shard.yml"})

    elif language in ('.raku', '.rakumod', '.pm6'):
        meta = pp / "META6.json"
        if meta.exists():
            deps.append({"name": "(see META6.json)", "source": "META6.json"})

    elif language == '.jl':
        proj = pp / "Project.toml"
        if proj.exists():
            deps.append({"name": "(see Project.toml)", "source": "Project.toml"})

    return deps
