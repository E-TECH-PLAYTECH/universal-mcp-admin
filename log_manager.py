"""
log_manager.py - Server log access, analysis, and error pattern detection
"""

import os
import platform
import re
from pathlib import Path
from typing import Any, Dict, List, Optional


def _get_claude_log_dir() -> Optional[Path]:
    """Get the Claude Desktop log directory based on OS."""
    system = platform.system()
    if system == "Darwin":
        log_dir = Path.home() / "Library" / "Logs" / "Claude"
        if log_dir.exists():
            return log_dir
    elif system == "Windows":
        appdata = os.getenv("APPDATA")
        if appdata:
            log_dir = Path(appdata) / "Claude" / "logs"
            if log_dir.exists():
                return log_dir
    else:
        # Linux / other
        for candidate in [
            Path.home() / ".local" / "share" / "Claude" / "logs",
            Path.home() / ".config" / "Claude" / "logs",
        ]:
            if candidate.exists():
                return candidate
    return None


def _find_log_files(server_name: Optional[str] = None) -> List[Path]:
    """Find log files, optionally filtering by server name."""
    log_dir = _get_claude_log_dir()
    if not log_dir:
        return []

    log_files: List[Path] = []
    for f in sorted(log_dir.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True):
        if f.is_file() and f.suffix in ('.log', '.txt', ''):
            if server_name:
                # Check if log file relates to this server
                if server_name.lower() in f.name.lower():
                    log_files.append(f)
            else:
                log_files.append(f)

    # Also check for MCP-specific log locations
    mcp_log_dir = _get_claude_log_dir()
    if mcp_log_dir:
        mcp_dir = mcp_log_dir / "mcp"
        if mcp_dir.exists():
            for f in sorted(mcp_dir.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True):
                if f.is_file():
                    if server_name is None or server_name.lower() in f.name.lower():
                        log_files.append(f)

    return log_files


def get_server_logs(
    server_name: Optional[str] = None,
    lines: int = 100,
) -> Dict[str, Any]:
    """Get recent log lines, optionally filtered by server name."""
    log_files = _find_log_files(server_name)

    if not log_files:
        log_dir = _get_claude_log_dir()
        return {
            "success": False,
            "message": f"No log files found" + (f" for server '{server_name}'" if server_name else ""),
            "log_dir": str(log_dir) if log_dir else "not found",
            "available_logs": [],
        }

    result_lines: List[str] = []
    files_read: List[str] = []

    for log_file in log_files[:5]:  # Read up to 5 most recent log files
        try:
            content = log_file.read_text(encoding='utf-8', errors='replace')
            all_lines = content.splitlines()
            tail = all_lines[-lines:] if len(all_lines) > lines else all_lines
            result_lines.extend(tail)
            files_read.append(str(log_file))
        except Exception as e:
            files_read.append(f"{log_file} (error: {e})")

    return {
        "success": True,
        "files_read": files_read,
        "line_count": len(result_lines),
        "content": "\n".join(result_lines[-lines:]),
    }


# Common error patterns
ERROR_PATTERNS = [
    (r'(?i)error[:\s](.+)', "error"),
    (r'(?i)exception[:\s](.+)', "exception"),
    (r'(?i)traceback\s*\(most recent call last\)', "traceback"),
    (r'(?i)failed[:\s](.+)', "failure"),
    (r'(?i)panic[:\s](.+)', "panic"),
    (r'(?i)fatal[:\s](.+)', "fatal"),
    (r'(?i)segfault|segmentation fault', "segfault"),
    (r'(?i)ECONNREFUSED|ECONNRESET|EPIPE', "connection_error"),
]


def analyze_logs(
    server_name: Optional[str] = None,
    pattern: Optional[str] = None,
) -> Dict[str, Any]:
    """Analyze logs for errors and patterns."""
    logs_result = get_server_logs(server_name, lines=500)
    if not logs_result.get("success"):
        return logs_result

    content = logs_result.get("content", "")
    lines = content.splitlines()

    errors: List[Dict[str, Any]] = []
    pattern_matches: List[str] = []

    for line in lines:
        for ep, category in ERROR_PATTERNS:
            m = re.search(ep, line)
            if m:
                errors.append({
                    "category": category,
                    "line": line.strip()[:200],
                    "match": m.group(0)[:100],
                })
                break

        if pattern:
            if re.search(pattern, line, re.IGNORECASE):
                pattern_matches.append(line.strip()[:200])

    # Summarize errors
    categories: Dict[str, int] = {}
    for e in errors:
        cat = e["category"]
        categories[cat] = categories.get(cat, 0) + 1

    return {
        "success": True,
        "total_lines": len(lines),
        "error_count": len(errors),
        "error_categories": categories,
        "recent_errors": errors[-20:],
        "pattern_matches": pattern_matches[-20:] if pattern else [],
    }


def search_logs(
    server_name: Optional[str] = None,
    pattern: str = "",
    lines: int = 200,
) -> Dict[str, Any]:
    """Search logs for a specific pattern."""
    logs_result = get_server_logs(server_name, lines=lines)
    if not logs_result.get("success"):
        return logs_result

    content = logs_result.get("content", "")
    matching = []
    for line in content.splitlines():
        if re.search(pattern, line, re.IGNORECASE):
            matching.append(line.strip()[:300])

    return {
        "success": True,
        "pattern": pattern,
        "match_count": len(matching),
        "matches": matching[-50:],
    }
