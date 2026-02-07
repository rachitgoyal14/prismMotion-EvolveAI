# app/stages/stage5_render.py  (or create app/utils/video_utils.py and import from there)

import subprocess
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

def convert_to_portrait_9_16(
    input_video: Path,
    output_video: Path,
    quality: str = "high",
    target_width: int = 1080
) -> Path:
    if not input_video.exists():
        raise FileNotFoundError(f"Input video not found: {input_video}")

    quality_presets = {
        "low":    480,
        "medium": 720,
        "high":   1080,
    }
    width = quality_presets.get(quality, 1080)
    height = int(round(width * 16 / 9))

    # ────────────────────────────────────────────────
    # Main tunable parameters
    fg_scale_factor = 0.74          # 0.74–0.80 range – start with 0.76
    bg_blur_radius  = 60
    bg_blur_sigma   = 2
    bg_brightness   = -0.08
    bg_saturation   = 0.30
    # ────────────────────────────────────────────────

    fg_height = int(round(height * fg_scale_factor))

    filter_complex = (
        f"[0:v]scale={width}:{height}:force_original_aspect_ratio=increase,"
        f"crop={width}:{height},"
        f"boxblur={bg_blur_radius}:{bg_blur_sigma},"
        f"eq=brightness={bg_brightness}:saturation={bg_saturation}[bg];"
        f"[0:v]scale=-2:{fg_height}[fg];"
        f"[bg][fg]overlay=(main_w-overlay_w)/2:(main_h-overlay_h)/2"
    )

    cmd = [
        "ffmpeg", "-y",
        "-i", str(input_video),
        "-filter_complex", filter_complex,
        "-c:v", "libx264", "-crf", "22", "-preset", "medium",
        "-c:a", "aac", "-b:a", "128k",
        "-movflags", "+faststart",
        str(output_video)
    ]

    logger.info(f"Portrait conversion → {width}×{height}, fg_scale={fg_scale_factor}")
    logger.debug(f"Filter: {filter_complex}")

    try:
        subprocess.run(cmd, check=True, capture_output=True, timeout=600)
        return output_video
    except subprocess.CalledProcessError as e:
        logger.error(f"ffmpeg failed:\n{e.stderr.decode('utf-8', errors='ignore')}")
        raise RuntimeError("Portrait conversion failed")
    except Exception as e:
        logger.exception("Portrait conversion error")
        raise