"""
Stage 5 MoA: Render Manim animations and combine with TTS audio.
OPTIMIZED with detailed logging and progress tracking.
"""
import subprocess
import json
from pathlib import Path
from app.paths import OUTPUTS_DIR
from app.utils.logging_config import StageLogger

import logging
logger = logging.getLogger(__name__)

MANIM_DIR = OUTPUTS_DIR / "manim"
VIDEOS_DIR = OUTPUTS_DIR / "videos"
AUDIO_DIR = OUTPUTS_DIR / "audio"


def render_manim_scene(scene_file: Path, output_dir: Path, quality: str = "high") -> Path:
    """Render a single Manim scene to video."""
    quality_flags = {"low": "-ql", "medium": "-qm", "high": "-qh", "production": "-qk"}
    quality_dirs = {"low": "480p15", "medium": "720p30", "high": "1080p60", "production": "2160p60"}
    
    flag = quality_flags.get(quality, "-qh")
    quality_dir = quality_dirs.get(quality, "1080p60")
    
    scene_id = scene_file.stem.replace("scene_", "")
    scene_class = f"Scene{scene_id}"
    
    cmd = [
        "manim", flag, str(scene_file), scene_class,
        "-o", f"{scene_file.stem}.mp4",
        "--media_dir", str(output_dir),
        "--disable_caching"
    ]
    
    logger.info(f"Scene {scene_id}: Rendering with Manim ({quality})...", extra={'progress': True})
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True, timeout=300)
        
        rendered_video = output_dir / "videos" / scene_file.stem / quality_dir / f"{scene_file.stem}.mp4"
        
        if not rendered_video.exists():
            raise FileNotFoundError(f"Rendered video not found: {rendered_video}")
        
        logger.info(f"Scene {scene_id}: Rendered ✓", extra={'progress': True})
        return rendered_video
        
    except subprocess.TimeoutExpired:
        raise RuntimeError(f"Scene {scene_id} render timed out (>5min)")
    except subprocess.CalledProcessError as e:
        error_msg = e.stderr[:200] if e.stderr else "Unknown error"
        raise RuntimeError(f"Manim failed: {error_msg}")


def combine_video_audio(video_path: Path, audio_path: Path, output_path: Path):
    """Combine video with audio using ffmpeg."""
    cmd = [
        "ffmpeg", "-i", str(video_path), "-i", str(audio_path),
        "-c:v", "copy", "-c:a", "aac", "-shortest", "-y", str(output_path)
    ]
    
    try:
        subprocess.run(cmd, capture_output=True, text=True, check=True, timeout=60)
    except subprocess.TimeoutExpired:
        raise RuntimeError("FFmpeg audio combine timed out")
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"FFmpeg failed: {e.stderr[:200]}")


def concatenate_videos(video_paths: list[Path], output_path: Path):
    """Concatenate multiple videos using ffmpeg."""
    if not video_paths:
        raise ValueError("No videos to concatenate")
    
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


def render_moa_video(video_id: str, quality: str = "high") -> Path:
    """Complete MoA video rendering pipeline with progress tracking."""
    stage_logger = StageLogger("Manim Rendering")
    stage_logger.start()
    
    manim_scenes_dir = MANIM_DIR / video_id / "scenes"
    audio_scenes_dir = AUDIO_DIR / video_id
    output_dir = VIDEOS_DIR / video_id
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Load scene data
    scenes_data_file = manim_scenes_dir / "scenes_data.json"
    if not scenes_data_file.exists():
        raise FileNotFoundError(f"Scene data not found: {scenes_data_file}")
    
    metadata = json.loads(scenes_data_file.read_text())
    scenes_data = metadata.get("scenes_data", metadata)
    scenes = sorted(scenes_data.get("scenes", []), key=lambda s: s["scene_id"])
    
    stage_logger.progress(f"Rendering {len(scenes)} scenes with quality={quality}...")
    
    combined_videos = []
    failed_renders = []
    completed = 0
    
    for scene in scenes:
        scene_id = scene["scene_id"]
        scene_file = manim_scenes_dir / f"scene_{scene_id}.py"
        audio_file = audio_scenes_dir / f"scene_{scene_id}.wav"
        
        if not scene_file.exists():
            logger.warning(f"Scene {scene_id}: File missing, skipping", extra={'progress': True})
            failed_renders.append({"scene_id": scene_id, "reason": "File not found"})
            continue
        
        try:
            # Render Manim
            rendered_video = render_manim_scene(scene_file, MANIM_DIR / video_id, quality)
            
            # Combine with audio if available
            if audio_file.exists():
                combined_video = output_dir / f"scene_{scene_id}_with_audio.mp4"
                try:
                    logger.info(f"Scene {scene_id}: Adding audio...", extra={'progress': True})
                    combine_video_audio(rendered_video, audio_file, combined_video)
                    combined_videos.append(combined_video)
                    logger.info(f"Scene {scene_id}: Audio added ✓", extra={'progress': True})
                except Exception as e:
                    logger.warning(f"Scene {scene_id}: Audio failed, using silent video", extra={'progress': True})
                    combined_videos.append(rendered_video)
            else:
                logger.warning(f"Scene {scene_id}: No audio found", extra={'progress': True})
                combined_videos.append(rendered_video)
            
            completed += 1
            stage_logger.progress(f"Scene {scene_id}: Complete ✓ ({completed}/{len(scenes)})")
            
        except Exception as e:
            logger.error(f"Scene {scene_id}: Render failed - {str(e)[:100]}", extra={'progress': True})
            failed_renders.append({"scene_id": scene_id, "reason": str(e)[:200]})
            continue
    
    if not combined_videos:
        stage_logger.error("All scenes failed to render")
        raise RuntimeError(f"No scenes rendered successfully. {len(scenes)} scenes failed.")
    
    # Concatenate
    logger.info(f"Concatenating {len(combined_videos)} videos...", extra={'progress': True})
    final_output = output_dir / "final_moa.mp4"
    
    try:
        concatenate_videos(combined_videos, final_output)
    except Exception as e:
        logger.error(f"Concatenation failed: {e}", extra={'progress': True})
        if combined_videos:
            import shutil
            shutil.copy(combined_videos[0], final_output)
            logger.warning("Using first scene as output", extra={'progress': True})
    
    # Save report
    report = {
        "video_id": video_id,
        "quality": quality,
        "total_scenes": len(scenes),
        "successful_scenes": len(combined_videos),
        "failed_scenes": failed_renders,
        "output_path": str(final_output)
    }
    (output_dir / "render_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    
    if failed_renders:
        stage_logger.complete(f"{len(combined_videos)}/{len(scenes)} scenes OK, {len(failed_renders)} failed")
    else:
        stage_logger.complete(f"All {len(combined_videos)} scenes rendered successfully")
    
    return final_output