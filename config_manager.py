"""
config_manager.py - Logic for editing claude_desktop_config.json
"""

import json
import os
import platform
from pathlib import Path
from typing import Dict, List, Optional, Any


def get_default_config_path() -> Path:
    """
    Get the default Claude Desktop config path based on the operating system.
    
    Returns:
        Path to the claude_desktop_config.json file
    """
    system = platform.system()
    
    if system == "Darwin":  # macOS
        return Path.home() / "Library" / "Application Support" / "Claude" / "claude_desktop_config.json"
    elif system == "Windows":
        appdata = os.getenv("APPDATA")
        if not appdata:
            raise ValueError("APPDATA environment variable not set on Windows")
        return Path(appdata) / "Claude" / "claude_desktop_config.json"
    else:  # Linux and others
        return Path.home() / ".config" / "Claude" / "claude_desktop_config.json"


def get_config_path() -> Path:
    """
    Get the configured or default Claude Desktop config path.
    
    Returns:
        Path to the claude_desktop_config.json file
    """
    # Check if custom path is set in environment
    custom_path = os.getenv("CLAUDE_CONFIG_PATH", "")
    if custom_path:
        return Path(custom_path)
    
    return get_default_config_path()


def read_config() -> Dict[str, Any]:
    """
    Read and parse the claude_desktop_config.json file.
    
    Returns:
        Dictionary containing the config data
        
    Raises:
        FileNotFoundError: If config file doesn't exist
        json.JSONDecodeError: If config file is not valid JSON
    """
    config_path = get_config_path()
    
    if not config_path.exists():
        raise FileNotFoundError(f"Claude Desktop config not found at: {config_path}")
    
    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)


def list_mcp_servers() -> List[Dict[str, Any]]:
    """
    List all MCP servers from the Claude Desktop config.
    
    Returns:
        List of server information dictionaries, each containing:
        - name: Server name
        - command: Command to run the server
        - args: Command arguments
        - cwd: Working directory (if specified)
        - env: Environment variables (if specified)
    """
    try:
        config = read_config()
    except (FileNotFoundError, json.JSONDecodeError) as e:
        raise ValueError(f"Failed to read config: {str(e)}")
    
    servers = []
    mcp_servers = config.get("mcpServers", {})
    
    for server_name, server_config in mcp_servers.items():
        server_info = {
            "name": server_name,
            "command": server_config.get("command", ""),
            "args": server_config.get("args", []),
        }
        
        # Add optional fields if present
        if "cwd" in server_config:
            server_info["cwd"] = server_config["cwd"]
        if "env" in server_config:
            server_info["env"] = server_config["env"]
        
        servers.append(server_info)
    
    return servers


def get_server_config(server_name: str) -> Dict[str, Any]:
    """
    Get the configuration for a specific MCP server.
    
    Args:
        server_name: Name of the server to retrieve
        
    Returns:
        Server configuration dictionary
        
    Raises:
        ValueError: If server not found in config
    """
    config = read_config()
    mcp_servers = config.get("mcpServers", {})
    
    if server_name not in mcp_servers:
        raise ValueError(f"Server '{server_name}' not found in config")
    
    return mcp_servers[server_name]


def write_config(config_data: Dict[str, Any]) -> None:
    """
    Write configuration data to claude_desktop_config.json.
    Creates a backup before writing.
    
    Args:
        config_data: Configuration dictionary to write
    """
    config_path = get_config_path()
    
    # Create backup if file exists
    if config_path.exists():
        backup_path = config_path.with_suffix(".json.bak")
        with open(config_path, "r", encoding="utf-8") as src:
            with open(backup_path, "w", encoding="utf-8") as dst:
                dst.write(src.read())
    
    # Write new config
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(config_data, f, indent=2, ensure_ascii=False)


