"""
build_detector.py - Build system detection and compilation support
"""

import json
import os
from pathlib import Path
from typing import Any, Dict, Optional

from mcp_manager import check_path_allowed


def detect_build_system(project_path: Path) -> Dict[str, Any]:
    """
    Detect build system and return build configuration.
    
    Args:
        project_path: Path to the project directory
        
    Returns:
        Dictionary containing:
        - type: Build system type (cargo, make, cmake, go, typescript, etc.)
        - command: Build command to run
        - args: Arguments for the build command
        - needs_compilation: Whether compilation is needed
        - project_path: Path to project
    """
    project_path = Path(project_path).resolve()
    check_path_allowed(project_path)
    
    build_info: Dict[str, Any] = {
        'type': None,
        'command': None,
        'args': [],
        'needs_compilation': False,
        'project_path': str(project_path)
    }
    
    # Check for Cargo.toml (Rust)
    if (project_path / "Cargo.toml").exists():
        build_info['type'] = 'cargo'
        build_info['command'] = 'cargo'
        build_info['args'] = ['build', '--release']
        build_info['needs_compilation'] = True
        return build_info
    
    # Check for Makefile (C/C++)
    if (project_path / "Makefile").exists() or (project_path / "makefile").exists():
        build_info['type'] = 'make'
        build_info['command'] = 'make'
        build_info['args'] = []
        build_info['needs_compilation'] = True
        return build_info
    
    # Check for CMakeLists.txt (C/C++)
    if (project_path / "CMakeLists.txt").exists():
        build_info['type'] = 'cmake'
        build_info['command'] = 'cmake'
        build_info['args'] = ['--build', '.']
        build_info['needs_compilation'] = True
        return build_info
    
    # Check for go.mod (Go)
    if (project_path / "go.mod").exists():
        build_info['type'] = 'go'
        build_info['command'] = 'go'
        build_info['args'] = ['build']
        build_info['needs_compilation'] = True
        return build_info
    
    # Check for package.json with TypeScript (TypeScript)
    package_json_path = project_path / "package.json"
    if package_json_path.exists():
        try:
            with open(package_json_path, 'r', encoding='utf-8') as f:
                pkg = json.load(f)
            
            # Check for TypeScript
            has_typescript = (
                'typescript' in pkg.get('devDependencies', {}) or
                'typescript' in pkg.get('dependencies', {}) or
                (project_path / "tsconfig.json").exists()
            )
            
            if has_typescript:
                build_info['type'] = 'typescript'
                # Check for build script
                scripts = pkg.get('scripts', {})
                if 'build' in scripts:
                    build_info['command'] = 'npm'
                    build_info['args'] = ['run', 'build']
                else:
                    build_info['command'] = 'tsc'
                    build_info['args'] = []
                build_info['needs_compilation'] = True
                return build_info
        except (json.JSONDecodeError, Exception):
            pass
    
    # Check for pom.xml (Java / Maven)
    if (project_path / "pom.xml").exists():
        build_info['type'] = 'maven'
        build_info['command'] = 'mvn'
        build_info['args'] = ['compile']
        build_info['needs_compilation'] = True
        return build_info
    
    # Check for build.gradle or build.gradle.kts (Java / Gradle)
    if (project_path / "build.gradle").exists() or (project_path / "build.gradle.kts").exists():
        build_info['type'] = 'gradle'
        build_info['command'] = 'gradle'
        build_info['args'] = ['build']
        build_info['needs_compilation'] = True
        return build_info
    
    # Check for meson.build (Meson build system)
    if (project_path / "meson.build").exists():
        build_info['type'] = 'meson'
        build_info['command'] = 'meson'
        build_info['args'] = ['compile', '-C', 'build']
        build_info['needs_compilation'] = True
        return build_info
    
    # Check for build.zig (Zig)
    if (project_path / "build.zig").exists():
        build_info['type'] = 'zig'
        build_info['command'] = 'zig'
        build_info['args'] = ['build']
        build_info['needs_compilation'] = True
        return build_info
    
    # Check for Package.swift (Swift)
    if (project_path / "Package.swift").exists():
        build_info['type'] = 'swift'
        build_info['command'] = 'swift'
        build_info['args'] = ['build']
        build_info['needs_compilation'] = True
        return build_info
    
    # Check for .csproj or .sln (C# / .NET)
    csproj_files = list(project_path.glob("*.csproj"))
    sln_files = list(project_path.glob("*.sln"))
    if csproj_files or sln_files:
        build_info['type'] = 'dotnet'
        build_info['command'] = 'dotnet'
        build_info['args'] = ['build']
        build_info['needs_compilation'] = True
        return build_info
    
    # Check for composer.json (PHP)
    if (project_path / "composer.json").exists():
        build_info['type'] = 'composer'
        build_info['command'] = 'composer'
        build_info['args'] = ['install']
        build_info['needs_compilation'] = False
        return build_info
    
    # Check for *.rockspec (Lua / LuaRocks)
    rockspec_files = list(project_path.glob("*.rockspec"))
    if rockspec_files:
        build_info['type'] = 'luarocks'
        build_info['command'] = 'luarocks'
        build_info['args'] = ['install', str(rockspec_files[0])]
        build_info['needs_compilation'] = False
        return build_info
    
    # Check for build.sbt (Scala / sbt)
    if (project_path / "build.sbt").exists():
        build_info['type'] = 'sbt'
        build_info['command'] = 'sbt'
        build_info['args'] = ['compile']
        build_info['needs_compilation'] = True
        return build_info
    
    # Check for mix.exs (Elixir / Mix)
    if (project_path / "mix.exs").exists():
        build_info['type'] = 'mix'
        build_info['command'] = 'mix'
        build_info['args'] = ['compile']
        build_info['needs_compilation'] = True
        return build_info
    
    # Check for pubspec.yaml (Dart)
    if (project_path / "pubspec.yaml").exists():
        build_info['type'] = 'dart'
        build_info['command'] = 'dart'
        build_info['args'] = ['pub', 'get']
        build_info['needs_compilation'] = True
        return build_info
    
    # Check for *.cabal or stack.yaml (Haskell)
    cabal_files = list(project_path.glob("*.cabal"))
    if cabal_files:
        build_info['type'] = 'cabal'
        build_info['command'] = 'cabal'
        build_info['args'] = ['build']
        build_info['needs_compilation'] = True
        return build_info
    if (project_path / "stack.yaml").exists():
        build_info['type'] = 'stack'
        build_info['command'] = 'stack'
        build_info['args'] = ['build']
        build_info['needs_compilation'] = True
        return build_info
    
    # Check for dune-project (OCaml / Dune)
    if (project_path / "dune-project").exists() or (project_path / "dune").exists():
        build_info['type'] = 'dune'
        build_info['command'] = 'dune'
        build_info['args'] = ['build']
        build_info['needs_compilation'] = True
        return build_info
    
    # Check for *.nimble (Nim / Nimble)
    nimble_files = list(project_path.glob("*.nimble"))
    if nimble_files:
        build_info['type'] = 'nimble'
        build_info['command'] = 'nimble'
        build_info['args'] = ['build']
        build_info['needs_compilation'] = True
        return build_info
    
    # Check for dub.json or dub.sdl (D / Dub)
    if (project_path / "dub.json").exists() or (project_path / "dub.sdl").exists():
        build_info['type'] = 'dub'
        build_info['command'] = 'dub'
        build_info['args'] = ['build']
        build_info['needs_compilation'] = True
        return build_info
    
    # Check for shard.yml (Crystal / Shards)
    if (project_path / "shard.yml").exists():
        build_info['type'] = 'crystal'
        build_info['command'] = 'crystal'
        build_info['args'] = ['build']
        build_info['needs_compilation'] = True
        return build_info
    
    # Check for META6.json (Raku)
    if (project_path / "META6.json").exists():
        build_info['type'] = 'raku'
        build_info['command'] = 'zef'
        build_info['args'] = ['install', '.']
        build_info['needs_compilation'] = False
        return build_info
    
    # Check for Project.toml (Julia)
    if (project_path / "Project.toml").exists():
        build_info['type'] = 'julia'
        build_info['command'] = 'julia'
        build_info['args'] = ['--project=.', '-e', 'using Pkg; Pkg.instantiate()']
        build_info['needs_compilation'] = False
        return build_info
    
    # Check for Gemfile (Ruby) - placed after more specific checks
    if (project_path / "Gemfile").exists():
        build_info['type'] = 'bundler'
        build_info['command'] = 'bundle'
        build_info['args'] = ['install']
        build_info['needs_compilation'] = False
        return build_info
    
    return build_info


