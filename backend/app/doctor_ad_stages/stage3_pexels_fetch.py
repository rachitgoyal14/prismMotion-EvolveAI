"""
Stage 3 Doctor Ad: Handle logo scene (no Pexels fetching needed).
Logo will be handled in rendering stage using uploaded company logo.
"""
from pathlib import Path
from app.utils.pexels_client import get_media_for_scene, download_media
from app.paths import OUTPUTS_DIR

import logging
logger = logging.getLogger(__name__)

VIDEOS_DIR = OUTPUTS_DIR / "videos"


def fetch_pexels_closing(pexels_query: str, video_id: str, scene_id: int) -> dict:
    """
    Fetch and download 1 Pexels asset for closing scene (prefer image for Manim integration).
    
    Args:
        pexels_query: Search query (e.g., "doctor consultation")
        video_id: Video ID
        scene_id: Scene ID
    
    Returns:
        dict with local paths:
        {
            "image": {"local_path": "...", "src": "..."},
            "video": {"local_path": "...", "src": "..."}  # Optional, but we prefer image
        }
    """
    logger.info(f"Fetching Pexels asset: '{pexels_query}'")
    
    # Download to videos/{video_id}/pexels/
    pexels_dir = VIDEOS_DIR / video_id / "pexels"
    pexels_dir.mkdir(parents=True, exist_ok=True)
    
    # Get media from Pexels (prefer image for easy Manim integration)
    media = get_media_for_scene([pexels_query], prefer_video=False)
    
    result = {"image": None, "video": None}
    
    # Download image (preferred)
    image = media.get("image")
    if image and image.get("src"):
        image_path = pexels_dir / f"scene_{scene_id}_image.jpg"
        if download_media(image["src"], image_path):
            result["image"] = {
                "local_path": str(image_path),
                "src": image["src"],
                "alt": image.get("alt", "")
            }
            logger.info(f"Downloaded Pexels image: {image_path.name}")
        else:
            logger.warning(f"Image download failed for scene {scene_id}")
    
    # Download video only as fallback
    video = media.get("video")
    if video and video.get("src") and not result["image"]:
        video_path = pexels_dir / f"scene_{scene_id}_video.mp4"
        if download_media(video["src"], video_path):
            result["video"] = {
                "local_path": str(video_path),
                "src": video["src"]
            }
            logger.info(f"Downloaded Pexels video: {video_path.name}")
        else:
            logger.warning(f"Video download failed for scene {scene_id}")
    
    if not result["image"] and not result["video"]:
        raise RuntimeError(f"Failed to download any Pexels media for query: {pexels_query}")
    
    return result


def run_stage3_pexels(scenes_data: dict, video_id: str, logo_path: str | None = None) -> dict:
    """
    Handle logo scene (no Pexels fetching needed).
    
    Args:
        scenes_data: Scene data with logo scene(s)
        video_id: Video ID
        logo_path: Path to uploaded company logo
    
    Returns:
        dict with logo information
    """
    scenes = scenes_data.get("scenes", [])
    
    # Find Logo scenes
    logo_scenes = [s for s in scenes if s.get("type") == "logo"]
    
    if not logo_scenes:
        logger.warning("No Logo scenes found")
        return {}
    
    logo_info = {}
    
    if logo_path:
        logger.info(f"Logo scene will use uploaded logo: {logo_path}")
        for scene in logo_scenes:
            scene_id = scene["scene_id"]
            logo_info[scene_id] = {
                "logo_path": logo_path,
                "tagline": scene.get("tagline", "")
            }
    else:
        logger.warning("No logo uploaded, logo scene will use placeholder")
        for scene in logo_scenes:
            scene_id = scene["scene_id"]
            logo_info[scene_id] = {
                "logo_path": None,
                "tagline": scene.get("tagline", "")
            }
    
    logger.info(f"Prepared logo info for {len(logo_info)} scene(s)")
    
    return logo_info