from pathlib import Path
from typing import Union
from core.preprocessor import ContactMetadata

class VCardParser:
    """Parses .vcf (vCard) files to extract contact metadata."""

    def parse_file(self, filepath: Union[str, Path]) -> ContactMetadata:
        """Parses a vCard file to extract Full Name, Phone numbers, Emails, and Organization.

        Args:
            filepath: The path to the .vcf file.

        Returns:
            A ContactMetadata object.

        Raises:
            FileNotFoundError: If the file does not exist.
            NotImplementedError: Raised during the TDD Red stage.
        """
        raise NotImplementedError("This is a skeleton for TDD Red stage.")
