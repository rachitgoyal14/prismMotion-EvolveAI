"""
Stage 5 Social Media: Render Manim scenes and combine with audio for short-form videos.
Modified for 9:16 portrait format (Instagram Reels, TikTok, YouTube Shorts)
"""
import subprocess
import time
import json
from pathlib import Path
from app.paths import OUTPUTS_DIR
from app.utils.logging_config import StageLogger
from app.utils.llm import call_llm
from app.utils.json_safe import extract_json
from app.paths import PROMPTS_DIR
import logging
logger = logging.getLogger(__name__)

MANIM_DIR = OUTPUTS_DIR / "manim"
VIDEOS_DIR = OUTPUTS_DIR / "videos"
AUDIO_DIR = OUTPUTS_DIR / "audio"


def auto_fix_runtime_error_with_llm_sm(
    broken_code: str,
    runtime_error: str,
    scene_data: dict,
    attempt: int
) -> str:
    """
    Send runtime error + traceback to LLM for intelligent fix.
    
    Args:
        broken_code: Manim code that failed at runtime
        runtime_error: Full Python traceback
        scene_data: Original scene requirements
        attempt: Fix attempt number
    
    Returns:
        Fixed code
    """
    logger.info(f"🔧 Asking LLM to fix runtime error (attempt {attempt})...", extra={'progress': True})
    
    # Load runtime fix prompt
    fix_prompt_path = PROMPTS_DIR / "manim_runtime_fix.txt"
    
    if fix_prompt_path.exists():
        fix_template = fix_prompt_path.read_text(encoding="utf-8")
        fix_prompt = fix_template.replace("{runtime_error}", runtime_error) \
                                  .replace("{broken_code}", broken_code) \
                                  .replace("{scene_json}", json.dumps(scene_data, indent=2))
    else:
        fix_prompt = f"""Fix this Manim code that has a RUNTIME ERROR.
Code:
{broken_code}

Error:
{runtime_error}

Scene:
{json.dumps(scene_data, indent=2)}

Return ONLY the corrected code in a code block."""
    
    full_prompt = f"""You are a Manim expert. Fix runtime errors in Manim animations.

{fix_prompt}"""
    response = call_llm(full_prompt)
    
    # Extract code from response
    if "```python" in response:
        code = response.split("```python")[1].split("```")[0].strip()
    elif "```" in response:
        code = response.split("```")[1].split("```")[0].strip()
    else:
        code = response
    
    return code


