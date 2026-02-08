"""
Stage 3 Doctor Ad: Handle product and logo scenes.
Product and logo will be handled in rendering stage using uploaded images.
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


def run_stage3_pexels(scenes_data: dict, video_id: str, logo_path: str | None = None, product_image_path: str | None = None) -> dict:
    """
    Handle product and logo scenes.
    
    Args:
        scenes_data: Scene data with product and logo scene(s)
        video_id: Video ID
        logo_path: Path to uploaded company logo
        product_image_path: Path to uploaded product image
    
    Returns:
        dict with product and logo information
    """
    scenes = scenes_data.get("scenes", [])
    
    # Find Product and Logo scenes
    product_scenes = [s for s in scenes if s.get("type") == "product"]
    logo_scenes = [s for s in scenes if s.get("type") == "logo"]
    
    scene_info = {}
    
    # Handle product scenes
    if product_scenes:
        if product_image_path:
            logger.info(f"Product scene will use uploaded product image: {product_image_path}")
            for scene in product_scenes:
                scene_id = scene["scene_id"]
                scene_info[scene_id] = {
                    "type": "product",
                    "product_image_path": product_image_path,
                    "product_name": scene.get("product_name", "")
                }
        else:
            logger.warning("No product image uploaded, product scene will use placeholder")
            for scene in product_scenes:
                scene_id = scene["scene_id"]
                scene_info[scene_id] = {
                    "type": "product",
                    "product_image_path": None,
                    "product_name": scene.get("product_name", "")
                }
    
    # Handle logo scenes
    if logo_scenes:
        if logo_path:
            logger.info(f"Logo scene will use uploaded logo: {logo_path}")
            for scene in logo_scenes:
                scene_id = scene["scene_id"]
                scene_info[scene_id] = {
                    "type": "logo",
                    "logo_path": logo_path,
                    "tagline": scene.get("tagline", "")
                }
        else:
            logger.warning("No logo uploaded, logo scene will use placeholder")
            for scene in logo_scenes:
                scene_id = scene["scene_id"]
                scene_info[scene_id] = {
                    "type": "logo",
                    "logo_path": None,
                    "tagline": scene.get("tagline", "")
                }
    
    logger.info(f"Prepared scene info for {len(scene_info)} scene(s) ({len(product_scenes)} product, {len(logo_scenes)} logo)")
    
    return scene_info