"""
Stage 5: Render video using Remotion.
Uses npx remotion render with composition PharmaVideo and props from scenes_with_media + script.
"""
import json
import shutil
import subprocess
from pathlib import Path
import logging
logger = logging.getLogger(__name__)

from app.paths import OUTPUTS_DIR, REMOTION_DIR

VIDEOS_DIR = OUTPUTS_DIR / "videos"
AUDIO_DIR = OUTPUTS_DIR / "audio"
MEDIA_PUBLIC_ROOT = REMOTION_DIR / "public" / "media"


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

    # Copy media into Remotion public folder
    # Resulting structure:
    #   remotion/public/media/<video_id>/scene_<id>_image.jpg or _video.mp4
    media_public_dir = MEDIA_PUBLIC_ROOT / video_id
    media_public_dir.mkdir(parents=True, exist_ok=True)

    for s in scenes:
        sid = s.get("scene_id")
        # Source WAV generated in stage4
        source_audio = AUDIO_DIR / video_id / f"scene_{sid}.wav"

        # Destination inside Remotion public dir (if source exists)
        audio_rel_path = None
        if source_audio.exists():
            dest_audio = public_audio_root / f"scene_{sid}.wav"
            # Copy or overwrite to ensure latest audio is available
            shutil.copy2(source_audio, dest_audio)
            # This relative path is what <Audio src={staticFile(...)} /> will receive.
            audio_rel_path = f"audio/{video_id}/scene_{sid}.wav"

        # Copy image if local exists, else fallback to remote
        image = s.get("pexels_image") or {}
        source_image = Path(image.get("local_src")) if image.get("local_src") else None
        image_rel_path = None
        image_alt = image.get("alt", "")
        if source_image and source_image.exists():
            dest_image = media_public_dir / source_image.name
            shutil.copy2(source_image, dest_image)
            image_rel_path = f"media/{video_id}/{source_image.name}"
        elif image.get("src"):
            logger.warning(f"Using remote image for scene {sid}")
            image_rel_path = image["src"]  # Requires --enable-remote-media

        # Copy video if local exists, else fallback to remote
        video = s.get("pexels_video") or {}
        source_video = Path(video.get("local_src")) if video.get("local_src") else None
        video_rel_path = None
        if source_video and source_video.exists():
            dest_video = media_public_dir / source_video.name
            shutil.copy2(source_video, dest_video)
            video_rel_path = f"media/{video_id}/{source_video.name}"
        elif video.get("src"):
            logger.warning(f"Using remote video for scene {sid}")
            video_rel_path = video["src"]

        entry = {
            "scene_id": sid,
            "duration_sec": s.get("duration_sec", 6),
            "concept": s.get("concept", ""),
            "script": script_map.get(sid, ""),
            "image": {"src": image_rel_path, "alt": image_alt} if image_rel_path else None,
            "video": {"src": video_rel_path} if video_rel_path else None,
            # Relative path under remotion/public; consumed via staticFile() in PharmaVideo.tsx
            "audio_src": audio_rel_path,
        }
        props_scenes.append(entry)

    props = {"scenes": props_scenes}
    out_dir = VIDEOS_DIR / video_id
    out_dir.mkdir(parents=True, exist_ok=True)
    # Write props to a file to avoid Windows CLI JSON escaping issues.
    props_path = out_dir / "props.json"
    props_path.write_text(json.dumps(props, ensure_ascii=False), encoding="utf-8")
    final_path = out_dir / "final.mp4"

    npx_cmd = shutil.which("npx")
    if npx_cmd is None:
        raise RuntimeError("npx not found in PATH. Ensure Node.js is installed and in your PATH.")

    cmd = [
        "npx",  # This works cross-platform; subprocess will resolve .cmd on Windows if needed
        "remotion",
        "render",
        "src/index.ts",
        "PharmaVideo",
        str(final_path),
        f"--props={props_path}",
        "--enable-remote-media",  # Keep for remote fallbacks; remove if no remotes expected
        "--codec=h264",
        "--audio-codec=aac",
    ]

    subprocess.run(
        cmd,
        cwd=REMOTION_DIR,
        check=True,
    )
    return final_path