def render_manim_scene_sm(
    scene_data: dict,
    manim_code_path: Path,
    video_id: str,
    quality: str = "high"
) -> tuple[int, Path | None]:
    """
    Render a single Manim scene for social media in 9:16 portrait format.
    Optimized for Instagram Reels, TikTok, and YouTube Shorts.
    
    Returns:
        (scene_id, video_path or None on success)
    """
    scene_id = scene_data.get("scene_id", 0)
    output_dir = VIDEOS_DIR / video_id / "manim_renders"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Portrait 9:16 aspect ratio configurations
    # Using standard Manim quality flags which handle resolution internally
    quality_configs = {
        "low": {
            "flag": "-ql",  # 480p @ 15fps
            "width": 480,
        },
        "medium": {
            "flag": "-qm",  # 720p @ 30fps
            "width": 720,
        },
        "high": {
            "flag": "-qh",  # 1080p @ 60fps
            "width": 1080,
        }
    }
    
    config = quality_configs.get(quality, quality_configs["high"])
    flag = config["flag"]
    scene_class = f"Scene{scene_id}"
    
    try:
        # Render Manim with standard quality flags
        # Note: -ql/-qm/-qh already set resolution; avoid conflicting custom resolution in portrait mode
        cmd = [
            "manim", flag,
            str(manim_code_path),
            scene_class,
            "-o", f"scene_{scene_id}.mp4",
            "--media_dir", str(output_dir),
            "--disable_caching",
        ]
        
        logger.info(f"Scene {scene_id}: Running Manim command: {' '.join(cmd)}")
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300  # 5 minutes per scene
        )
        
        # Log Manim output for debugging
        if result.stdout:
            logger.debug(f"Scene {scene_id}: Manim stdout:\n{result.stdout[:500]}")
        if result.stderr:
            logger.debug(f"Scene {scene_id}: Manim stderr:\n{result.stderr[:500]}")
        
        if result.returncode != 0:
            raise RuntimeError(f"Manim render failed (exit code {result.returncode}):\n{result.stderr[:500]}")
        
        # Find rendered video - try multiple possible paths since Manim output structure varies
        possible_paths = [
            output_dir / "videos" / f"scene_{scene_id}" / "480p15" / f"scene_{scene_id}.mp4",  # low
            output_dir / "videos" / f"scene_{scene_id}" / "720p30" / f"scene_{scene_id}.mp4",   # medium
            output_dir / "videos" / f"scene_{scene_id}" / "1080p60" / f"scene_{scene_id}.mp4",  # high
            output_dir / "videos" / "480p15" / f"scene_{scene_id}.mp4",  # low quality
            output_dir / "videos" / "720p30" / f"scene_{scene_id}.mp4",   # medium quality
            output_dir / "videos" / "1080p60" / f"scene_{scene_id}.mp4",  # high quality
            output_dir / "videos" / f"scene_{scene_id}.mp4",              # direct path
        ]
        rendered_video = None
        for path in possible_paths:
            if path.exists():
                rendered_video = path
                logger.info(f"Scene {scene_id}: Found video at {path}")
                break
        
        if not rendered_video:
            # Last resort: search entire output_dir for any mp4 with this scene_id
            for mp4_file in output_dir.rglob(f"scene_{scene_id}.mp4"):
                rendered_video = mp4_file
                logger.info(f"Scene {scene_id}: Found video via recursive search at {mp4_file}")
                break
        
        if not rendered_video:
            logger.error(f"Scene {scene_id}: Rendered video not found at any expected path")
            logger.error(f"Scene {scene_id}: Output dir contents: {list(output_dir.iterdir()) if output_dir.exists() else 'N/A'}")
            return (scene_id, None)

        # Re-encode to portrait 9:16 using ffmpeg to ensure correct orientation/aspect
        width = config.get("width", 480)
        height = int(round(width * 16 / 9))
        portrait_video = output_dir / f"scene_{scene_id}_portrait.mp4"

        try:
            # ────────────────────────────────────────────────
            # Tunable parameters – adjust based on your Manim content
            fg_scale_factor = 0.76       # 0.74 – 0.80; most Manim scenes need ~0.75–0.77
            bg_blur_radius  = 60         # higher = more background blur
            bg_blur_sigma   = 2.0
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

            ff_cmd = [
                "ffmpeg", "-y",
                "-i", str(rendered_video),
                "-filter_complex", filter_complex,
                "-c:v", "libx264", "-crf", "23", "-preset", "veryfast",
                "-c:a", "aac", "-b:a", "128k",
                "-movflags", "+faststart",           # better streaming
                str(portrait_video)
            ]

            logger.info(
                f"Scene {scene_id}: Re-encoding to portrait {width}×{height} "
                f"(fg_scale={fg_scale_factor}, blur={bg_blur_radius}:{bg_blur_sigma})"
            )
            # logger.debug(f"Filter complex: {filter_complex}")   # uncomment for debugging

            r = subprocess.run(
                ff_cmd,
                capture_output=True,
                text=True,
                timeout=180,          # 3 minutes – should be plenty per scene
                check=True
            )

            final_render_video = portrait_video
            logger.info(f"Scene {scene_id}: Portrait video created → {portrait_video}")

        except subprocess.CalledProcessError as err:
            logger.error(
                f"ffmpeg portrait encode failed (scene {scene_id}):\n"
                f"{err.stderr[:800]}"   # show more of the error
            )
            final_render_video = rendered_video   # fallback to landscape version
        except subprocess.TimeoutExpired:
            logger.error(f"ffmpeg timeout (scene {scene_id})")
            final_render_video = rendered_video
        except Exception as e:
            logger.error(f"Unexpected error in portrait conversion (scene {scene_id}): {e}")
            final_render_video = rendered_video        
        logger.info(f"Scene {scene_id}: Render complete → {rendered_video}")
        return (scene_id, final_render_video)

        
    except subprocess.TimeoutExpired:
        logger.error(f"Scene {scene_id}: Render timeout (5min limit)")
        return (scene_id, None)
    except Exception as e:
        logger.error(f"Scene {scene_id}: Render failed - {e}")
        return (scene_id, None)


