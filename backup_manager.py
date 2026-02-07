"""
backup_manager.py - Backup tracking, restoration, and checkpoint system
"""

import difflib
import json
import os
import shutil
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


class BackupManager:
    """
    Track backups with metadata, support restoration and checkpoints.
    """

    def __init__(self, registry_file: Optional[Path] = None):
        if registry_file is None:
            cache_dir = Path.home() / ".cache" / "universal-mcp-admin"
            cache_dir.mkdir(parents=True, exist_ok=True)
            registry_file = cache_dir / "backups.json"
        self.registry_file = Path(registry_file)
        self._registry: Dict[str, Any] = self._load_registry()

    def _load_registry(self) -> Dict[str, Any]:
        if self.registry_file.exists():
            try:
                with open(self.registry_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except (json.JSONDecodeError, Exception):
                return {"backups": [], "checkpoints": []}
        return {"backups": [], "checkpoints": []}

    def _save_registry(self) -> None:
        try:
            self.registry_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.registry_file, 'w', encoding='utf-8') as f:
                json.dump(self._registry, f, indent=2)
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Backup tracking
    # ------------------------------------------------------------------

    def register_backup(
        self,
        file_path: str,
        backup_path: str,
        operation: str,
        server_name: Optional[str] = None,
        tool_name: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Register a backup in the registry and return its id."""
        backup_id = str(uuid.uuid4())[:8]
        entry = {
            "id": backup_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "file_path": str(file_path),
            "backup_path": str(backup_path),
            "operation": operation,
            "server_name": server_name,
            "tool_name": tool_name,
            "metadata": metadata or {},
        }
        self._registry.setdefault("backups", []).append(entry)
        self._save_registry()
        return backup_id

    def list_backups(
        self,
        file_path: Optional[str] = None,
        server_name: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Return backups filtered by file_path or server_name, newest first."""
        backups = self._registry.get("backups", [])
        if file_path:
            backups = [b for b in backups if b.get("file_path") == str(file_path)]
        if server_name:
            backups = [b for b in backups if b.get("server_name") == server_name]
        return sorted(backups, key=lambda b: b.get("timestamp", ""), reverse=True)

    def get_backup_metadata(self, backup_id: str) -> Optional[Dict[str, Any]]:
        """Get metadata for a specific backup."""
        for b in self._registry.get("backups", []):
            if b.get("id") == backup_id:
                return b
        return None

    # ------------------------------------------------------------------
    # Restoration
    # ------------------------------------------------------------------

    def restore_backup(
        self, backup_id: str, target_path: Optional[str] = None
    ) -> Tuple[bool, str]:
        """Restore a file from a backup. Creates a safety backup of current file first."""
        entry = self.get_backup_metadata(backup_id)
        if entry is None:
            return False, f"Backup '{backup_id}' not found in registry"

        backup_path = Path(entry["backup_path"])
        if not backup_path.exists():
            return False, f"Backup file not found: {backup_path}"

        dest = Path(target_path) if target_path else Path(entry["file_path"])

        # Safety backup of current file
        if dest.exists():
            safety_bak = dest.with_suffix(dest.suffix + ".pre-restore.bak")
            shutil.copy2(dest, safety_bak)

        shutil.copy2(backup_path, dest)
        return True, f"Restored from backup '{backup_id}' to {dest}"

    # ------------------------------------------------------------------
    # Cleanup
    # ------------------------------------------------------------------

    def cleanup_backups(
        self, older_than_days: int = 30, keep_recent: int = 10
    ) -> Tuple[int, int]:
        """Remove old backup files and registry entries. Returns (removed, kept)."""
        cutoff = datetime.now(timezone.utc) - timedelta(days=older_than_days)
        backups = self._registry.get("backups", [])
        # group by file_path
        by_file: Dict[str, List[Dict[str, Any]]] = {}
        for b in backups:
            by_file.setdefault(b.get("file_path", ""), []).append(b)

        keep_ids = set()
        for fp, entries in by_file.items():
            entries.sort(key=lambda b: b.get("timestamp", ""), reverse=True)
            for i, entry in enumerate(entries):
                if i < keep_recent:
                    keep_ids.add(entry["id"])
                    continue
                ts_str = entry.get("timestamp", "")
                try:
                    ts = datetime.fromisoformat(ts_str.rstrip("Z"))
                    if ts >= cutoff:
                        keep_ids.add(entry["id"])
                except Exception:
                    keep_ids.add(entry["id"])

        removed = 0
        new_backups = []
        for b in backups:
            if b["id"] in keep_ids:
                new_backups.append(b)
            else:
                bp = Path(b.get("backup_path", ""))
                if bp.exists():
                    try:
                        bp.unlink()
                    except Exception:
                        pass
                removed += 1

        self._registry["backups"] = new_backups
        self._save_registry()
        return removed, len(new_backups)

    # ------------------------------------------------------------------
    # Diff
    # ------------------------------------------------------------------

    def diff_backup(self, backup_id: str) -> Tuple[bool, str]:
        """Return a unified diff between backup and current file."""
        entry = self.get_backup_metadata(backup_id)
        if entry is None:
            return False, f"Backup '{backup_id}' not found"

        backup_path = Path(entry["backup_path"])
        current_path = Path(entry["file_path"])

        if not backup_path.exists():
            return False, f"Backup file missing: {backup_path}"
        if not current_path.exists():
            return False, f"Current file missing: {current_path}"

        with open(backup_path, 'r', encoding='utf-8') as f:
            old_lines = f.readlines()
        with open(current_path, 'r', encoding='utf-8') as f:
            new_lines = f.readlines()

        diff = difflib.unified_diff(
            old_lines, new_lines,
            fromfile=f"backup ({entry['id']})",
            tofile="current",
        )
        return True, "".join(diff) or "(no differences)"

    # ------------------------------------------------------------------
    # Checkpoints
    # ------------------------------------------------------------------

    def create_checkpoint(
        self,
        server_name: str,
        description: str,
        file_paths: List[str],
    ) -> str:
        """Create a named checkpoint (snapshot of multiple files)."""
        checkpoint_id = str(uuid.uuid4())[:8]
        checkpoint_dir = self.registry_file.parent / "checkpoints" / checkpoint_id
        checkpoint_dir.mkdir(parents=True, exist_ok=True)

        saved_files = []
        for fp in file_paths:
            p = Path(fp)
            if p.exists():
                dest = checkpoint_dir / p.name
                shutil.copy2(p, dest)
                saved_files.append({"original": str(p), "saved": str(dest)})

        entry = {
            "id": checkpoint_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "server_name": server_name,
            "description": description,
            "files": saved_files,
        }
        self._registry.setdefault("checkpoints", []).append(entry)
        self._save_registry()
        return checkpoint_id

    def list_checkpoints(self, server_name: Optional[str] = None) -> List[Dict[str, Any]]:
        """List checkpoints, optionally filtered by server."""
        cps = self._registry.get("checkpoints", [])
        if server_name:
            cps = [c for c in cps if c.get("server_name") == server_name]
        return sorted(cps, key=lambda c: c.get("timestamp", ""), reverse=True)

    def restore_checkpoint(self, checkpoint_id: str) -> Tuple[bool, str]:
        """Restore all files from a checkpoint."""
        for cp in self._registry.get("checkpoints", []):
            if cp.get("id") == checkpoint_id:
                restored = []
                for f in cp.get("files", []):
                    src = Path(f["saved"])
                    dest = Path(f["original"])
                    if src.exists():
                        if dest.exists():
                            safety = dest.with_suffix(dest.suffix + ".pre-restore.bak")
                            shutil.copy2(dest, safety)
                        shutil.copy2(src, dest)
                        restored.append(str(dest))
                return True, f"Restored {len(restored)} files from checkpoint '{checkpoint_id}'"
        return False, f"Checkpoint '{checkpoint_id}' not found"


# Global instance
_backup_manager: Optional[BackupManager] = None


def get_backup_manager() -> BackupManager:
    """Get or create the global BackupManager instance."""
    global _backup_manager
    if _backup_manager is None:
        _backup_manager = BackupManager()
    return _backup_manager
