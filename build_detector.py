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
        'Cargo.toml',      # Rust
        'go.mod',          # Go
        'package.json',    # Node.js/TypeScript
        'Makefile',        # Make
        'makefile',        # Make (lowercase)
        'CMakeLists.txt',  # CMake
        'meson.build',     # Meson
        'build.zig',       # Zig
        '.git',            # Git repo root
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
