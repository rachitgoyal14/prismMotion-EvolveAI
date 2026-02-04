"""
Stage 2: Fetch Pexels media per scene, then have LLM generate Remotion TSX composition.
"""
import json
from pathlib import Path

from app.paths import PROMPTS_DIR, OUTPUTS_DIR, REMOTION_DIR
from app.utils.json_safe import extract_json
from app.utils.llm import call_llm
from app.utils.pexels_client import get_media_for_scene


def enrich_scenes_with_media(scenes_data: dict) -> dict:
    """For each scene, fetch one image (and optionally video) from Pexels using scene's search terms."""
    scenes = scenes_data.get("scenes", [])
    for s in scenes:
        terms = s.get("pexels_search_terms", [s.get("concept", "pharmaceutical")])
        if isinstance(terms, str):
            terms = [terms]
        media = get_media_for_scene(terms, prefer_video=True)
        s["pexels_image"] = media["image"]
        s["pexels_video"] = media["video"]
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
        # Normalize for JSON (no non-serializable)
        if s.get("pexels_image"):
            s["image"] = {"src": s["pexels_image"].get("src", ""), "alt": s["pexels_image"].get("alt", "")}
        else:
            s["image"] = {"src": "", "alt": ""}
        if s.get("pexels_video"):
            s["video"] = {"src": s["pexels_video"].get("src", "")}
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


def run_stage2(scenes_data: dict, script: list[dict]) -> str:
    """
    Enrich scenes with Pexels media, generate TSX, write to remotion/src/PharmaVideo.tsx.
    Returns path to the written TSX file.
    """
    enriched = enrich_scenes_with_media(scenes_data)
    tsx_code = generate_remotion_tsx(enriched, script)
    out_path = REMOTION_DIR / "src" / "PharmaVideo.tsx"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(tsx_code, encoding="utf-8")
    # Also persist enriched scenes + script for render stage
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    (OUTPUTS_DIR / "scenes_with_media.json").write_text(
        json.dumps(enriched, indent=2), encoding="utf-8"
    )
    return str(out_path)
