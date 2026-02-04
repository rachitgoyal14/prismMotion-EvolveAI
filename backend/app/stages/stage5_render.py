"""
Stage 5: Render video using Remotion.
Uses npx remotion render with composition PharmaVideo and props from scenes_with_media + script.
"""
import json
import shutil
import subprocess
from pathlib import Path

from app.paths import OUTPUTS_DIR, REMOTION_DIR

VIDEOS_DIR = OUTPUTS_DIR / "videos"
AUDIO_DIR = OUTPUTS_DIR / "audio"


def render_remotion(video_id: str) -> Path:
    """
    Load scenes_with_media + script, build props, run remotion render.
    Output: outputs/videos/<video_id>/final.mp4
    """
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

    # Copy audio into Remotion public folder so it can be served via staticFile().
    # Resulting structure:
    #   remotion/public/audio/<video_id>/scene_<id>.wav
    public_audio_root = REMOTION_DIR / "public" / "audio" / video_id
    public_audio_root.mkdir(parents=True, exist_ok=True)

    for s in scenes:
        sid = s.get("scene_id")
        # Source WAV generated in stage4
        source_audio = AUDIO_DIR / video_id / f"scene_{sid}.wav"

        # Destination inside Remotion public dir (if source exists)
        public_rel_path = None
        if source_audio.exists():
            dest_audio = public_audio_root / f"scene_{sid}.wav"
            # Copy or overwrite to ensure latest audio is available
            shutil.copy2(source_audio, dest_audio)
            # This relative path is what <Audio src={staticFile(...)} /> will receive.
            public_rel_path = f"audio/{video_id}/scene_{sid}.wav"

        entry = {
            "scene_id": sid,
            "duration_sec": s.get("duration_sec", 6),
            "concept": s.get("concept", ""),
            "script": script_map.get(sid, ""),
            "image": s.get("image")
            or (
                s.get("pexels_image")
                and {
                    "src": s["pexels_image"].get("src"),
                    "alt": s["pexels_image"].get("alt"),
                }
            )
            or {"src": "", "alt": ""},
            "video": (
                s.get("video")
                or (
                    s.get("pexels_video")
                    and {"src": s["pexels_video"].get("src")}
                )
            )
            if s.get("pexels_video")
            else None,
            # Relative path under remotion/public; consumed via staticFile() in PharmaVideo.tsx
            "audio_src": public_rel_path,
        }
        props_scenes.append(entry)

    props = {"scenes": props_scenes}
    out_dir = VIDEOS_DIR / video_id
    out_dir.mkdir(parents=True, exist_ok=True)
    # Write props to a file to avoid Windows CLI JSON escaping issues.
    props_path = out_dir / "props.json"
    props_path.write_text(json.dumps(props, ensure_ascii=False), encoding="utf-8")
    final_path = out_dir / "final.mp4"

    cmd = [
        "npx.cmd",
        "remotion",
        "render",
        "src/index.ts",
        "PharmaVideo",
        str(final_path),
        f"--props={props_path}",
        "--enable-remote-media",
        "--codec=h264",
        "--audio-codec=aac",
    ]

    subprocess.run(
        cmd,
        cwd=REMOTION_DIR,
        check=True,
    )
    return final_path
