"""
Stage 2: Fetch Pexels media per scene, then have LLM generate Remotion TSX composition.
"""
import json
from pathlib import Path

from app.paths import PROMPTS_DIR, OUTPUTS_DIR, REMOTION_DIR
from app.utils.json_safe import extract_json
from app.utils.llm import call_llm
from app.utils.pexels_client import get_media_for_scene
from app.utils.pexels_client import download_media

import logging
logger = logging.getLogger(__name__)

VIDEOS_DIR = OUTPUTS_DIR / "videos"

def enrich_scenes_with_media(scenes_data: dict, video_id: str) -> dict:
    """For each scene, fetch and DOWNLOAD one image (and optionally video) from Pexels."""
    scenes = scenes_data.get("scenes", [])
    
    # Download to remotion/public/media/{video_id}/ so Remotion can access via staticFile()
    media_dir = REMOTION_DIR / "public" / "media" / video_id
    media_dir.mkdir(parents=True, exist_ok=True)
    
    for s in scenes:
        terms = s.get("pexels_search_terms", [s.get("concept", "pharmaceutical")])
        if isinstance(terms, str):
            terms = [terms]
        media = get_media_for_scene(terms, prefer_video=True)
        
        # Download image
        image = media["image"]
        if image and image.get("src"):
            image_path = media_dir / f"scene_{s['scene_id']}_image.jpg"
            if download_media(image["src"], image_path):
                # Store relative path from public/ folder for staticFile()
                image["local_src"] = f"media/{video_id}/scene_{s['scene_id']}_image.jpg"
                logger.info(f"Downloaded image for scene {s['scene_id']}: {image['local_src']}")
            else:
                logger.warning(f"Image download failed for scene {s['scene_id']}; using remote as fallback")
                image["local_src"] = image["src"]  # Fallback to remote URL
        
        # Download video
        video = media["video"]
        if video and video.get("src"):
            video_path = media_dir / f"scene_{s['scene_id']}_video.mp4"
            if download_media(video["src"], video_path):
                # Store relative path from public/ folder for staticFile()
                video["local_src"] = f"media/{video_id}/scene_{s['scene_id']}_video.mp4"
                logger.info(f"Downloaded video for scene {s['scene_id']}: {video['local_src']}")
            else:
                logger.warning(f"Video download failed for scene {s['scene_id']}; using remote as fallback")
                video["local_src"] = video["src"]  # Fallback to remote URL
        
        s["pexels_image"] = image
        s["pexels_video"] = video
    
    return scenes_data

def generate_remotion_tsx(scenes_with_media: dict, script_per_scene: list[dict]) -> str:
    """Merge script into scenes and have LLM generate TSX code."""
    script_map = {
        s["scene_id"]: s["script"]
        for s in script_per_scene
    }
    scenes = scenes_with_media.get("scenes", [])
    for s in scenes:
        sid = s.get("scene_id")
        s["script"] = script_map.get(sid, "")
        
        # Use LOCAL paths (relative to public/) instead of remote URLs
        if s.get("pexels_image") and s["pexels_image"].get("local_src"):
            s["image"] = {
                "src": s["pexels_image"]["local_src"],  # ✅ Use local path
                "alt": s["pexels_image"].get("alt", "")
            }
        else:
            s["image"] = {"src": "", "alt": ""}
            
        if s.get("pexels_video") and s["pexels_video"].get("local_src"):
            s["video"] = {
                "src": s["pexels_video"]["local_src"]  # ✅ Use local path
            }
        else:
            s["video"] = None
            
    payload = {"video_type": scenes_with_media.get("video_type"), "scenes": scenes}
    prompt_path = PROMPTS_DIR / "remotion_composition.txt"
    prompt = prompt_path.read_text(encoding="utf-8").replace(
        "{scenes_with_media_json}", json.dumps(payload, indent=2)
    )
    output = call_llm(prompt)
    data = extract_json(output)
    return data.get("tsx_code", "").strip()

def run_stage2(scenes_data: dict, script: list[dict], video_id: str) -> str:
    """
    Enrich scenes with Pexels media and persist JSON outputs for downstream stages.

    Note: We intentionally do NOT overwrite `remotion/src/PharmaVideo.tsx` here.
    Using an LLM-generated TSX proved brittle (black frames, props mismatches, missing audio).
    Keep the Remotion composition stable and drive it via props + JSON instead.
    """
    enriched = enrich_scenes_with_media(scenes_data, video_id)
    out_path = REMOTION_DIR / "src" / "PharmaVideo.tsx"
    # Also persist enriched scenes + script for render stage
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    (OUTPUTS_DIR / "scenes_with_media.json").write_text(
        json.dumps(enriched, indent=2), encoding="utf-8"
    )
    return str(out_path)