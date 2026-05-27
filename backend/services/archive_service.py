import os
import shutil
import zipfile
import tempfile
from pathlib import Path
from config import config

class ArchiveService:
    def __init__(self):
        self.output_dir = config.output_dir
        self.chat_path = config.chat_file_path

    def export_archive(self, target_zip_path: Path) -> None:
        """Zips the raw chat log, scraped markdown files/images, Chroma database, and pipeline state."""
        # Create parent directory if needed
        target_zip_path.parent.mkdir(parents=True, exist_ok=True)
        
        with zipfile.ZipFile(target_zip_path, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            # 1. Zip the raw chat log if it exists
            if self.chat_path.exists():
                zip_file.write(self.chat_path, arcname=self.chat_path.name)
                
            # 2. Zip the entire output directory recursively
            if self.output_dir.exists():
                for root, dirs, files in os.walk(self.output_dir):
                    root_path = Path(root)
                    
                    # Exclude the "backups" directory to avoid huge nested sizes
                    if "backups" in root_path.parts:
                        continue
                    # Exclude the "temp" directory where the active download is being compiled
                    if "temp" in root_path.parts:
                        continue
                        
                    for file in files:
                        file_path = root_path / file
                        # Create relative path inside the zip, mirroring config.output_dir
                        rel_path = file_path.relative_to(self.output_dir.parent)
                        zip_file.write(file_path, arcname=str(rel_path))

    def import_archive(self, zip_path: Path) -> None:
        """Safely extracts a zipped archive, replacing active chat logs, scrapings, Chroma databases, and metadata."""
        if not zipfile.is_zipfile(zip_path):
            raise ValueError("The uploaded file is not a valid zip archive.")

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Extract to temporary directory to validate structure
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(temp_path)
                
            # Validate presence of at least chat.txt or output directory
            chat_exists = (temp_path / "chat.txt").exists()
            output_exists = (temp_path / "output").exists()
            
            if not chat_exists and not output_exists:
                raise ValueError("Archive is missing required memory base files (chat.txt or output/).")
                
            # 1. Restore chat.txt
            if chat_exists:
                if self.chat_path.exists():
                    self.chat_path.unlink()
                shutil.copy2(temp_path / "chat.txt", self.chat_path)
                
            # 2. Restore output directory
            if output_exists:
                # Wipe current active directories EXCEPT output/backups to keep snapshot history!
                if self.output_dir.exists():
                    for path in self.output_dir.iterdir():
                        if path.name == "backups":
                            continue
                        if path.name == "temp":
                            continue
                        if path.is_dir():
                            shutil.rmtree(path)
                        else:
                            path.unlink()
                else:
                    self.output_dir.mkdir(parents=True, exist_ok=True)
                    
                # Replicate files from temp path to output path
                temp_output = temp_path / "output"
                for item in temp_output.iterdir():
                    if item.name == "backups":
                        continue
                    if item.name == "temp":
                        continue
                    dest = self.output_dir / item.name
                    if item.is_dir():
                        shutil.copytree(item, dest)
                    else:
                        shutil.copy2(item, dest)

archive_service = ArchiveService()