def get_project_path_from_source_file(source_file_path: Path) -> Path:
    """
    Determine project root directory from a source file path.
    
    Looks for build system files (Cargo.toml, go.mod, package.json, etc.)
    by walking up the directory tree.
    
    Args:
        source_file_path: Path to a source file
        
    Returns:
        Path to project root directory
    """
    current = Path(source_file_path).resolve().parent
    
    # Build system indicators
    indicators = [
        'Cargo.toml',       # Rust
        'go.mod',           # Go
        'package.json',     # Node.js/TypeScript
        'Makefile',         # Make
        'makefile',         # Make (lowercase)
        'CMakeLists.txt',   # CMake
        'meson.build',      # Meson
        'build.zig',        # Zig
        'build.zig.zon',    # Zig (package manifest)
        'pom.xml',          # Java (Maven)
        'build.gradle',     # Java/Kotlin (Gradle)
        'build.gradle.kts', # Java/Kotlin (Gradle Kotlin DSL)
        'Gemfile',          # Ruby (Bundler)
        'Package.swift',    # Swift (SPM)
        'composer.json',    # PHP (Composer)
        'build.sbt',        # Scala (sbt)
        'mix.exs',          # Elixir (Mix)
        'pubspec.yaml',     # Dart (pub)
        'stack.yaml',       # Haskell (Stack)
        'dune-project',     # OCaml (Dune)
        'dub.json',         # D (Dub)
        'dub.sdl',          # D (Dub)
        'shard.yml',        # Crystal (Shards)
        'META6.json',       # Raku (zef)
        'Project.toml',     # Julia
        '.git',             # Git repo root
    ]
    
    # Walk up the directory tree
    for _ in range(20):  # Limit depth to prevent infinite loops
        for indicator in indicators:
            if (current / indicator).exists():
                return current
        parent = current.parent
        if parent == current:  # Reached filesystem root
            break
        current = parent
    
    # If no build system found, return the directory containing the source file
    return Path(source_file_path).resolve().parent
