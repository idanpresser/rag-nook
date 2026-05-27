from pathlib import Path
from typing import Union

class OCRProcessor:
    """Extracts text content embedded in images using OCR."""

    def extract_text(self, image_path: Union[str, Path]) -> str:
        """Extracts text from the given image path.

        Args:
            image_path: Path to the image file.

        Returns:
            The extracted text string.

        Raises:
            FileNotFoundError: If the image file does not exist.
            NotImplementedError: Raised during the TDD Red stage.
        """
        raise NotImplementedError("This is a skeleton for TDD Red stage.")
