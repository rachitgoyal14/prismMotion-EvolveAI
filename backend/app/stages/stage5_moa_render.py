"""
Stage 5 MoA: Render Manim animations and combine with TTS audio.
Now with graceful failure handling - continues even if some scenes fail.
"""
import subprocess
import json
from pathlib import Path
from app.paths import OUTPUTS_DIR

import logging
logger = logging.getLogger(__name__)

MANIM_DIR = OUTPUTS_DIR / "manim"
VIDEOS_DIR = OUTPUTS_DIR / "videos"
AUDIO_DIR = OUTPUTS_DIR / "audio"


def render_manim_scene(scene_file: Path, output_dir: Path, quality: str = "high") -> Path:
    """
    Render a single Manim scene to video.
    
    Args:
        scene_file: Path to Python file containing Manim Scene class
        output_dir: Directory to save rendered video
        quality: "low" | "medium" | "high" | "production"
    
    Returns:
        Path to rendered video file
    
    Raises:
        RuntimeError: If rendering fails
    """
    quality_flags = {
        "low": "-ql",
        "medium": "-qm", 
        "high": "-qh",
        "production": "-qk"  # 4K
    }
    
    quality_dirs = {
        "low": "480p15",
        "medium": "720p30",
        "high": "1080p60",
        "production": "2160p60"
    }
    
    flag = quality_flags.get(quality, "-qh")
    quality_dir = quality_dirs.get(quality, "1080p60")
    
    # Extract scene ID from filename (scene_1.py -> 1)
    scene_id = scene_file.stem.replace("scene_", "")
    scene_class = f"Scene{scene_id}"
    
    cmd = [
        "manim",
        flag,
        str(scene_file),
        scene_class,
        "-o", f"{scene_file.stem}.mp4",
        "--media_dir", str(output_dir),
        "--disable_caching"
    ]
    
    logger.info(f"Rendering {scene_file.name} with command: {' '.join(cmd)}")
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True,
            timeout=300  # 5 minute timeout per scene
        )
        logger.info(f"Manim render output: {result.stdout}")
        
        # Manim outputs to media_dir/videos/{scene_file.stem}/{quality}/scene.mp4
        rendered_video = output_dir / "videos" / scene_file.stem / quality_dir / f"{scene_file.stem}.mp4"
        
        if not rendered_video.exists():
            raise FileNotFoundError(f"Expected rendered video not found: {rendered_video}")
        
        logger.info(f"✓ Successfully rendered {scene_file.name}")
        return rendered_video
        
    except subprocess.TimeoutExpired:
        logger.error(f"Manim rendering timed out for {scene_file.name}")
        raise RuntimeError(f"Manim render timed out for {scene_file.name}")
    except subprocess.CalledProcessError as e:
        logger.error(f"Manim rendering failed for {scene_file.name}: {e.stderr}")
        raise RuntimeError(f"Manim render failed for {scene_file.name}: {e.stderr}")


def combine_video_audio(video_path: Path, audio_path: Path, output_path: Path):
    """
    Combine video with audio using ffmpeg.
    
    Args:
        video_path: Path to video file (no audio)
        audio_path: Path to audio file
        output_path: Path for final combined video
    
    Raises:
        RuntimeError: If ffmpeg fails
    """
    cmd = [
        "ffmpeg",
        "-i", str(video_path),
        "-i", str(audio_path),
        "-c:v", "copy",  # Copy video stream (no re-encoding)
        "-c:a", "aac",   # Encode audio as AAC
        "-shortest",     # End when shortest stream ends
        "-y",            # Overwrite output
        str(output_path)
    ]
    
    logger.info(f"Combining video and audio: {output_path.name}")
    
    try:
        subprocess.run(cmd, capture_output=True, text=True, check=True, timeout=60)
        logger.info(f"✓ Successfully combined video and audio: {output_path}")
    except subprocess.TimeoutExpired:
        raise RuntimeError(f"FFmpeg timed out combining {video_path.name}")
    except subprocess.CalledProcessError as e:
        logger.error(f"FFmpeg failed: {e.stderr}")
        raise RuntimeError(f"Failed to combine video and audio: {e.stderr}")


def concatenate_videos(video_paths: list[Path], output_path: Path):
    """
    Concatenate multiple videos into one using ffmpeg.
    
    Args:
        video_paths: List of video file paths (in order)
        output_path: Path for final concatenated video
    
    Raises:
        RuntimeError: If concatenation fails
    """
    if not video_paths:
        raise ValueError("No videos to concatenate")
    
    # If only one video, just copy it
    if len(video_paths) == 1:
        import shutil
        shutil.copy(video_paths[0], output_path)
        logger.info(f"Only one video, copied to {output_path}")
        return
    
    # Create temporary file list for ffmpeg concat
    concat_file = output_path.parent / "concat_list.txt"
    
    with open(concat_file, "w") as f:
        for vp in video_paths:
            f.write(f"file '{vp.absolute()}'\n")
    
    cmd = [
        "ffmpeg",
        "-f", "concat",
        "-safe", "0",
        "-i", str(concat_file),
        "-c", "copy",  # Copy streams without re-encoding
        "-y",
        str(output_path)
    ]
    
    logger.info(f"Concatenating {len(video_paths)} videos...")
    
    try:
        subprocess.run(cmd, capture_output=True, text=True, check=True, timeout=120)
        logger.info(f"✓ Successfully concatenated videos: {output_path}")
        concat_file.unlink()  # Clean up temp file
    except subprocess.TimeoutExpired:
        concat_file.unlink(missing_ok=True)
        raise RuntimeError("FFmpeg concatenation timed out")
    except subprocess.CalledProcessError as e:
        concat_file.unlink(missing_ok=True)
        logger.error(f"FFmpeg concatenation failed: {e.stderr}")
        raise RuntimeError(f"Failed to concatenate videos: {e.stderr}")


