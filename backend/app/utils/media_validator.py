"""
Media validation utilities for aspect ratio checking.
Ensures downloaded images and videos match the target landscape aspect ratio.
"""
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# Target: 16:9 landscape (1920x1080)
TARGET_ASPECT_RATIO = 16 / 9
ASPECT_RATIO_TOLERANCE = 0.3  # Allow ratios from roughly 4:3 to 21:9


def get_image_dimensions(image_path: Path) -> tuple[int, int] | None:
    """
    Get image dimensions (width, height) without loading entire image into memory.
    Supports JPEG, PNG, GIF, WebP.
    Returns (width, height) or None if unable to determine.
    """
    try:
        from PIL import Image
        with Image.open(image_path) as img:
            w, h = img.width, img.height
            logger.debug(f"Image dimensions: {w}x{h}")
            return w, h
    except ImportError:
        logger.warning("Pillow not installed - cannot validate image dimensions. Install with: pip install Pillow")
        return None
    except Exception as e:
        logger.warning(f"Failed to get image dimensions for {image_path}: {e}")
        return None


def get_video_dimensions(video_path: Path) -> tuple[int, int] | None:
    """
    Get video dimensions (width, height) using ffprobe.
    Returns (width, height) or None if unable to determine.
    """
    try:
        import subprocess
        result = subprocess.run(
            [
                "ffprobe",
                "-v", "error",
                "-select_streams", "v:0",
                "-show_entries", "stream=width,height",
                "-of", "csv=p=0",
                str(video_path)
            ],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode == 0 and result.stdout.strip():
            parts = result.stdout.strip().split(',')
            if len(parts) >= 2:
                w, h = int(parts[0]), int(parts[1])
                logger.debug(f"Video dimensions: {w}x{h}")
                return w, h
    except FileNotFoundError:
        logger.debug("ffprobe not available - cannot validate video dimensions. Install FFmpeg for validation.")
    except Exception as e:
        logger.warning(f"Failed to get video dimensions for {video_path}: {e}")
    
    return None


def is_landscape_aspect(width: int, height: int) -> bool:
    """Check if aspect ratio is landscape (width >= height)."""
    return width >= height


def get_aspect_ratio(width: int, height: int) -> float:
    """Calculate aspect ratio (width/height)."""
    return width / height if height > 0 else 0


def validate_media_aspect_ratio(
    media_path: Path,
    media_type: str = "image"
) -> tuple[bool, int, int]:
    """
    Validate that downloaded media has landscape aspect ratio.
    
    Args:
        media_path: Path to image or video file
        media_type: "image" or "video"
    
    Returns:
        (is_valid, width, height) - dimensions return 0,0 if unable to check
    """
    if not media_path.exists():
        logger.warning(f"Media file not found: {media_path}")
        return False, 0, 0
    
    if media_type == "image":
        dims = get_image_dimensions(media_path)
    elif media_type == "video":
        dims = get_video_dimensions(media_path)
    else:
        logger.warning(f"Unknown media type: {media_type}")
        return False, 0, 0
    
    if not dims:
        logger.warning(f"Could not determine dimensions for {media_path} ({media_type})")
        return True, 0, 0  # Allow if we can't determine (assume it's OK)
    
    width, height = dims
    is_landscape = is_landscape_aspect(width, height)
    aspect_ratio = get_aspect_ratio(width, height)
    
    status = "✓ PASS" if is_landscape else "✗ FAIL"
    logger.info(f"{status}: {media_path.name} - {width}x{height} (AR: {aspect_ratio:.2f}, Target: 1.78)")
    
    return is_landscape, width, height


def validate_scene_media(
    image_path: Path | None,
    video_path: Path | None,
    scene_id: int
) -> bool:
    """
    Validate both image and video for a scene.
    Returns True if all present media is valid, False if any are invalid.
    """
    all_valid = True
    
    if image_path and image_path.exists():
        is_valid, w, h = validate_media_aspect_ratio(image_path, "image")
        if not is_valid:
            logger.error(f"Scene {scene_id}: Image {w}x{h} has INVALID aspect ratio (portrait/wrong orientation)")
            all_valid = False
        else:
            logger.info(f"Scene {scene_id}: Image {w}x{h} has VALID aspect ratio")
    
    if video_path and video_path.exists():
        is_valid, w, h = validate_media_aspect_ratio(video_path, "video")
        if not is_valid:
            logger.error(f"Scene {scene_id}: Video {w}x{h} has INVALID aspect ratio (portrait/wrong orientation)")
            all_valid = False
        else:
            logger.info(f"Scene {scene_id}: Video {w}x{h} has VALID aspect ratio")
    
    return all_valid
