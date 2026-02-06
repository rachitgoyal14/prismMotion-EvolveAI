"""
Stage 5 Doctor Ad: Render all Manim scenes (including closing with Pexels image), combine with audio.
"""
import subprocess
import json
from pathlib import Path
from app.paths import OUTPUTS_DIR
from app.utils.logging_config import StageLogger
from app.utils.llm import call_llm  # Assuming this is available
from app.utils.json_safe import extract_json
from app.paths import PROMPTS_DIR
import logging
logger = logging.getLogger(__name__)

MANIM_DIR = OUTPUTS_DIR / "manim"
VIDEOS_DIR = OUTPUTS_DIR / "videos"
AUDIO_DIR = OUTPUTS_DIR / "audio"

def auto_fix_runtime_error_with_llm(
    broken_code: str,
    runtime_error: str,
    scene_data: dict,
    attempt: int
) -> str:
    """
    Send runtime error + traceback to LLM for intelligent fix.
    (Moved from stage2 for reuse.)
    
    Args:
        broken_code: Manim code that failed at runtime
        runtime_error: Full Python traceback
        scene_data: Original scene requirements
        attempt: Fix attempt number
    
    Returns:
        Fixed code
    """
    logger.info(f"🔧 Asking LLM to fix runtime error (attempt {attempt})...", extra={'progress': True})
    
    # Load runtime fix prompt (assume it exists)
    fix_prompt_path = PROMPTS_DIR / "manim_runtime_fix.txt"
    
    if fix_prompt_path.exists():
        fix_template = fix_prompt_path.read_text(encoding="utf-8")
        fix_prompt = fix_template.replace("{runtime_error}", runtime_error) \
                                  .replace("{broken_code}", broken_code) \
                                  .replace("{scene_json}", json.dumps(scene_data, indent=2))
    else:
        # Fallback
        fix_prompt = f"""Fix this Manim code that has a RUNTIME ERROR.

RUNTIME ERROR:
{runtime_error}

BROKEN CODE:
{broken_code}

Return ONLY JSON: {{"manim_code": "<fixed code>"}}"""
    
    output = call_llm(fix_prompt, temperature=0.3)
    
    try:
        data = extract_json(output)
        fixed_code = data.get("manim_code", "").strip()
        
        if not fixed_code:
            raise ValueError("LLM returned empty manim_code")
        
        logger.info(f"✓ LLM returned fixed code ({len(fixed_code)} chars)", extra={'progress': True})
        return fixed_code
        
    except Exception as e:
        logger.error(f"Failed to parse LLM fix: {e}", extra={'progress': True})
        raise ValueError(f"LLM fix failed: {e}")


def render_manim_scene(scene_file: Path, output_dir: Path, scene_data: dict, quality: str = "high", max_retries: int = 2) -> Path:
    """Render single Manim scene with retry on error."""
    quality_flags = {"low": "-ql", "medium": "-qm", "high": "-qh", "production": "-qk"}
    quality_dirs = {"low": "480p15", "medium": "720p30", "high": "1080p60", "production": "2160p60"}
    
    flag = quality_flags.get(quality, "-qh")
    quality_dir = quality_dirs.get(quality, "1080p60")
    
    scene_id = scene_file.stem.replace("scene_", "")
    scene_class = f"Scene{scene_id}"
    
    for attempt in range(max_retries + 1):
        logger.info(f"Scene {scene_id}: Rendering Manim ({quality}) - attempt {attempt + 1}...", extra={'progress': True})
        
        cmd = [
            "manim", flag, str(scene_file), scene_class,
            "-o", f"{scene_file.stem}.mp4",
            "--media_dir", str(output_dir),
            "--disable_caching"
        ]
        
        try:
            process = subprocess.run(cmd, capture_output=True, text=True, check=True, timeout=300)
            rendered_video = output_dir / "videos" / scene_file.stem / quality_dir / f"{scene_file.stem}.mp4"
            
            if not rendered_video.exists():
                raise FileNotFoundError(f"Rendered video not found: {rendered_video}")
            
            logger.info(f"Scene {scene_id}: Rendered ✓", extra={'progress': True})
            return rendered_video
            
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
            runtime_error = e.stderr if hasattr(e, 'stderr') else str(e)
            logger.warning(f"Scene {scene_id}: Render failed - {runtime_error[:200]}...", extra={'progress': True})
            
            if attempt < max_retries:
                # Fix with LLM
                broken_code = scene_file.read_text(encoding="utf-8")
                fixed_code = auto_fix_runtime_error_with_llm(
                    broken_code=broken_code,
                    runtime_error=runtime_error,
                    scene_data=scene_data,
                    attempt=attempt + 1
                )
                # Overwrite the scene file with fixed code
                scene_file.write_text(fixed_code, encoding="utf-8")
                logger.info(f"Scene {scene_id}: Code fixed, retrying render...", extra={'progress': True})
            else:
                raise RuntimeError(f"Manim render failed after {max_retries} retries: {runtime_error[:200]}")


