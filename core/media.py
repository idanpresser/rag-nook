import base64
from io import BytesIO
from pathlib import Path
from typing import Union
from PIL import Image

class MediaOptimizer:
    """Optimizes local images into highly compressed formats and generates thumbnails."""

    def __init__(self, output_dir: Union[str, Path] = "/Users/idaneyal/DEV/personal_momory/output/optimized_media"):
        self.output_dir = Path(output_dir)

    def optimize_image(self, input_path: Union[str, Path]) -> Path:
        """Optimizes a local image file and saves it under output/optimized_media/ as a .avif.

        Uses AVIF format if supported, falling back cleanly to WEBP or JPEG if the host lacks
        native AVIF compilers, ensuring cross-platform sandbox safety.

        Args:
            input_path: Path to the input image file.

        Returns:
            The Path to the optimized AVIF file.

        Raises:
            FileNotFoundError: If the input file does not exist.
        """
        in_path = Path(input_path).resolve()
        if not in_path.exists():
            raise FileNotFoundError(f"Input image not found: {in_path}")

        # Ensure output directory exists
        self.output_dir.mkdir(parents=True, exist_ok=True)
        out_path = self.output_dir / f"{in_path.stem}.avif"

        with Image.open(in_path) as img:
            # Convert RGBA/LA modes to RGB to avoid compatibility issues
            if img.mode in ("RGBA", "LA", "P"):
                img = img.convert("RGB")

            try:
                # Try saving in native AVIF format
                img.save(out_path, format="AVIF", quality=70)
            except Exception:
                # Fallback option 1: Save as WEBP under the .avif extension
                try:
                    img.save(out_path, format="WEBP", quality=75)
                except Exception:
                    # Fallback option 2: Save as JPEG under the .avif extension
                    img.save(out_path, format="JPEG", quality=75)

        return out_path

    def generate_thumbnail_base64(self, image_path: Union[str, Path], max_size=(100, 100)) -> str:
        """Generates a highly compressed low-res base64 string thumbnail of the image.

        Args:
            image_path: Path to the image file.
            max_size: Maximum width/height tuple for the thumbnail.

        Returns:
            A base64 data URL string representing the thumbnail.

        Raises:
            FileNotFoundError: If the image file does not exist.
        """
        path = Path(image_path).resolve()
        if not path.exists():
            raise FileNotFoundError(f"Image not found: {path}")

        with Image.open(path) as img:
            # Create a thumbnail keeping aspect ratio
            img.thumbnail(max_size)
            
            buffered = BytesIO()
            try:
                img.save(buffered, format="WEBP", quality=60)
                mime = "image/webp"
            except Exception:
                img.save(buffered, format="JPEG", quality=60)
                mime = "image/jpeg"

            img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")
            return f"data:{mime};base64,{img_str}"
