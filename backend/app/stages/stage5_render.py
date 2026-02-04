"""
Stage 5: Render video using Remotion.
Uses npx remotion render with composition PharmaVideo and props from scenes_with_media + script.
"""
import json
import subprocess
from pathlib import Path

from app.paths import OUTPUTS_DIR, REMOTION_DIR

VIDEOS_DIR = OUTPUTS_DIR / "videos"


def render_remotion(video_id: str) -> Path:
    """
    Load scenes_with_media + script, build props, run remotion render.
    Output: outputs/videos/<video_id>/final.mp4
    """
    import shutil

    print("node:", shutil.which("node"))
    print("npx:", shutil.which("npx"))
    print("npm:", shutil.which("npm"))

    scenes_path = OUTPUTS_DIR / "scenes_with_media.json"
    script_path = OUTPUTS_DIR / "script.json"
    if not scenes_path.exists():
        raise FileNotFoundError("Run stage2 first: scenes_with_media.json not found")
    if not script_path.exists():
        raise FileNotFoundError("Run stage3 first: script.json not found")

    scenes_data = json.loads(scenes_path.read_text(encoding="utf-8"))
    script_data = json.loads(script_path.read_text(encoding="utf-8"))
    script_map = {s["scene_id"]: s["script"] for s in script_data}

    scenes = scenes_data.get("scenes", [])
    props_scenes = []
    for s in scenes:
        sid = s.get("scene_id")
        entry = {
            "scene_id": sid,
            "duration_sec": s.get("duration_sec", 6),
            "concept": s.get("concept", ""),
            "script": script_map.get(sid, ""),
            "image": s.get("image") or (s.get("pexels_image") and {"src": s["pexels_image"].get("src"), "alt": s["pexels_image"].get("alt")}) or {"src": "", "alt": ""},
            "video": (s.get("video") or (s.get("pexels_video") and {"src": s["pexels_video"].get("src")})) if s.get("pexels_video") else None,
        }
        props_scenes.append(entry)

    props = {"scenes": props_scenes}
    out_dir = VIDEOS_DIR / video_id
    out_dir.mkdir(parents=True, exist_ok=True)
    final_path = out_dir / "final.mp4"

    cmd = [
        "npx.cmd",
        "remotion",
        "render",
        "src/index.ts",
        "PharmaVideo",
        str(final_path),
        "--props",
        json.dumps(props),
    ]
    print("REMOTION_DIR exists:", REMOTION_DIR, REMOTION_DIR.exists())

    subprocess.run(
        cmd,
        cwd=REMOTION_DIR,
        check=True,
    )
    return final_path
