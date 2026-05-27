from pathlib import Path
from typing import Union

class MediaOptimizer:
    """Optimizes local images into highly compressed formats and generates thumbnails."""

    def optimize_image(self, input_path: Union[str, Path]) -> Path:
        """Optimizes a local image file and saves it under output/optimized_media/.

        Args:
            input_path: Path to the input image file.

        Returns:
            The Path to the optimized AVIF file.

        Raises:
            FileNotFoundError: If the input file does not exist.
            NotImplementedError: Raised during the TDD Red stage.
        """
        raise NotImplementedError("This is a skeleton for TDD Red stage.")

    def generate_thumbnail_base64(self, image_path: Union[str, Path]) -> str:
        """Generates a low-res base64 string thumbnail of the image.

        Args:
            image_path: Path to the image file.

        Returns:
            A base64 data URL string representing the thumbnail.

        Raises:
            NotImplementedError: Raised during the TDD Red stage.
        """
        raise NotImplementedError("This is a skeleton for TDD Red stage.")