def update_server_config(server_name: str, updates: Dict[str, Any]) -> None:
    """
    Update configuration for a specific MCP server.
    
    Args:
        server_name: Name of the server to update
        updates: Dictionary of fields to update
    """
    config = read_config()
    
    if "mcpServers" not in config:
        config["mcpServers"] = {}
    
    if server_name not in config["mcpServers"]:
        config["mcpServers"][server_name] = {}
    
    config["mcpServers"][server_name].update(updates)
    write_config(config)


def validate_server_config(config: Dict[str, Any]) -> tuple:
    """
    Validate a server configuration structure.
    
    Args:
        config: Server configuration dictionary to validate
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not isinstance(config, dict):
        return False, "Config must be a dictionary"
    
    if "command" not in config or not config["command"]:
        return False, "Config must have a 'command' field"
    
    if "args" in config and not isinstance(config["args"], list):
        return False, "'args' must be a list"
    
    if "env" in config and not isinstance(config["env"], dict):
        return False, "'env' must be a dictionary"
    
    return True, ""


def add_server_config(
    server_name: str,
    command: str,
    args: Optional[List[str]] = None,
    cwd: Optional[str] = None,
    env: Optional[Dict[str, str]] = None
) -> None:
    """
    Add a new MCP server to the configuration.
    
    Args:
        server_name: Unique name for the server
        command: Command to run the server
        args: Command arguments
        cwd: Working directory
        env: Environment variables
        
    Raises:
        ValueError: If server already exists or config is invalid
    """
    config = read_config()
    
    if "mcpServers" not in config:
        config["mcpServers"] = {}
    
    if server_name in config["mcpServers"]:
        raise ValueError(f"Server '{server_name}' already exists in config")
    
    server_config: Dict[str, Any] = {"command": command}
    
    if args is not None:
        server_config["args"] = args
    if cwd is not None:
        server_config["cwd"] = cwd
    if env is not None:
        server_config["env"] = env
    
    is_valid, error = validate_server_config(server_config)
    if not is_valid:
        raise ValueError(f"Invalid server config: {error}")
    
    config["mcpServers"][server_name] = server_config
    write_config(config)


def remove_server_config(server_name: str) -> Dict[str, Any]:
    """
    Remove an MCP server from the configuration.
    
    Args:
        server_name: Name of the server to remove
        
    Returns:
        The removed server configuration
        
    Raises:
        ValueError: If server not found in config
    """
    config = read_config()
    mcp_servers = config.get("mcpServers", {})
    
    if server_name not in mcp_servers:
        raise ValueError(f"Server '{server_name}' not found in config")
    
    removed_config = mcp_servers.pop(server_name)
    write_config(config)
    return removed_config


def enable_server(server_name: str, server_config: Optional[Dict[str, Any]] = None) -> None:
    """
    Enable a server by adding it to the active config.
    If server_config is provided, use it; otherwise look in disabled servers.
    
    Args:
        server_name: Name of the server to enable
        server_config: Optional config to use for the server
    """
    config = read_config()
    
    if "mcpServers" not in config:
        config["mcpServers"] = {}
    
    disabled = config.get("_disabledServers", {})
    
    if server_name in config["mcpServers"]:
        return  # Already enabled
    
    if server_config:
        config["mcpServers"][server_name] = server_config
    elif server_name in disabled:
        config["mcpServers"][server_name] = disabled.pop(server_name)
    else:
        raise ValueError(f"No config found for server '{server_name}'")
    
    write_config(config)


def disable_server(server_name: str) -> Dict[str, Any]:
    """
    Disable a server by moving it from active to disabled list.
    
    Args:
        server_name: Name of the server to disable
        
    Returns:
        The disabled server configuration
    """
    config = read_config()
    mcp_servers = config.get("mcpServers", {})
    
    if server_name not in mcp_servers:
        raise ValueError(f"Server '{server_name}' not found in config")
    
    if "_disabledServers" not in config:
        config["_disabledServers"] = {}
    
    config["_disabledServers"][server_name] = mcp_servers.pop(server_name)
    write_config(config)
    return config["_disabledServers"][server_name]
