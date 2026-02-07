"""
Stage 3 Social Media: Fetch Pexels assets for social media video.
"""
from pathlib import Path
from app.utils.pexels_client import get_media_for_scene, download_media
from app.paths import OUTPUTS_DIR

import logging
logger = logging.getLogger(__name__)

VIDEOS_DIR = OUTPUTS_DIR / "videos"


def run_stage3_sm_pexels(scenes_data: dict, video_id: str) -> dict:
    """
    Fetch Pexels media for each scene.
    
    Args:
        scenes_data: Dict with scenes list
        video_id: Video ID
    
    Returns:
        Dict mapping scene_id to media dict with local paths
    """
    scenes = scenes_data.get("scenes", [])

    logger.info(f"Fetching Pexels assets for {len(scenes)} scenes")

    # Create media directory
    media_dir = VIDEOS_DIR / video_id / "pexels"
    media_dir.mkdir(parents=True, exist_ok=True)

    pexels_media = {}

    for scene in scenes:
        scene_id = scene.get("scene_id", 0)
        # Use per-scene search terms provided by the scene planner
        search_terms = scene.get("pexels_search_terms") or []

        # Fallback candidates: visual_description, concept
        if not search_terms:
            candidates = []
            if scene.get("visual_description"):
                candidates.append(scene.get("visual_description"))
            if scene.get("concept"):
                candidates.append(scene.get("concept"))
            # make short human-friendly terms
            search_terms = [c for c in candidates if c]

        try:
            logger.info(f"Scene {scene_id}: Fetching Pexels media for terms: {search_terms}")

            # Get media from Pexels API (function expects list[str])
            media = get_media_for_scene(search_terms, prefer_video=False)

            if not media or (not media.get("image") and not media.get("video")):
                logger.warning(f"Scene {scene_id}: No Pexels media found for '{search_terms}'")
                pexels_media[scene_id] = {}
                continue

            result = {"image": None, "video": None}

            # Download image (preferred)
            image = media.get("image")
            if image and image.get("src"):
                image_path = media_dir / f"scene_{scene_id}_image.jpg"
                if download_media(image["src"], image_path):
                    result["image"] = {
                        "local_path": str(image_path),
                        "src": image["src"],
                        "alt": image.get("alt", "")
                    }
                    logger.info(f"Scene {scene_id}: Downloaded image")

            # Download video as fallback
            video = media.get("video")
            if video and video.get("src") and not result["image"]:
                video_path = media_dir / f"scene_{scene_id}_video.mp4"
                if download_media(video["src"], video_path):
                    result["video"] = {
                        "local_path": str(video_path),
                        "src": video["src"]
                    }
                    logger.info(f"Scene {scene_id}: Downloaded video")

            pexels_media[scene_id] = result

        except Exception as e:
            logger.error(f"Scene {scene_id}: Pexels fetch failed - {e}")
            pexels_media[scene_id] = {}

    logger.info(f"Pexels fetch complete: {len(pexels_media)} scenes")
    return pexels_media
