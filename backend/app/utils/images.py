"""Image validation, EXIF normalization, resizing, and WebP conversion utilities."""

from io import BytesIO
from PIL import Image, ImageOps, UnidentifiedImageError

from app.utils.errors import APIError

MAX_IMAGE_BYTES = 10 * 1024 * 1024  # 10 MB
MAX_DIMENSION_PX = 1200
ALLOWED_IMAGE_FORMATS = {"JPEG", "PNG", "WEBP"}


def process_uploaded_image(file_storage) -> bytes:
    """Validate an uploaded image, fix EXIF rotation, strip metadata, resize, and convert to WebP."""
    if file_storage is None:
        raise APIError(400, "INVALID_IMAGE", "No image file provided")

    raw_bytes = file_storage.read()
    if not raw_bytes:
        raise APIError(400, "INVALID_IMAGE", "Uploaded image file is empty")
    if len(raw_bytes) > MAX_IMAGE_BYTES:
        raise APIError(400, "FILE_TOO_LARGE", "Image exceeds 10 MB limit")

    try:
        with Image.open(BytesIO(raw_bytes)) as img:
            if img.format not in ALLOWED_IMAGE_FORMATS:
                raise APIError(
                    400,
                    "INVALID_IMAGE",
                    "Only JPEG, PNG, and WebP images are allowed",
                )

            # Fix smartphone camera orientation before stripping EXIF
            img = ImageOps.exif_transpose(img)

            # Normalize color mode so WebP encoding always succeeds cleanly
            if img.mode in ("RGBA", "LA") or (
                img.mode == "P" and "transparency" in img.info
            ):
                img = img.convert("RGBA")
            elif img.mode != "RGB":
                img = img.convert("RGB")

            # Resize proportionally so the longest side is at most 1200px
            img.thumbnail((MAX_DIMENSION_PX, MAX_DIMENSION_PX), Image.Resampling.LANCZOS)

            output = BytesIO()
            # Omitting exif= strips all EXIF/GPS metadata from the resulting WebP
            img.save(output, format="WEBP", quality=85)
            return output.getvalue()
    except APIError:
        raise
    except (UnidentifiedImageError, OSError):
        raise APIError(
            400,
            "INVALID_IMAGE",
            "Only JPEG, PNG, and WebP images are allowed",
        )
