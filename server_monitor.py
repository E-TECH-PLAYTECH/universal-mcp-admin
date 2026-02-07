"""
server_monitor.py - Server lifecycle management: status checking, enable/disable, restart
"""

import os
import re
import signal
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional

import config_manager


def check_server_status(server_name: str) -> Dict[str, Any]:
    """
    Check if an MCP server is currently running.
    Checks the process table for matching command/args.
    """
    try:
        config = config_manager.get_server_config(server_name)
    except ValueError as e:
        return {"status": "not_configured", "message": str(e)}

    command = config.get("command", "")
    args = config.get("args", [])

    # Build search pattern from command + args
    search_terms = [command] + args[:2]

    try:
        proc = subprocess.run(
            ['ps', 'aux'],
            capture_output=True, text=True, timeout=10
        )
        output = proc.stdout
    except Exception as e:
        return {"status": "unknown", "message": f"Cannot check processes: {e}"}

    matching_lines = []
    for line in output.splitlines():
        matches = sum(1 for term in search_terms if term and term in line)
        if matches >= 2:  # At least 2 terms must match
            matching_lines.append(line.strip())

    if matching_lines:
        return {
            "status": "running",
            "server_name": server_name,
            "matches": matching_lines[:3],
        }
    else:
        return {
            "status": "stopped",
            "server_name": server_name,
            "message": f"No matching process found for {command} {' '.join(args[:3])}",
        }


def list_server_statuses() -> List[Dict[str, Any]]:
    """Check status of all configured MCP servers."""
    try:
        servers = config_manager.list_mcp_servers()
    except Exception as e:
        return [{"error": str(e)}]

    statuses = []
    for server in servers:
        status = check_server_status(server["name"])
        status["server_name"] = server["name"]
        statuses.append(status)
    return statuses


def enable_server(server_name: str) -> Dict[str, Any]:
    """Enable a server in the configuration."""
    try:
        config_manager.enable_server(server_name)
        return {
            "success": True,
            "message": f"Server '{server_name}' enabled",
        }
    except Exception as e:
        return {
            "success": False,
            "message": str(e),
        }


def disable_server(server_name: str) -> Dict[str, Any]:
    """Disable a server in the configuration."""
    try:
        removed = config_manager.disable_server(server_name)
        return {
            "success": True,
            "message": f"Server '{server_name}' disabled (config preserved)",
            "config": removed,
        }
    except Exception as e:
        return {
            "success": False,
            "message": str(e),
        }


def get_server_info(server_name: str) -> Dict[str, Any]:
    """Get comprehensive server information."""
    try:
        config = config_manager.get_server_config(server_name)
    except ValueError as e:
        return {"error": str(e)}

    status = check_server_status(server_name)

    info: Dict[str, Any] = {
        "server_name": server_name,
        "config": config,
        "status": status.get("status", "unknown"),
        "command": config.get("command", ""),
        "args": config.get("args", []),
    }

    cwd = config.get("cwd", "")
    if cwd:
        info["cwd"] = cwd
        info["cwd_exists"] = Path(cwd).is_dir()

    env = config.get("env", {})
    if env:
        info["env_vars"] = list(env.keys())

    return info
