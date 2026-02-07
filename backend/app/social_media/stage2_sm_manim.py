"""
Stage 2 Social Media: Generate Manim code for short-form scenes.
Optimized for fast, engaging animations suitable for Instagram Reels.
"""
import json
import re
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


def shrink_text_and_scale_for_portrait(code: str) -> str:
    """
    Post-process generated Manim code to make text smaller and better suited
    for portrait (9:16) social media format.
    """
    try:
        # 1. Cap font_size values (body ≤ 36, titles ≤ 54)
        def cap_font_size(match):
            try:
                size = float(match.group(1))
                is_title = "title" in match.group(0).lower() or "heading" in match.group(0).lower()
                new_size = min(size, 54 if is_title else 36)
                return f'font_size={new_size}'
            except:
                return match.group(0)  # keep original if conversion fails

        code = re.sub(r'font_size\s*=\s*(\d+\.?\d*)', cap_font_size, code, flags=re.IGNORECASE)

        # 2. Force reasonable default size on Tex / MathTex if missing
        code = re.sub(
            r'(Tex|MathTex)\(([^)]*?)\)',
            lambda m: f'{m.group(1)}({m.group(2)}, font_size=32)' 
                      if 'font_size' not in m.group(2) else m.group(0),
            code,
            flags=re.DOTALL
        )

        # 3. Reduce aggressive .scale() calls
        code = re.sub(
            r'\.scale\((\d+\.?\d*)\)',
            lambda m: f'.scale({min(float(m.group(1)), 0.85):.2f})',
            code
        )

        # 4. Scale down scene.add() calls that don't already have .scale()
        code = re.sub(
            r'(scene\.add\()([^)]*?)(?<!\.scale\([^)]+\))([^)]*?\))',
            lambda m: f'{m.group(1)}{m.group(2)}.scale(0.82){m.group(3)}',
            code,
            flags=re.DOTALL
        )

        # 5. Increase buff on vertical edges
        code = re.sub(
            r'\.to_edge\s*\(\s*(UP|DOWN)\s*\)',
            r'.to_edge(\1, buff=1.4)',
            code,
            flags=re.IGNORECASE
        )
        code = re.sub(
            r'\.move_to\s*\(\s*(UP|DOWN)\s*\)',
            r'.move_to(\1 * 0.75)',
            code,
            flags=re.IGNORECASE
        )

        return code.strip()

    except Exception as e:
        logger.error(f"Error in shrink_text_and_scale_for_portrait: {e}", exc_info=True)
        return code  # return original if processing fails


def generate_manim_scene_sm(scene: dict, retry_count: int = 0, max_retries: int = 2) -> tuple[int, str]:
    scene_id = scene.get("scene_id", 0)
    logger.info(f"Generating Manim code for scene {scene_id}")

    # Load prompt template
    prompt_path = PROMPTS_DIR / "manim_generator.txt"
    if not prompt_path.exists():
        logger.warning("Manim generator prompt not found → using minimal fallback")
        template = (
            "Create a short 5-12 second Manim animation for social media (Instagram Reels / TikTok).\n"
            "Scene description: {scene_json}\n"
            "Scene ID: {scene_id}\n"
            "Duration: ~10 seconds\n"
            "Use simple, engaging animations with text, shapes, arrows.\n"
            "Return only the complete Python code."
        )
    else:
        template = prompt_path.read_text(encoding="utf-8")

    prompt = template.replace("{scene_json}", json.dumps(scene, indent=2))
    prompt = prompt.replace("{scene_id}", str(scene_id))
    prompt = prompt.replace("{duration}", "10")
    prompt = prompt.replace("{visual_elements}", "Text, shapes, simple animations")

    full_prompt = f"""You are an expert Manim animation programmer. Generate short, efficient Manim code for vertical social media videos (5-15 seconds max).

{prompt}

Return ONLY the complete, valid Python code (no explanations)."""

    response = call_llm(full_prompt)

    # Extract code
    try:
        code_data = extract_json(response)
        code = (
            code_data.get("manim_code")
            or code_data.get("code")
            or response
        )
    except Exception:
        code = response

    code = str(code).strip()

    # Shrink text & scale for portrait
    original_len = len(code)
    code = shrink_text_and_scale_for_portrait(code)
    logger.info(
        f"Scene {scene_id}: Post-processing applied "
        f"({original_len} → {len(code)} chars)"
    )

    # Validate the adjusted code
    if validate_manim_code is not None:
        try:
            is_valid, error_msg = validate_manim_code(code, scene_id)
            if is_valid:
                logger.info(f"Scene {scene_id}: Syntax valid ✓")
            else:
                logger.warning(f"Scene {scene_id}: Syntax error after shrink - {error_msg}")
                if retry_count < max_retries:
                    logger.info(f"Retrying scene {scene_id} (attempt {retry_count + 1})...")
                    return generate_manim_scene_sm(scene, retry_count + 1, max_retries)
        except Exception as e:
            logger.warning(f"Scene {scene_id}: Validation error - {e}")
            if retry_count < max_retries:
                logger.info(f"Retrying scene {scene_id} (attempt {retry_count + 1})...")
                return generate_manim_scene_sm(scene, retry_count + 1, max_retries)

    return scene_id, code


def run_stage2_sm(
    scenes_data: dict,
    script: dict,
    video_id: str,
    max_workers: int = 3
) -> None:
    scenes = scenes_data.get("scenes", [])
    if not scenes:
        logger.warning("No scenes found in scenes_data")
        return

    manim_dir = OUTPUTS_DIR / "videos" / video_id / "manim"
    manim_dir.mkdir(parents=True, exist_ok=True)

    logger.info(f"Generating Manim code for {len(scenes)} scenes (max_workers={max_workers})")

    stage_logger = StageLogger("Social Media Manim Generation")
    stage_logger.start()

    results = {}

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(generate_manim_scene_sm, scene): scene.get("scene_id", i)
            for i, scene in enumerate(scenes)
        }

        for future in as_completed(futures):
            try:
                scene_id, code = future.result()
                results[scene_id] = code
                logger.debug(f"Scene {scene_id}: Generated {len(code)} chars")
            except Exception as e:
                logger.error(f"Failed to generate scene code: {e}")

    for scene_id, code in results.items():
        code_path = manim_dir / f"scene_{scene_id}.py"
        code_path.write_text(code, encoding="utf-8")
        logger.info(f"Saved: {code_path}")

    stage_logger.complete(f"{len(results)} Manim scenes generated")
    logger.info("Stage 2 complete: Manim code generation finished")