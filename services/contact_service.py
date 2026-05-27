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
            A ContactMetadata object containing the extracted properties.

        Raises:
            FileNotFoundError: If the file does not exist.
        """
        path = Path(filepath).resolve()
        if not path.exists():
            raise FileNotFoundError(f"vCard file not found: {path}")

        full_name = ""
        phones = []
        emails = []
        org = None

        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                line = line.strip()
                if not line or ":" not in line:
                    continue

                key_part, value = line.split(":", 1)
                value = value.strip()
                
                # Split off parameters (e.g. TEL;type=CELL -> TEL)
                key = key_part.split(";")[0].upper()

                if key == "FN":
                    full_name = value
                elif key == "TEL":
                    if value:
                        phones.append(value)
                elif key == "EMAIL":
                    if value:
                        emails.append(value)
                elif key == "ORG":
                    if value:
                        # Standard ORG field can have component divisions separated by semicolons
                        org = value.replace(";", " - ").strip() if ";" in value else value

        if not full_name:
            full_name = "Unknown Contact"

        return ContactMetadata(
            full_name=full_name,
            phones=phones,
            emails=emails,
            org=org
        )
