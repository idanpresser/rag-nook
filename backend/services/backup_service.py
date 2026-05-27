import os
import shutil
import datetime
from pathlib import Path
from typing import List, Dict, Any
from config import config

class ChromaBackupService:
    def __init__(self, backup_dir: Path = None):
        if backup_dir is None:
            self.backup_dir = config.output_dir / "backups"
        else:
            self.backup_dir = backup_dir

    def create_backup(self, label: str = None) -> str:
        """Copies output/vector_db recursively to output/backups/<timestamp>_<label>."""
        if not config.vector_db_dir.exists():
            raise FileNotFoundError("Active vector database directory does not exist to backup.")

        self.backup_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        # Sanitize label
        clean_label = "".join(c for c in (label or "snapshot") if c.isalnum() or c in ("-", "_")).strip()
        backup_name = f"{timestamp}_{clean_label}"
        target_path = self.backup_dir / backup_name

        shutil.copytree(config.vector_db_dir, target_path)
        return backup_name

    def list_backups(self) -> List[Dict[str, Any]]:
        """Scans backups directory and returns structured metadata including human-readable sizes."""
        if not self.backup_dir.exists():
            return []

        backups = []
        for path in self.backup_dir.iterdir():
            if path.is_dir():
                # Parse timestamp and label
                parts = path.name.split("_", 2)
                timestamp_str = "N/A"
                label = path.name
                if len(parts) >= 2:
                    try:
                        ts = parts[0] + "_" + parts[1]
                        dt = datetime.datetime.strptime(ts, "%Y%m%d_%H%M%S")
                        timestamp_str = dt.strftime("%Y-%m-%d %H:%M:%S")
                        label = parts[2] if len(parts) > 2 else "snapshot"
                    except ValueError:
                        pass
                
                # Calculate size on disk
                total_size = 0
                for root, dirs, files in os.walk(path):
                    for f in files:
                        fp = os.path.join(root, f)
                        total_size += os.path.getsize(fp)
                
                size_str = self._format_size(total_size)

                backups.append({
                    "name": path.name,
                    "label": label,
                    "created_at": timestamp_str,
                    "size_bytes": total_size,
                    "size_str": size_str
                })
        
        backups.sort(key=lambda x: x["name"], reverse=True)
        return backups

    def restore_backup(self, name: str) -> None:
        """Safely removes the active output/vector_db folder and replaces it with the target backup."""
        target_path = self.backup_dir / name
        if not target_path.exists():
            raise FileNotFoundError(f"Backup snapshot '{name}' does not exist.")

        # Wipe current active vector database directory
        if config.vector_db_dir.exists():
            shutil.rmtree(config.vector_db_dir)

        # Restore from snapshot
        shutil.copytree(target_path, config.vector_db_dir)

    def delete_backup(self, name: str) -> None:
        """Permanently removes the target backup directory."""
        target_path = self.backup_dir / name
        if not target_path.exists():
            raise FileNotFoundError(f"Backup snapshot '{name}' does not exist.")
        
        shutil.rmtree(target_path)

    def _format_size(self, size_bytes: int) -> str:
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.1f} TB"

backup_service = ChromaBackupService()