def render_moa_video(video_id: str, quality: str = "high") -> Path:
    """
    Complete MoA video rendering pipeline with graceful failure handling:
    1. Render each Manim scene (skip failures)
    2. Combine each scene with its TTS audio (skip if audio missing)
    3. Concatenate all successful scenes into final video
    
    Args:
        video_id: Unique video identifier
        quality: Manim render quality
    
    Returns:
        Path to final rendered video
    
    Raises:
        RuntimeError: If no scenes could be rendered successfully
    """
    manim_scenes_dir = MANIM_DIR / video_id / "scenes"
    audio_scenes_dir = AUDIO_DIR / video_id
    output_dir = VIDEOS_DIR / video_id
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Load scene data to get order
    scenes_data_file = manim_scenes_dir / "scenes_data.json"
    if not scenes_data_file.exists():
        raise FileNotFoundError(f"Scene data not found: {scenes_data_file}")
    
    metadata = json.loads(scenes_data_file.read_text())
    scenes_data = metadata.get("scenes_data", metadata)  # Handle both formats
    scenes = sorted(scenes_data.get("scenes", []), key=lambda s: s["scene_id"])
    
    combined_videos = []
    failed_renders = []
    
    # Process each scene
    for scene in scenes:
        scene_id = scene["scene_id"]
        scene_file = manim_scenes_dir / f"scene_{scene_id}.py"
        audio_file = audio_scenes_dir / f"scene_{scene_id}.wav"
        
        if not scene_file.exists():
            logger.warning(f"Scene file not found: {scene_file}, skipping scene {scene_id}")
            failed_renders.append({"scene_id": scene_id, "reason": "Scene file not found"})
            continue
        
        try:
            # 1. Render Manim animation
            logger.info(f"Rendering scene {scene_id}...")
            rendered_video = render_manim_scene(scene_file, MANIM_DIR / video_id, quality)
            
            # 2. Combine with audio if available
            if audio_file.exists():
                combined_video = output_dir / f"scene_{scene_id}_with_audio.mp4"
                try:
                    combine_video_audio(rendered_video, audio_file, combined_video)
                    combined_videos.append(combined_video)
                except Exception as e:
                    logger.error(f"Failed to combine scene {scene_id} with audio: {e}")
                    logger.warning(f"Using video without audio for scene {scene_id}")
                    # Use video without audio as fallback
                    combined_videos.append(rendered_video)
            else:
                logger.warning(f"Audio not found for scene {scene_id}: {audio_file}")
                # Use video without audio
                combined_videos.append(rendered_video)
            
            logger.info(f"✓ Scene {scene_id} processed successfully")
            
        except Exception as e:
            logger.error(f"✗ Failed to render scene {scene_id}: {e}")
            failed_renders.append({"scene_id": scene_id, "reason": str(e)})
            # Continue with next scene
            continue
    
    # Check if we have any successful renders
    if not combined_videos:
        raise RuntimeError(
            f"No scenes were successfully rendered. "
            f"All {len(scenes)} scenes failed. "
            f"Failed scenes: {failed_renders}"
        )
    
    # Log summary
    success_count = len(combined_videos)
    total_count = len(scenes)
    logger.info(f"Rendered {success_count}/{total_count} scenes successfully")
    
    if failed_renders:
        logger.warning(f"Failed scenes: {[f['scene_id'] for f in failed_renders]}")
    
    # 3. Concatenate all successful scenes
    final_output = output_dir / "final_moa.mp4"
    try:
        concatenate_videos(combined_videos, final_output)
    except Exception as e:
        logger.error(f"Failed to concatenate videos: {e}")
        # If concatenation fails but we have videos, save the first one as output
        if combined_videos:
            logger.warning("Concatenation failed, using first successful scene as output")
            import shutil
            shutil.copy(combined_videos[0], final_output)
    
    # Save render report
    report = {
        "video_id": video_id,
        "quality": quality,
        "total_scenes": total_count,
        "successful_scenes": success_count,
        "failed_scenes": failed_renders,
        "output_path": str(final_output)
    }
    
    report_file = output_dir / "render_report.json"
    report_file.write_text(json.dumps(report, indent=2), encoding="utf-8")
    
    logger.info(f"✅ MoA video rendering complete: {final_output}")
    logger.info(f"📊 Render report saved: {report_file}")
    
    return final_output