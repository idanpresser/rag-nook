import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Union

@dataclass
class ScanResult:
    """Dataclass holding the result of a local directory scan."""
    chat_log_path: Path
    media_files: List[Path] = field(default_factory=list)
    vcard_files: List[Path] = field(default_factory=list)


class LocalFolderScanner:
    """Scans local directories for WhatsApp chat logs and associated multimodal attachments."""

    def scan(self, directory_path: Union[str, Path]) -> ScanResult:
        """Scans the directory for chat logs and associated .jpg, .png, .heic, and .vcf files.

        Args:
            directory_path: The directory path to scan.

        Returns:
            A ScanResult object containing paths to the chat log, media files, and vCards.

        Raises:
            FileNotFoundError: If the directory does not exist or has no chat log file.
        """
        dir_path = Path(directory_path).resolve()
        
        if not dir_path.exists() or not dir_path.is_dir():
            raise FileNotFoundError(f"Directory does not exist: {dir_path}")

        # List all files in the immediate directory
        all_files = [f for f in dir_path.iterdir() if f.is_file()]

        # Identify chat log (.txt files)
        txt_files = [f for f in all_files if f.suffix.lower() == ".txt"]
        
        chat_log_path = None
        if len(txt_files) == 1:
            chat_log_path = txt_files[0]
        elif len(txt_files) > 1:
            # Look for a file whose name contains "chat" or "whatsapp" (case-insensitive)
            for f in txt_files:
                if "chat" in f.name.lower() or "whatsapp" in f.name.lower():
                    chat_log_path = f
                    break
            # Fallback to the first text file if no match
            if not chat_log_path:
                chat_log_path = txt_files[0]
        else:
            raise FileNotFoundError(f"No chat log file found in directory: {dir_path}")

        # Classify media and vcard files by extension
        media_files: List[Path] = []
        vcard_files: List[Path] = []

        media_extensions = {".jpg", ".jpeg", ".png", ".heic"}
        
        for f in all_files:
            suffix = f.suffix.lower()
            if suffix in media_extensions:
                media_files.append(f)
            elif suffix == ".vcf":
                vcard_files.append(f)

        # Sort paths to ensure deterministic order
        media_files.sort()
        vcard_files.sort()

        return ScanResult(
            chat_log_path=chat_log_path,
            media_files=media_files,
            vcard_files=vcard_files
        )
