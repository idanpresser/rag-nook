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
            A ScanResult object.

        Raises:
            FileNotFoundError: If the directory does not exist or has no chat log file.
        """
        # Skeleton implementation that will fail the tests
        raise NotImplementedError("This is a skeleton for TDD Red stage.")
