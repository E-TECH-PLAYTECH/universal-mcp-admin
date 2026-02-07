"""
export_manager.py - Export MCP server data for training LLMs and RAG systems

This module provides functionality to export server configurations, tool definitions,
source code, and metadata into formats suitable for:
- Training/fine-tuning local LLMs (JSONL format, Alpaca or conversational)
- Building RAG systems (chunked JSON with metadata, line-aware splitting)
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import config_manager
import mcp_manager
import resource_discovery
import tool_analyzer


# ============================================================================
# Data Gathering
# ============================================================================


def gather_server_data(server_name: Optional[str] = None) -> Dict[str, Any]:
    """
    Gather comprehensive data about MCP server(s).

    Args:
        server_name: Optional specific server name, or None for all servers

    Returns:
        Dictionary with 'export_timestamp' and 'servers' list.
        Each server entry has: name, config, source_file, source_code,
        language, tools, resources, prompts.
    """
    data: Dict[str, Any] = {
        "export_timestamp": datetime.now().isoformat(),
        "servers": [],
    }

    try:
        # Build a {name: config} mapping without redundant API calls.
        # get_server_config returns a raw dict (no "name" key);
        # list_mcp_servers returns dicts that include a "name" key.
        if server_name:
            config = config_manager.get_server_config(server_name)
            server_names = [server_name]
            configs_by_name: Dict[str, Any] = {server_name: config}
        else:
            servers_list = config_manager.list_mcp_servers()
            server_names = [s["name"] for s in servers_list]
            configs_by_name = {s["name"]: s for s in servers_list}

        for name in server_names:
            server_data: Dict[str, Any] = {
                "name": name,
                "config": configs_by_name[name],
            }

            try:
                source_code, source_path = mcp_manager.read_source_file(
                    name, max_chars=500000
                )
                extension = source_path.suffix
                server_data["source_file"] = str(source_path)
                server_data["source_code"] = source_code
                server_data["language"] = extension

                server_data["tools"] = tool_analyzer.list_tools_in_source(
                    source_code, extension
                )
                server_data["resources"] = resource_discovery.list_mcp_resources(
                    source_code, extension
                )
                server_data["prompts"] = resource_discovery.list_mcp_prompts(
                    source_code, extension
                )
            except Exception as e:
                server_data["source_error"] = f"Failed to read source: {e}"
                server_data.setdefault("tools", [])
                server_data.setdefault("resources", [])
                server_data.setdefault("prompts", [])

            data["servers"].append(server_data)

    except Exception as e:
        data["error"] = f"Failed to gather server data: {e}"

    return data


# ============================================================================
# Training Data Export (JSONL)
# ============================================================================


def _format_params(params: List[Dict[str, Any]]) -> str:
    """Format a parameter list into a readable string."""
    parts: List[str] = []
    for p in params:
        name = p.get("name", "")
        ptype = p.get("type", "")
        parts.append(f"{name}: {ptype}" if ptype else name)
    return ", ".join(parts) if parts else "none"


def _tool_signature(tool: Dict[str, Any]) -> str:
    """Build a human-readable signature string for a tool."""
    name = tool.get("name", "unknown")
    params_str = _format_params(tool.get("parameters", []))
    sig = f"{name}({params_str})"
    ret = tool.get("return_type", "")
    if ret:
        sig += f" -> {ret}"
    return sig


def _make_alpaca(instruction: str, output: str, inp: str = "") -> Dict[str, Any]:
    return {"instruction": instruction, "input": inp, "output": output}


def _make_conversational(user_msg: str, assistant_msg: str) -> Dict[str, Any]:
    return {
        "messages": [
            {"role": "user", "content": user_msg},
            {"role": "assistant", "content": assistant_msg},
        ]
    }


def _generate_training_lines(
    server: Dict[str, Any],
    include_examples: bool,
    fmt: str,
) -> List[Dict[str, Any]]:
    """Generate training lines for a single server."""
    lines: List[Dict[str, Any]] = []
    server_name = server["name"]
    tools = server.get("tools", [])

    def _emit(user_text: str, assistant_text: str) -> None:
        if fmt == "conversational":
            lines.append(_make_conversational(user_text, assistant_text))
        else:
            lines.append(_make_alpaca(user_text, assistant_text))

    # --- Tool definition Q&A ---
    for tool in tools:
        tool_name = tool.get("name", "unknown")
        sig = _tool_signature(tool)
        docstring = tool.get("docstring", "")
        params = tool.get("parameters", [])
        return_type = tool.get("return_type", "")

        # What does tool X do?
        answer = f"The tool '{sig}' is part of the '{server_name}' MCP server."
        if docstring:
            answer += f"\n\nDescription: {docstring}"
        if params:
            answer += (
                f"\n\nParameters: "
                f"{', '.join(p.get('name', '') for p in params)}"
            )
        if return_type:
            answer += f"\n\nReturns: {return_type}"
        _emit(f"What does the MCP tool '{tool_name}' do?", answer)

        # How do I use tool X?
        if include_examples and params:
            params_str = _format_params(params)
            usage = (
                f"To use {tool_name}, call it with the following parameters: "
                f"{params_str}."
            )
            if docstring:
                usage += f" {docstring}"
            _emit(f"How do I use {tool_name}?", usage)

        # What parameters does tool X accept?
        if params:
            param_details: List[str] = []
            for p in params:
                detail = p.get("name", "")
                if p.get("type"):
                    detail += f" ({p['type']})"
                param_details.append(detail)
            _emit(
                f"What parameters does {tool_name} accept?",
                f"{tool_name} accepts: {'; '.join(param_details)}.",
            )

    # --- Tool listing for this server ---
    if tools:
        tool_names = [t.get("name", "unknown") for t in tools]
        _emit(
            f"What tools does the '{server_name}' MCP server have?",
            f"The '{server_name}' server has {len(tools)} tools: "
            f"{', '.join(tool_names)}.",
        )

    # --- Server configuration ---
    config = server.get("config", {})
    command = config.get("command", "N/A")
    args = config.get("args", [])
    args_str = ", ".join(str(a) for a in args) if isinstance(args, list) else str(args)
    config_answer = (
        f"The '{server_name}' server is configured as follows:\n"
        f"- Command: {command}\n"
        f"- Arguments: {args_str}"
    )
    cwd = config.get("cwd")
    if cwd:
        config_answer += f"\n- Working Directory: {cwd}"
    _emit(
        f"What is the configuration for the '{server_name}' MCP server?",
        config_answer,
    )

    return lines


def export_training_data(
    output_path: str = "training_data.jsonl",
    server_name: Optional[str] = None,
    include_examples: bool = True,
    fmt: str = "alpaca",
) -> Dict[str, Any]:
    """
    Export data in JSONL format suitable for training/fine-tuning LLMs.

    Supported formats:
      - "alpaca":  {"instruction", "input", "output"}
      - "conversational":  {"messages": [{"role": ..., "content": ...}, ...]}

    Args:
        output_path: Path to output JSONL file
        server_name: Optional specific server, or None for all
        include_examples: Include usage-example lines
        fmt: "alpaca" or "conversational"

    Returns:
        Dict with success, output_file, lines_written, servers_exported
    """
    if fmt not in ("alpaca", "conversational"):
        return {
            "success": False,
            "error": f"Unknown format '{fmt}'. Use 'alpaca' or 'conversational'.",
        }

    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)

    data = gather_server_data(server_name)
    lines_written = 0

    try:
        with open(output_file, "w", encoding="utf-8") as f:
            for server in data.get("servers", []):
                if "source_error" in server and not server.get("tools"):
                    continue
                for line in _generate_training_lines(server, include_examples, fmt):
                    f.write(json.dumps(line, ensure_ascii=False) + "\n")
                    lines_written += 1

        return {
            "success": True,
            "output_file": str(output_file.resolve()),
            "lines_written": lines_written,
            "servers_exported": len(data.get("servers", [])),
            "format": fmt,
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "output_file": str(output_file),
            "lines_written": lines_written,
        }


# ============================================================================
# RAG Data Export (chunked JSON)
# ============================================================================


def _chunk_text_by_lines(
    text: str,
    chunk_size: int,
    chunk_overlap: int,
    metadata: Dict[str, Any],
    start_chunk_id: int = 0,
) -> List[Dict[str, Any]]:
    """
    Split *text* into overlapping chunks that break at newline boundaries.

    Args:
        text: The text to split
        chunk_size: Target max characters per chunk (must be > 0)
        chunk_overlap: Characters of overlap between chunks (must be < chunk_size)
        metadata: Metadata dict attached to every chunk
        start_chunk_id: First chunk_id value to use

    Returns:
        List of chunk dicts with chunk_id, content, metadata
    """
    if not text:
        return []

    # Small-enough text -> single chunk
    if len(text) <= chunk_size:
        return [
            {
                "chunk_id": start_chunk_id,
                "content": text,
                "metadata": metadata.copy(),
            }
        ]

    lines = text.split("\n")
    chunks: List[Dict[str, Any]] = []
    current_lines: List[str] = []
    current_size = 0
    cid = start_chunk_id

    for line in lines:
        line_len = len(line) + 1  # +1 for the newline we stripped
        # If a single line exceeds chunk_size, emit what we have then emit
        # the long line as its own chunk.
        if current_size + line_len > chunk_size and current_lines:
            chunk_text = "\n".join(current_lines)
            chunks.append(
                {
                    "chunk_id": cid,
                    "content": chunk_text,
                    "metadata": metadata.copy(),
                }
            )
            cid += 1

            # Build overlap: walk backwards through current_lines
            overlap_lines: List[str] = []
            overlap_size = 0
            for prev_line in reversed(current_lines):
                if overlap_size + len(prev_line) + 1 > chunk_overlap:
                    break
                overlap_lines.insert(0, prev_line)
                overlap_size += len(prev_line) + 1
            current_lines = overlap_lines
            current_size = overlap_size

        current_lines.append(line)
        current_size += line_len

    # Flush remaining lines
    if current_lines:
        chunk_text = "\n".join(current_lines)
        chunks.append(
            {
                "chunk_id": cid,
                "content": chunk_text,
                "metadata": metadata.copy(),
            }
        )

    return chunks


def export_rag_data(
    output_path: str = "rag_data.json",
    server_name: Optional[str] = None,
    chunk_size: int = 1000,
    chunk_overlap: int = 200,
) -> Dict[str, Any]:
    """
    Export data in chunked JSON format suitable for RAG systems.

    Each chunk includes content text and rich metadata (server name,
    tool name, type, source file, language, line numbers).

    Args:
        output_path: Path to output JSON file
        server_name: Optional specific server, or None for all
        chunk_size: Max characters per chunk (default 1000)
        chunk_overlap: Overlap between chunks (default 200, must be < chunk_size)

    Returns:
        Dict with success, output_file, chunks_created, servers_exported
    """
    # Input validation
    if chunk_size <= 0:
        return {"success": False, "error": "chunk_size must be > 0"}
    if chunk_overlap < 0:
        return {"success": False, "error": "chunk_overlap must be >= 0"}
    if chunk_overlap >= chunk_size:
        return {
            "success": False,
            "error": f"chunk_overlap ({chunk_overlap}) must be < chunk_size ({chunk_size})",
        }

    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)

    data = gather_server_data(server_name)
    all_chunks: List[Dict[str, Any]] = []
    next_id = 0  # monotonically increasing chunk id

    try:
        for server in data.get("servers", []):
            if "source_error" in server and not server.get("tools"):
                continue

            srv_name = server["name"]
            source_file = server.get("source_file", "")

            # --- Server configuration chunk ---
            config = server.get("config", {})
            args = config.get("args", [])
            args_str = (
                ", ".join(str(a) for a in args) if isinstance(args, list) else str(args)
            )
            config_text = (
                f"MCP Server Configuration: {srv_name}\n"
                f"Command: {config.get('command', 'N/A')}\n"
                f"Arguments: {args_str}\n"
            )
            cwd = config.get("cwd")
            if cwd:
                config_text += f"Working Directory: {cwd}\n"

            new_chunks = _chunk_text_by_lines(
                config_text,
                chunk_size,
                chunk_overlap,
                metadata={
                    "type": "server_config",
                    "server_name": srv_name,
                    "source_file": source_file,
                },
                start_chunk_id=next_id,
            )
            all_chunks.extend(new_chunks)
            next_id += len(new_chunks)

            # --- Tool definition chunks (one per tool when it fits) ---
            for tool in server.get("tools", []):
                tool_name = tool.get("name", "unknown")
                docstring = tool.get("docstring", "")
                params = tool.get("parameters", [])
                return_type = tool.get("return_type", "")

                tool_text = f"Tool: {tool_name}\nServer: {srv_name}\n"
                if docstring:
                    tool_text += f"Description: {docstring}\n"
                if params:
                    tool_text += "Parameters:\n"
                    for p in params:
                        pname = p.get("name", "")
                        ptype = p.get("type", "")
                        tool_text += f"  - {pname}"
                        if ptype:
                            tool_text += f" ({ptype})"
                        tool_text += "\n"
                if return_type:
                    tool_text += f"Returns: {return_type}\n"

                new_chunks = _chunk_text_by_lines(
                    tool_text,
                    chunk_size,
                    chunk_overlap,
                    metadata={
                        "type": "tool_definition",
                        "server_name": srv_name,
                        "tool_name": tool_name,
                        "source_file": source_file,
                        "line_start": tool.get("line_start"),
                        "line_end": tool.get("line_end"),
                    },
                    start_chunk_id=next_id,
                )
                all_chunks.extend(new_chunks)
                next_id += len(new_chunks)

            # --- Source code chunks ---
            source_code = server.get("source_code", "")
            if source_code:
                new_chunks = _chunk_text_by_lines(
                    source_code,
                    chunk_size,
                    chunk_overlap,
                    metadata={
                        "type": "source_code",
                        "server_name": srv_name,
                        "language": server.get("language", ""),
                        "source_file": source_file,
                    },
                    start_chunk_id=next_id,
                )
                all_chunks.extend(new_chunks)
                next_id += len(new_chunks)

            # --- Resource chunks ---
            for resource in server.get("resources", []):
                res_text = f"Resource: {resource.get('name', 'unknown')}\n"
                res_text += f"URI: {resource.get('uri', '')}\n"
                if resource.get("docstring"):
                    res_text += f"Description: {resource['docstring']}\n"

                new_chunks = _chunk_text_by_lines(
                    res_text,
                    chunk_size,
                    chunk_overlap,
                    metadata={
                        "type": "resource",
                        "server_name": srv_name,
                        "resource_name": resource.get("name", ""),
                        "resource_uri": resource.get("uri", ""),
                    },
                    start_chunk_id=next_id,
                )
                all_chunks.extend(new_chunks)
                next_id += len(new_chunks)

        # Write output
        output_data = {
            "export_timestamp": data.get("export_timestamp"),
            "chunk_count": len(all_chunks),
            "chunks": all_chunks,
        }
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)

        return {
            "success": True,
            "output_file": str(output_file.resolve()),
            "chunks_created": len(all_chunks),
            "servers_exported": len(data.get("servers", [])),
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "output_file": str(output_file),
            "chunks_created": len(all_chunks),
        }
