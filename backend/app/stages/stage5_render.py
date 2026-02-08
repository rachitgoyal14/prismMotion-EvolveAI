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
    Load scenes_with_media + script + animations, build props, run remotion render.
    Output: outputs/videos/<video_id>/final.mp4
    """
    scenes_path = OUTPUTS_DIR / "scenes_with_media.json"
    script_path = OUTPUTS_DIR / "script.json"
    animations_path = OUTPUTS_DIR / "animations.json"
    
    if not scenes_path.exists():
        raise FileNotFoundError("Run stage2 first: scenes_with_media.json not found")
    if not script_path.exists():
        raise FileNotFoundError("Run stage3 first: script.json not found")

    scenes_data = json.loads(scenes_path.read_text(encoding="utf-8"))
    script_data = json.loads(script_path.read_text(encoding="utf-8"))
    script_map = {s["scene_id"]: s["script"] for s in script_data}
    
    # Load animations if available (optional)
    animations_map = {}
    if animations_path.exists():
        animations_data = json.loads(animations_path.read_text(encoding="utf-8"))
        animations_map = animations_data.get("animations", {})
        logger.info(f"Loaded animations for {len(animations_map)} scenes")
    else:
        logger.info("No animations.json found - animations will not be applied")

    scenes = scenes_data.get("scenes", [])
    props_scenes = []
    branding = scenes_data.get("branding", {})



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
    # # ---------------- Branding Assets ----------------
    # branding_public_dir = REMOTION_DIR / "public" / "assets" / video_id
    # branding_public_dir.mkdir(parents=True, exist_ok=True)

    # branding_result = {"logos": [], "images": []}

    # for category in ["logos", "images"]:
    #     for asset_path in branding.get(category, []):

    #         # 🔥 FIX: resolve relative to OUTPUTS_DIR
    #         src = OUTPUTS_DIR / asset_path

    #         if not src.exists():
    #             logger.warning(f"Branding asset missing: {src}")
    #             continue

    #         dest_dir = branding_public_dir / category
    #         dest_dir.mkdir(parents=True, exist_ok=True)

    #         dest = dest_dir / src.name
    #         shutil.copy2(src, dest)

    #         branding_result[category].append(
    #             f"assets/{video_id}/{category}/{src.name}"
    #         )

    # logger.info(f"Branding assets copied: {branding_result}")
    # Branding already copied in Stage 2 — just pass through
    branding_result = scenes_data.get("branding", {"logos": [], "images": []})
    for category in ["logos", "images"]:
        branding_result[category] = [
            path for path in branding_result.get(category, [])
            if (REMOTION_DIR / "public" / path).exists()
    ]


    logger.info(f"Using branding from scenes JSON: {branding_result}")



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
            image_rel_path = None
            image_alt = image.get("alt", "")

            # Check if local_src exists (already in remotion/public/)
            if image.get("local_src"):
                source_image = REMOTION_DIR / "public" / image.get("local_src")
                if source_image.exists():
                    # File already exists in correct location, just use the relative path
                    image_rel_path = image.get("local_src")
                    logger.info(f"✓ Using local image for scene {sid}: {image_rel_path}")
                else:
                    logger.warning(f"Local image path specified but file not found: {source_image}")
                    # Fallback to remote if local file missing
                    if image.get("src"):
                        logger.warning(f"Using remote image for scene {sid}")
                        image_rel_path = image["src"]
            elif image.get("src"):
                logger.warning(f"Using remote image for scene {sid}")
                image_rel_path = image["src"]

            # Copy video if local exists, else fallback to remote
            video = s.get("pexels_video") or {}
            video_rel_path = None

            # Check if local_src exists (already in remotion/public/)
            if video.get("local_src"):
                source_video = REMOTION_DIR / "public" / video.get("local_src")
                if source_video.exists():
                    # File already exists in correct location, just use the relative path
                    video_rel_path = video.get("local_src")
                    logger.info(f"✓ Using local video for scene {sid}: {video_rel_path}")
                else:
                    logger.warning(f"Local video path specified but file not found: {source_video}")
                    # Fallback to remote if local file missing
                    if video.get("src"):
                        logger.warning(f"Using remote video for scene {sid}")
                        video_rel_path = video["src"]
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
        
        # Add animation metadata if available
        if str(sid) in animations_map:
            entry["animation"] = animations_map[str(sid)]
        elif sid in animations_map:
            entry["animation"] = animations_map[sid]
        
        props_scenes.append(entry)

    props = {"scenes": props_scenes, "branding": branding_result}
    out_dir = VIDEOS_DIR / video_id
    out_dir.mkdir(parents=True, exist_ok=True)
    # Write props to a file to avoid Windows CLI JSON escaping issues.
    props_path = out_dir / "props.json"
    props_path.write_text(json.dumps(props, ensure_ascii=False), encoding="utf-8")
    final_path = out_dir / "final.mp4"
   
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
        "--port=3000",
    ]

    subprocess.run(
        cmd,
        cwd=REMOTION_DIR,
        check=True,
    )
    return final_path