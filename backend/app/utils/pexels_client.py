"""
Pexels API client for searching photos and videos.
https://www.pexels.com/api/documentation/
"""
import os
import httpx

PEXELS_API = "https://api.pexels.com"


def _get_headers():
    key = os.getenv("PEXELS_API_KEY")
    if not key:
        raise RuntimeError("PEXELS_API_KEY not set")
    return {"Authorization": key}


def search_photos(query: str, per_page: int = 5) -> list[dict]:
    """Search photos. Returns list of { id, src (medium), photographer, alt }."""
    with httpx.Client() as client:
        r = client.get(
            f"{PEXELS_API}/v1/search",
            params={"query": query, "per_page": per_page},
            headers=_get_headers(),
        )
        r.raise_for_status()
        data = r.json()
    return [
        {
            "id": p["id"],
            "src": p["src"].get("medium") or p["src"].get("large") or p["url"],
            "photographer": p.get("photographer", ""),
            "alt": p.get("alt", query),
        }
        for p in data.get("photos", [])
    ]


def search_videos(query: str, per_page: int = 3) -> list[dict]:
    """Search videos. Returns list of { id, video_files (best quality URL), user, duration }."""
    with httpx.Client() as client:
        r = client.get(
            f"{PEXELS_API}/videos/search",
            params={"query": query, "per_page": per_page},
            headers=_get_headers(),
        )
        r.raise_for_status()
        data = r.json()
    out = []
    for v in data.get("videos", []):
        files = v.get("video_files", [])
        best = None
        for f in files:
            if f.get("quality") == "hd" and f.get("width", 0) >= 1280:
                best = f.get("link")
                break
        if not best and files:
            best = files[0].get("link")
        if best:
            out.append({
                "id": v["id"],
                "src": best,
                "user": v.get("user", {}).get("name", ""),
                "duration": v.get("duration", 0),
            })
    return out


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
