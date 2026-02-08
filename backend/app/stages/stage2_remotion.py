"""
Stage 2: Fetch Pexels media per scene, then have LLM generate Remotion TSX composition.
"""
import json
from pathlib import Path
from typing import Optional

from app.paths import PROMPTS_DIR, OUTPUTS_DIR, REMOTION_DIR
from app.utils.json_safe import extract_json
from app.utils.llm import call_llm
from app.utils.pexels_client import get_media_for_scene
from app.utils.pexels_client import download_media
from app.utils.media_validator import validate_scene_media, validate_media_aspect_ratio
import shutil
import logging
logger = logging.getLogger(__name__)

VIDEOS_DIR = OUTPUTS_DIR / "videos"

def copy_uploaded_assets_to_remotion(video_id: str, assets: Optional[dict]):
    """
    Copy uploaded assets into Remotion public folder
    so staticFile() can access them.
    """
    if not assets:
        return {"logos": [], "images": []}

    src_base = VIDEOS_DIR / video_id / "assets"
    dest_base = REMOTION_DIR / "public" / "assets" / video_id

    dest_base.mkdir(parents=True, exist_ok=True)

    result = {"logos": [], "images": []}

    for category in ["logos", "images"]:
        src_dir = src_base / category
        dest_dir = dest_base / category

        if not src_dir.exists():
            continue

        dest_dir.mkdir(parents=True, exist_ok=True)

        for file in src_dir.iterdir():
            dest_file = dest_dir / file.name
            shutil.copy2(file, dest_file)


            # Path relative to remotion/public
            result[category].append(
                f"assets/{video_id}/{category}/{file.name}"
            )

    logger.info(f"Copied uploaded assets to Remotion public: {result}")
    return result