def combine_video_audio(video_path: Path, audio_path: Path, output_path: Path):
    """Combine video with audio."""
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
        subprocess.run(cmd, capture_output=True, text=True, check=True, timeout=60)
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"FFmpeg audio combine failed: {e.stderr[:200]}")


def concatenate_videos(video_paths: list[Path], output_path: Path):
    """Concatenate multiple videos."""
    if len(video_paths) == 1:
        import shutil
        shutil.copy(video_paths[0], output_path)
        return
    
    concat_file = output_path.parent / "concat_list.txt"
    
    with open(concat_file, "w") as f:
        for vp in video_paths:
            f.write(f"file '{vp.absolute()}'\n")
    
    cmd = ["ffmpeg", "-f", "concat", "-safe", "0", "-i", str(concat_file), "-c", "copy", "-y", str(output_path)]
    
    try:
        subprocess.run(cmd, capture_output=True, text=True, check=True, timeout=120)
        concat_file.unlink()
    except Exception as e:
        concat_file.unlink(missing_ok=True)
        raise RuntimeError(f"Concatenation failed: {str(e)[:200]}")


def render_doctor_video(video_id: str, scenes_data: dict, quality: str = "high") -> Path:
    """
    Complete doctor ad rendering: All scenes as Manim + Audio.
    
    Args:
        video_id: Video ID
        scenes_data: Full scenes data (with pexels_image_path injected if applicable)
        quality: Manim quality
    
    Returns:
        Path to final video
    """
    stage_logger = StageLogger("Doctor Ad Rendering")
    stage_logger.start()
    
    manim_scenes_dir = MANIM_DIR / video_id / "scenes"
    audio_scenes_dir = AUDIO_DIR / video_id
    output_dir = VIDEOS_DIR / video_id
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Load scene data
    scenes = sorted(scenes_data.get("scenes", []), key=lambda s: s["scene_id"])
    
    stage_logger.progress(f"Rendering {len(scenes)} Manim scenes...")
    
    final_videos = []
    failed_scenes = []
    completed = 0
    
    for scene in scenes:
        scene_id = scene["scene_id"]
        audio_file = audio_scenes_dir / f"scene_{scene_id}.wav"
        
        try:
            # Render Manim scene (all scenes are now Manim)
            scene_file = manim_scenes_dir / f"scene_{scene_id}.py"
            
            if not scene_file.exists():
                logger.warning(f"Scene {scene_id}: Manim file missing", extra={'progress': True})
                failed_scenes.append({"scene_id": scene_id, "reason": "File missing"})
                continue
            
            rendered_video = render_manim_scene(scene_file, MANIM_DIR / video_id, scene, quality)
            
            # Combine with audio
            if audio_file.exists():
                final_video = output_dir / f"scene_{scene_id}_final.mp4"
                combine_video_audio(rendered_video, audio_file, final_video)
                final_videos.append(final_video)
                logger.info(f"Scene {scene_id}: Manim + audio ✓", extra={'progress': True})
            else:
                logger.warning(f"Scene {scene_id}: No audio, using silent", extra={'progress': True})
                final_videos.append(rendered_video)
            
            completed += 1
            stage_logger.progress(f"Scene {scene_id}: Complete ({completed}/{len(scenes)})")
            
        except Exception as e:
            logger.error(f"Scene {scene_id}: Failed - {str(e)[:150]}", extra={'progress': True})
            failed_scenes.append({"scene_id": scene_id, "reason": str(e)[:200]})
            continue
    
    if not final_videos:
        stage_logger.error("All scenes failed")
        raise RuntimeError("No scenes rendered successfully")
    
    # Concatenate all
    logger.info(f"Concatenating {len(final_videos)} videos...", extra={'progress': True})
    final_output = output_dir / "final_doctor.mp4"
    concatenate_videos(final_videos, final_output)
    
    # Save report
    report = {
        "video_id": video_id,
        "quality": quality,
        "total_scenes": len(scenes),
        "successful_scenes": len(final_videos),
        "failed_scenes": failed_scenes
    }
    (output_dir / "render_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    
    if failed_scenes:
        stage_logger.complete(f"{len(final_videos)}/{len(scenes)} OK, {len(failed_scenes)} failed")
    else:
        stage_logger.complete(f"All {len(final_videos)} scenes rendered")
    
    return final_output