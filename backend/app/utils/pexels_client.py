"""
Pexels API client for searching photos and videos.
https://www.pexels.com/api/documentation/
"""
import os
import httpx
from pathlib import Path
import logging
logger = logging.getLogger(__name__)
PEXELS_API = "https://api.pexels.com"

# Target aspect ratio for final video: 16:9 (1920x1080)
TARGET_ASPECT_RATIO = 16 / 9
ASPECT_RATIO_TOLERANCE = 0.2  # Allow ±20% tolerance from target


def _get_headers():
    key = os.getenv("PEXELS_API_KEY")
    if not key:
        raise RuntimeError("PEXELS_API_KEY not set")
    return {"Authorization": key}


def _is_landscape_aspect_ratio(width: int, height: int) -> bool:
    """Check if media has landscape aspect ratio (width >= height)."""
    if width <= 0 or height <= 0:
        return False
    return width >= height


def _get_aspect_ratio_score(width: int, height: int) -> float:
    """
    Calculate how close the aspect ratio is to 16:9.
    Score: 1.0 = perfect 16:9, lower = further away.
    """
    if width <= 0 or height <= 0:
        return 0.0
    aspect_ratio = width / height
    # Perfect score at 16:9 ≈ 1.777
    perfect_ratio = 16 / 9
    # Calculate difference
    ratio_diff = abs(aspect_ratio - perfect_ratio) / perfect_ratio
    # Clamp to 0-1 score (further from target = lower score)
    return max(0.0, 1.0 - ratio_diff)


def search_photos(query: str, per_page: int = 5) -> list[dict]:
    """
    Search photos with landscape aspect ratio filter.
    Returns list of { id, src (medium), photographer, alt, width, height }.
    Only returns landscape-oriented photos (width >= height).
    """
    with httpx.Client() as client:
        r = client.get(
            f"{PEXELS_API}/v1/search",
            params={"query": query, "per_page": per_page * 2},  # Fetch more to account for filtering
            headers=_get_headers(),
        )
        r.raise_for_status()
        data = r.json()
    
    results = []
    for p in data.get("photos", []):
        width = p.get("width", 0)
        height = p.get("height", 0)
        
        # Only accept landscape-oriented photos
        if not _is_landscape_aspect_ratio(width, height):
            logger.debug(f"Filtering out portrait photo {p['id']}: {width}x{height}")
            continue
        
        results.append({
            "id": p["id"],
            "src": p["src"].get("medium") or p["src"].get("large") or p["url"],
            "photographer": p.get("photographer", ""),
            "alt": p.get("alt", query),
            "width": width,
            "height": height,
            "aspect_ratio": width / height if height > 0 else 0,
        })
    
    # Sort by aspect ratio closeness to 16:9 (best matches first)
    results.sort(key=lambda x: _get_aspect_ratio_score(x["width"], x["height"]), reverse=True)
    
    logger.info(f"Found {len(results)} landscape photos for '{query}' (filtered from {len(data.get('photos', []))})")
    return results[:per_page]


def search_videos(query: str, per_page: int = 3) -> list[dict]:
    """
    Search videos with landscape aspect ratio filter.
    Returns list of { id, video_files (best quality URL), user, duration, width, height }.
    Only returns landscape-oriented videos (width >= height).
    """
    with httpx.Client() as client:
        r = client.get(
            f"{PEXELS_API}/videos/search",
            params={"query": query, "per_page": per_page * 2},  # Fetch more to account for filtering
            headers=_get_headers(),
        )
        r.raise_for_status()
        data = r.json()
    
    out = []
    for v in data.get("videos", []):
        files = v.get("video_files", [])
        best = None
        best_width = 0
        best_height = 0
        
        # Find best HD file with landscape aspect ratio
        for f in files:
            width = f.get("width", 0)
            height = f.get("height", 0)
            
            # Filter: landscape only
            if not _is_landscape_aspect_ratio(width, height):
                continue
            
            quality = f.get("quality", "")
            # Prefer HD quality, width >= 1280
            if quality == "hd" and width >= 1280 and f.get("link"):
                best = f.get("link")
                best_width = width
                best_height = height
                break
        
        # Fallback: accept any landscape video file if HD not found
        if not best:
            for f in files:
                width = f.get("width", 0)
                height = f.get("height", 0)
                
                if _is_landscape_aspect_ratio(width, height) and f.get("link"):
                    best = f.get("link")
                    best_width = width
                    best_height = height
                    break
        
        if best:
            out.append({
                "id": v["id"],
                "src": best,
                "user": v.get("user", {}).get("name", ""),
                "duration": v.get("duration", 0),
                "width": best_width,
                "height": best_height,
                "aspect_ratio": best_width / best_height if best_height > 0 else 0,
            })
        else:
            logger.debug(f"No landscape video found for id {v['id']}")
    
    # Sort by aspect ratio closeness to 16:9 (best matches first)
    out.sort(key=lambda x: _get_aspect_ratio_score(x["width"], x["height"]), reverse=True)
    
    logger.info(f"Found {len(out)} landscape videos for '{query}' (filtered from {len(data.get('videos', []))})")
    return out[:per_page]


def get_media_for_scene(search_terms: list[str], prefer_video: bool = False) -> dict:
    """
    Get one image and optionally one video for a scene.
    search_terms: list of query strings to try.
    Returns { "image": {...}, "video": {...} or None }.
    """
    image = None
    video = None
    for q in search_terms:
        if not image:
            photos = search_photos(q, per_page=1)
            if photos:
                image = photos[0]
        if prefer_video and not video:
            videos = search_videos(q, per_page=1)
            if videos:
                video = videos[0]
        if image and (not prefer_video or video):
            break
    return {"image": image, "video": video}


def download_media(url: str, dest_path: Path) -> bool:
    """Download a file from URL to dest_path. Returns True on success."""
    try:
        with httpx.Client() as client:
            with client.stream("GET", url) as r:  # Use stream() context manager
                r.raise_for_status()
                dest_path.parent.mkdir(parents=True, exist_ok=True)
                with open(dest_path, "wb") as f:
                    for chunk in r.iter_bytes(chunk_size=8192):
                        f.write(chunk)
        return True
    except Exception as e:
        logger.warning(f"Failed to download {url}: {e}")
        return False