def enrich_scenes_with_media(scenes_data: dict, video_id: str, region: Optional[str] = None) -> dict:
    """
    For each scene, fetch and DOWNLOAD one landscape-aspect-ratio image (and optionally video) from Pexels.
    Strictly rejects portrait/vertical media and uses landscape fallback searches.
    If region is provided, applies regional demographic context to search terms.
    """
    from app.utils.pexels_client import search_photos, search_videos
    from app.utils.region_mapper import apply_region_to_search_terms
    
    scenes = scenes_data.get("scenes", [])
    
    # Download to remotion/public/media/{video_id}/ so Remotion can access via staticFile()
    media_dir = REMOTION_DIR / "public" / "media" / video_id
    media_dir.mkdir(parents=True, exist_ok=True)
    
    # Fallback generic search terms for when specific terms don't work
    FALLBACK_IMAGE_TERMS = ["landscape", "horizontal", "wide format", "banner"]
    FALLBACK_VIDEO_TERMS = ["landscape video", "horizontal motion", "widescreen"]
    
    for s in scenes:
        scene_id = s['scene_id']
        terms = s.get("pexels_search_terms", [s.get("concept", "pharmaceutical")])
        if isinstance(terms, str):
            terms = [terms]
        
        # Apply regional demographic context to search terms
        if region:
            terms = apply_region_to_search_terms(terms, region)
            logger.info(f"Scene {scene_id}: Applied region '{region}' to search terms: {terms}")
        
        logger.info(f"Scene {scene_id}: Fetching landscape media for {terms}")
        
        # ============ FETCH IMAGE ============
        image = None
        image_tried_fallback = False
        for attempt, search_term in enumerate(terms, 1):
            logger.info(f"Scene {scene_id}: [Image] Attempt {attempt} with term: {search_term}")
            candidates = search_photos(search_term, per_page=5)
            
            for candidate in candidates:
                w = candidate.get("width", 0)
                h = candidate.get("height", 0)
                is_valid_landscape = w > 0 and h > 0 and w >= h
                aspect = w / h if h > 0 else 0
                
                status = "✓ VALID" if is_valid_landscape else "✗ PORTRAIT"
                logger.info(f"Scene {scene_id}: Image {w}x{h} (AR: {aspect:.2f}) - {status}")
                
                if is_valid_landscape:
                    image = candidate
                    break
            
            if image:
                break
        
        # Fallback: try generic landscape terms if specific search didn't work
        if not image and not image_tried_fallback:
            logger.warning(f"Scene {scene_id}: No landscape image found (attempt 1), trying fallback terms")
            image_tried_fallback = True
            for search_term in FALLBACK_IMAGE_TERMS:
                logger.info(f"Scene {scene_id}: [Image Fallback] Trying: {search_term}")
                candidates = search_photos(search_term, per_page=3)
                
                for candidate in candidates:
                    w = candidate.get("width", 0)
                    h = candidate.get("height", 0)
                    is_valid_landscape = w > 0 and h > 0 and w >= h
                    
                    if is_valid_landscape:
                        logger.info(f"Scene {scene_id}: Using fallback image {w}x{h}")
                        image = candidate
                        break
                
                if image:
                    break
        
        # Download validated image
        if image and image.get("src"):
            image_path = media_dir / f"scene_{scene_id}_image.jpg"
            if download_media(image["src"], image_path):
                # Double-check downloaded image
                is_valid, w, h = validate_media_aspect_ratio(image_path, "image") if image_path.exists() else (True, 0, 0)
                if is_valid or (w == 0 and h == 0):  # Allow if we can't check
                    image["local_src"] = f"media/{video_id}/scene_{scene_id}_image.jpg"
                    logger.info(f"Scene {scene_id}: ✓ Image downloaded and validated")
                else:
                    logger.error(f"Scene {scene_id}: Downloaded image FAILED validation ({w}x{h}) - REMOVING")
                    image_path.unlink(missing_ok=True)
                    image = None
            else:
                logger.warning(f"Scene {scene_id}: Image download failed")
                image = None
        
        if not image:
            logger.error(f"Scene {scene_id}: ✗✗ NO VALID LANDSCAPE IMAGE FOUND ✗✗")
        
        # ============ FETCH VIDEO ============
        video = None
        for attempt, search_term in enumerate(terms, 1):
            logger.info(f"Scene {scene_id}: [Video] Attempt {attempt} with term: {search_term}")
            candidates = search_videos(search_term, per_page=3)
            
            for candidate in candidates:
                w = candidate.get("width", 0)
                h = candidate.get("height", 0)
                is_valid_landscape = w > 0 and h > 0 and w >= h
                aspect = w / h if h > 0 else 0
                
                status = "✓ VALID" if is_valid_landscape else "✗ PORTRAIT"
                logger.info(f"Scene {scene_id}: Video {w}x{h} (AR: {aspect:.2f}) - {status}")
                
                if is_valid_landscape:
                    video = candidate
                    break
            
            if video:
                break
        
        # Fallback: try generic landscape terms if specific search didn't work
        if not video:
            logger.warning(f"Scene {scene_id}: No landscape video found (attempt 1), trying fallback terms")
            for search_term in FALLBACK_VIDEO_TERMS:
                logger.info(f"Scene {scene_id}: [Video Fallback] Trying: {search_term}")
                candidates = search_videos(search_term, per_page=2)
                
                for candidate in candidates:
                    w = candidate.get("width", 0)
                    h = candidate.get("height", 0)
                    is_valid_landscape = w > 0 and h > 0 and w >= h
                    
                    if is_valid_landscape:
                        logger.info(f"Scene {scene_id}: Using fallback video {w}x{h}")
                        video = candidate
                        break
                
                if video:
                    break
        
        # Download validated video
        if video and video.get("src"):
            video_path = media_dir / f"scene_{scene_id}_video.mp4"
            if download_media(video["src"], video_path):
                # Double-check downloaded video
                is_valid, w, h = validate_media_aspect_ratio(video_path, "video") if video_path.exists() else (True, 0, 0)
                if is_valid or (w == 0 and h == 0):  # Allow if we can't check
                    video["local_src"] = f"media/{video_id}/scene_{scene_id}_video.mp4"
                    logger.info(f"Scene {scene_id}: ✓ Video downloaded and validated")
                else:
                    logger.error(f"Scene {scene_id}: Downloaded video FAILED validation ({w}x{h}) - REMOVING")
                    video_path.unlink(missing_ok=True)
                    video = None
            else:
                logger.warning(f"Scene {scene_id}: Video download failed")
                video = None
        else:
            logger.debug(f"Scene {scene_id}: No landscape video available")
        
        s["pexels_image"] = image if image else None
        s["pexels_video"] = video if video else None
        
        if not image and not video:
            logger.error(f"Scene {scene_id}: ⚠️  WARNING: Scene has NO valid media! Video will have blank frame for this scene.")
    
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

def run_stage2(
    scenes_data: dict,
    script: list[dict],
    video_id: str,
    assets: Optional[dict] = None,
    region: Optional[str] = None,
) -> str:
    """
    Enrich scenes with Pexels media + uploaded assets.
    If region is provided, applies regional demographic context to media search.
    """

    # 1. Copy uploaded assets into Remotion
    remotion_assets = copy_uploaded_assets_to_remotion(video_id, assets)

    # 2. Enrich scenes with Pexels media (with optional region filtering)
    enriched = enrich_scenes_with_media(scenes_data, video_id, region=region)

    # 3. Attach branding assets globally
    enriched["branding"] = {
        "logos": remotion_assets.get("logos", []),
        "images": remotion_assets.get("images", []),
    }

    # 4. Persist JSON for Remotion render stage
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)

    (OUTPUTS_DIR / "scenes_with_media.json").write_text(
        json.dumps(enriched, indent=2),
        encoding="utf-8",
    )

    out_path = REMOTION_DIR / "src" / "PharmaVideo.tsx"

    return str(out_path)