def combine_video_audio_sm(video_path: Path, audio_path: Path, output_path: Path) -> None:
    """Combine single video with audio using FFmpeg."""
    if not audio_path.exists():
        logger.warning(f"Audio file not found: {audio_path}, copying video only")
        import shutil
        shutil.copy(str(video_path), str(output_path))
        return
    
    cmd = [
        "ffmpeg",
        "-i", str(video_path),
        "-i", str(audio_path),
        "-c:v", "copy",
        "-c:a", "aac",
        "-shortest",
        "-y",
        str(output_path)
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        if result.returncode != 0:
            raise RuntimeError(result.stderr)
        logger.info(f"Audio combined → {output_path}")
    except subprocess.TimeoutExpired:
        raise RuntimeError("FFmpeg audio combine timeout")
    except Exception as e:
        raise RuntimeError(f"FFmpeg audio combine failed: {str(e)[:200]}")


def concatenate_videos_sm(video_paths: list[Path], output_path: Path) -> None:
    """
    Concatenate video clips with audio overlays using ffmpeg.
    Maintains 9:16 portrait aspect ratio for social media.
    """
    if not video_paths:
        raise ValueError("No videos to concatenate")
    
    logger.info(f"Concatenating {len(video_paths)} portrait videos (9:16)...")
    
    # Create concat file
    concat_file = output_path.parent / "concat.txt"
    with open(concat_file, "w") as f:
        for path in video_paths:
            if path.exists():
                f.write(f"file '{path.resolve()}'\n")
    
    # FFmpeg concatenate - maintains aspect ratio
    cmd = [
        "ffmpeg", "-f", "concat", "-safe", "0",
        "-i", str(concat_file),
        "-c", "copy",  # No re-encoding, preserves original format
        "-y",  # Overwrite
        str(output_path)
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode != 0:
        raise RuntimeError(f"FFmpeg concat failed:\n{result.stderr}")
    
    logger.info(f"Portrait videos concatenated → {output_path}")
    concat_file.unlink()  # Cleanup


def render_sm_video(
    video_id: str,
    scenes_data: dict,
    quality: str = "high"
) -> Path:
    """
    Main render function for social media videos in 9:16 portrait format.
    Renders all Manim scenes + combines with audio for each scene.
    
    Args:
        video_id: Unique identifier for the video project
        scenes_data: Dictionary containing scene information
        quality: Render quality - "low" (480x854), "medium" (720x1280), or "high" (1080x1920)
    
    Returns:
        Path to final portrait video (9:16 aspect ratio)
    """
    manim_code_dir = VIDEOS_DIR / video_id / "manim"
    audio_dir = AUDIO_DIR / video_id
    output_dir = VIDEOS_DIR / video_id
    final_output = output_dir / "final.mp4"
    
    logger.info(f"Starting SM portrait render pipeline (quality={quality}, aspect_ratio=9:16)")
    
    stage_logger = StageLogger("Social Media Render (Portrait)")
    stage_logger.start()
    render_start = time.time()
    
    scenes = scenes_data.get("scenes", [])
    final_videos = []
    
    # Render each Manim scene and combine with audio
    for i, scene in enumerate(scenes):
        scene_id = scene.get("scene_id", i)
        code_path = manim_code_dir / f"scene_{scene_id}.py"
        
        if not code_path.exists():
            logger.warning(f"Scene {scene_id}: Code file not found, skipping")
            continue
        
        # Render Manim in portrait mode
        scene_id_ret, video_path = render_manim_scene_sm(scene, code_path, video_id, quality)
        
        if not video_path:
            logger.error(f"Scene {scene_id}: Render failed")
            continue
        
        # Find and combine audio
        audio_file = audio_dir / f"scene_{scene_id}.wav"
        final_scene_video = output_dir / f"scene_{scene_id}_final.mp4"

        if audio_file.exists():
            try:
                combine_video_audio_sm(video_path, audio_file, final_scene_video)
                final_videos.append(final_scene_video)
                logger.info(f"Scene {scene_id}: Audio combined")
            except Exception as e:
                logger.warning(f"Scene {scene_id}: Audio combine failed - {e}, using silent")
                final_videos.append(video_path)
        else:
            logger.warning(f"Scene {scene_id}: No audio found, using silent")
            final_videos.append(video_path)

    
    if not final_videos:
        raise RuntimeError("No scenes rendered successfully")
    
    # Concatenate all portrait videos with audio
    try:
        concatenate_videos_sm(final_videos, final_output)
        logger.info(f"Portrait videos concatenated → {final_output}")
    except Exception as e:
        logger.error(f"Concatenation failed: {e}")
        # Fallback: just use first video
        if final_videos:
            import shutil
            shutil.copy(str(final_videos[0]), str(final_output))
            logger.info("Fallback: Using first video")
    
    render_elapsed = time.time() - render_start
    stage_logger.complete(f"Final portrait video (9:16): {final_output}")
    logger.info(f"Render complete: {final_output} (render_seconds={round(render_elapsed,1)})")
    
    return final_output