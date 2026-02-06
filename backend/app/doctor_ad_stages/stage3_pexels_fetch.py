"""
Stage 3 Doctor Ad: Fetch single Pexels asset for closing scene.
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


def run_stage3_pexels(scenes_data: dict, video_id: str) -> dict:
    """
    Fetch Pexels asset for the closing scene.
    
    Args:
        scenes_data: Scene data with pexels scene(s)
        video_id: Video ID
    
    Returns:
        dict mapping scene_id to pexels media paths
    """
    scenes = scenes_data.get("scenes", [])
    
    # Find Pexels scenes
    pexels_scenes = [s for s in scenes if s.get("type") == "pexels"]
    
    if not pexels_scenes:
        logger.warning("No Pexels scenes found")
        return {}
    
    pexels_media = {}
    
    for scene in pexels_scenes:
        scene_id = scene["scene_id"]
        query = scene.get("pexels_query", "doctor consultation")
        
        try:
            media = fetch_pexels_closing(query, video_id, scene_id)
            pexels_media[scene_id] = media
        except Exception as e:
            logger.error(f"Failed to fetch Pexels for scene {scene_id}: {e}")
            continue
    
    logger.info(f"Fetched Pexels media for {len(pexels_media)} scene(s)")
    
    return pexels_media