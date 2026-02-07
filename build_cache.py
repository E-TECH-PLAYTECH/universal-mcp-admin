"""
build_cache.py - Build command caching and learning system
"""

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional


class BuildCache:
    """
    Cache successful build commands per project to enable learning and optimization.
    
    This class learns from successful builds and can suggest build commands
    based on project structure and previous successes.
    """
    
    def __init__(self, cache_file: Optional[Path] = None):
        """
        Initialize the build cache.
        
        Args:
            cache_file: Optional path to cache file. Defaults to .build_cache.json in project root.
        """
        if cache_file is None:
            # Default cache location
            cache_dir = Path.home() / ".cache" / "universal-mcp-admin"
            cache_dir.mkdir(parents=True, exist_ok=True)
            cache_file = cache_dir / "build_cache.json"
        
        self.cache_file = Path(cache_file)
        self._cache: Dict[str, Any] = self._load_cache()
    
    def _load_cache(self) -> Dict[str, Any]:
        """Load cache from disk."""
        if self.cache_file.exists():
            try:
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except (json.JSONDecodeError, Exception):
                return {}
        return {}
    
    def _save_cache(self) -> None:
        """Save cache to disk."""
        try:
            self.cache_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(self._cache, f, indent=2)
        except Exception:
            pass  # Fail silently if cache can't be written
    
    def get_build_command(
        self,
        project_path: Path,
        build_type: str
    ) -> Optional[List[str]]:
        """
        Get cached build command if available.
        
        Args:
            project_path: Path to project
            build_type: Type of build system (cargo, make, etc.)
            
        Returns:
            Cached build command as list of strings, or None if not cached
        """
        project_key = str(Path(project_path).resolve())
        cache_key = f"{project_key}:{build_type}"
        
        cached = self._cache.get(cache_key)
        if cached and cached.get('success', False):
            return cached.get('command')
        return None
    
    def cache_build_command(
        self,
        project_path: Path,
        command: List[str],
        success: bool,
        build_type: Optional[str] = None
    ) -> None:
        """
        Cache build command result.
        
        Args:
            project_path: Path to project
            command: Build command that was executed
            success: Whether the build succeeded
            build_type: Optional build system type
        """
        project_key = str(Path(project_path).resolve())
        cache_key = f"{project_key}:{build_type or 'unknown'}"
        
        self._cache[cache_key] = {
            'command': command,
            'success': success,
            'build_type': build_type,
            'project_path': project_key
        }
        
        self._save_cache()
    
    def suggest_build_command(
        self,
        project_path: Path,
        build_type: str
    ) -> Optional[List[str]]:
        """
        Suggest build command based on project structure and cache.
        
        Args:
            project_path: Path to project
            build_type: Type of build system
            
        Returns:
            Suggested build command, or None if no suggestion available
        """
        # First check cache
        cached = self.get_build_command(project_path, build_type)
        if cached:
            return cached
        
        # Default suggestions based on build type
        defaults: Dict[str, List[str]] = {
            'cargo': ['cargo', 'build', '--release'],
            'make': ['make'],
            'cmake': ['cmake', '--build', '.'],
            'go': ['go', 'build'],
            'typescript': ['npm', 'run', 'build'],
            'meson': ['meson', 'compile', '-C', 'build'],
            'zig': ['zig', 'build'],
        }
        
        return defaults.get(build_type)
    
    def record_error(
        self,
        project_path: Path,
        command: List[str],
        error_message: str,
        build_type: Optional[str] = None
    ) -> None:
        """
        Record a build error for learning purposes.
        
        Args:
            project_path: Path to project
            command: Build command that failed
            error_message: Error message from build
            build_type: Optional build system type
        """
        project_key = str(Path(project_path).resolve())
        error_key = f"{project_key}:errors"
        
        if error_key not in self._cache:
            self._cache[error_key] = []
        
        self._cache[error_key].append({
            'command': command,
            'error': error_message,
            'build_type': build_type
        })
        
        # Keep only last 10 errors per project
        if len(self._cache[error_key]) > 10:
            self._cache[error_key] = self._cache[error_key][-10:]
        
        self._save_cache()
    
    def get_error_history(
        self,
        project_path: Path
    ) -> List[Dict[str, Any]]:
        """
        Get error history for a project.
        
        Args:
            project_path: Path to project
            
        Returns:
            List of error records
        """
        project_key = str(Path(project_path).resolve())
        error_key = f"{project_key}:errors"
        return self._cache.get(error_key, [])


# Global cache instance
_build_cache: Optional[BuildCache] = None


def get_build_cache() -> BuildCache:
    """Get or create the global build cache instance."""
    global _build_cache
    if _build_cache is None:
        _build_cache = BuildCache()
    return _build_cache
