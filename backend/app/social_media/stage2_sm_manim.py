"""
Stage 2 Social Media: Generate Manim code for short-form scenes.
Optimized for fast, engaging animations suitable for Instagram Reels.
"""
import json
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from app.utils.llm import call_llm
from app.utils.json_safe import extract_json
from app.paths import PROMPTS_DIR, OUTPUTS_DIR
from app.utils.logging_config import StageLogger

import logging
logger = logging.getLogger(__name__)

MANIM_DIR = OUTPUTS_DIR / "manim"

# Import validators (only syntax, no runtime)
try:
    from app.utils.validate_manim import validate_manim_code
except ImportError:
    logger.warning("Validators not found, skipping validation")
    validate_manim_code = None


def generate_manim_scene_sm(scene: dict, retry_count: int = 0, max_retries: int = 2) -> tuple[int, str]:
    """
    Generate Manim code optimized for social media (short, fast animations).
    
    Flow:
    1. Generate code
    2. Validate syntax
    3. Retry on failure (up to max_retries)
    
    Returns:
        (scene_id, code)
    """
    scene_id = scene.get("scene_id", 0)
    
    logger.info(f"Generating Manim code for scene {scene_id}")
    
    # Load prompt
    prompt_path = PROMPTS_DIR / "manim_generator.txt"
    if not prompt_path.exists():
        logger.warning("Manim generator prompt not found, using fallback")
        prompt = f"Generate a 5-15 second Manim animation for: {json.dumps(scene)}"
    else:
        template = prompt_path.read_text(encoding="utf-8")
        prompt = template.replace("{scene_json}", json.dumps(scene, indent=2))
        prompt = prompt.replace("{scene_id}", str(scene_id))
        # Fill in other placeholders with sensible defaults
        prompt = prompt.replace("{duration}", "10")
        prompt = prompt.replace("{visual_elements}", "Text, shapes, simple animations")
    
    # Call LLM for Manim code
    full_prompt = f"""You are an expert Manim animation programmer. Generate short, efficient Manim code for social media videos (5-15 seconds max).

{prompt}"""
    response = call_llm(full_prompt)
    
    # Extract code from JSON response
    try:
        code_data = extract_json(response)
        if isinstance(code_data, dict):
            code = code_data.get("manim_code", code_data.get("code", response))
        else:
            code = response
    except Exception as e:
        logger.warning(f"JSON extraction failed: {e}, using raw response")
        code = response
    
    code = str(code).strip()
    
    # Validate syntax
    if validate_manim_code:
        try:
            is_valid, error_msg = validate_manim_code(code, scene_id)
            if is_valid:
                logger.info(f"Scene {scene_id}: Syntax valid ✓")
            else:
                logger.warning(f"Scene {scene_id}: Syntax error - {error_msg}")
                if retry_count < max_retries:
                    logger.info(f"Retrying scene {scene_id}...")
                    return generate_manim_scene_sm(scene, retry_count + 1, max_retries)
        except Exception as e:
            logger.warning(f"Scene {scene_id}: Validation error - {e}")
            if retry_count < max_retries:
                logger.info(f"Retrying scene {scene_id}...")
                return generate_manim_scene_sm(scene, retry_count + 1, max_retries)
    
    return (scene_id, code)


def run_stage2_sm(
    scenes_data: dict,
    script: dict,
    video_id: str,
    max_workers: int = 3
) -> None:
    """
    Generate Manim code for all scenes in parallel.
    
    Args:
        scenes_data: Scene breakdown from Stage 1
        script: Script with scene-level narration
        video_id: Video ID for output directory
        max_workers: Parallel workers
    """
    scenes = scenes_data.get("scenes", [])
    
    # Prepare output directory
    manim_dir = OUTPUTS_DIR / "videos" / video_id / "manim"
    manim_dir.mkdir(parents=True, exist_ok=True)
    
    logger.info(f"Generating Manim code for {len(scenes)} scenes (max_workers={max_workers})")
    
    stage_logger = StageLogger("Social Media Manim Generation")
    stage_logger.start()
    
    results = {}
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all tasks
        futures = {
            executor.submit(generate_manim_scene_sm, scene): scene.get("scene_id", i)
            for i, scene in enumerate(scenes)
        }
        
        # Collect results
        for future in as_completed(futures):
            try:
                scene_id, code = future.result()
                results[scene_id] = code
                logger.debug(f"Scene {scene_id}: Generated {len(code)} chars of Manim code")
            except Exception as e:
                logger.error(f"Failed to generate scene code: {e}")
    
    # Save all codes
    for scene_id, code in results.items():
        code_path = manim_dir / f"scene_{scene_id}.py"
        code_path.write_text(code, encoding="utf-8")
        logger.info(f"Saved: {code_path}")
    
    stage_logger.complete(f"{len(results)} Manim scenes generated")
    logger.info("Stage 2 complete: Manim code generation finished")
