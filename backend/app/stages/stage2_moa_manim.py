"""
Stage 2 MoA: Generate Manim animation code for each scene.
Now with validation and retry logic.
"""
import json
from pathlib import Path
from app.utils.llm import call_llm
from app.utils.json_safe import extract_json
from app.paths import PROMPTS_DIR, OUTPUTS_DIR

import logging
logger = logging.getLogger(__name__)

MANIM_DIR = OUTPUTS_DIR / "manim"

# Import validator (you'll need to add this to your utils)
try:
    from app.utils.validate_manim import validate_manim_code
except ImportError:
    logger.warning("validate_manim not found, skipping validation")
    validate_manim_code = None


def generate_manim_scene(scene: dict, retry_count: int = 0, max_retries: int = 2) -> str:
    """
    Generate Manim code for a single scene using LLM with validation and retry.
    
    Args:
        scene: Scene dict with scene_id, concept, visual_elements, duration_sec
        retry_count: Current retry attempt
        max_retries: Maximum number of retries
    
    Returns:
        Python code string for Manim Scene class
    
    Raises:
        ValueError: If code generation fails after max retries
    """
    prompt_path = PROMPTS_DIR / "manim_generator.txt"
    prompt_template = prompt_path.read_text(encoding="utf-8")
    
    scene_id = scene.get("scene_id", 1)
    duration = scene.get("duration_sec", 10)
    visual_elements = scene.get("visual_elements", [])
    
    # Add retry context to prompt if this is a retry
    retry_context = ""
    if retry_count > 0:
        retry_context = f"\n\nIMPORTANT: This is retry #{retry_count}. Previous attempt had errors. Please double-check:\n- All imports are present\n- No usage of FRAME_WIDTH/FRAME_HEIGHT\n- Class name is Scene{scene_id}\n- Code is syntactically valid\n"
    
    prompt = prompt_template.replace("{scene_json}", json.dumps(scene, indent=2)) \
                           .replace("{duration}", str(duration)) \
                           .replace("{visual_elements}", ", ".join(visual_elements)) \
                           .replace("{scene_id}", str(scene_id))
    
    prompt = prompt + retry_context
    
    logger.info(f"Generating Manim code for scene {scene_id} (attempt {retry_count + 1}/{max_retries + 1})...")
    
    output = call_llm(prompt, temperature=0.3 if retry_count > 0 else 0)
    result = extract_json(output)
    
    manim_code = result.get("manim_code", "")
    if not manim_code:
        raise ValueError(f"LLM did not return manim_code for scene {scene_id}")
    
    # Validate the generated code
    if validate_manim_code:
        is_valid, error_msg = validate_manim_code(manim_code, scene_id)
        
        if not is_valid:
            logger.warning(f"Generated code for scene {scene_id} failed validation: {error_msg}")
            
            # Retry if we haven't hit max retries
            if retry_count < max_retries:
                logger.info(f"Retrying scene {scene_id} generation...")
                return generate_manim_scene(scene, retry_count + 1, max_retries)
            else:
                # Last resort: try to auto-fix common issues
                logger.warning(f"Max retries reached for scene {scene_id}. Attempting auto-fix...")
                fixed_code = auto_fix_common_issues(manim_code, scene_id)
                
                # Validate fixed code
                if validate_manim_code:
                    is_fixed_valid, _ = validate_manim_code(fixed_code, scene_id)
                    if is_fixed_valid:
                        logger.info(f"Auto-fix successful for scene {scene_id}")
                        return fixed_code
                
                raise ValueError(
                    f"Failed to generate valid Manim code for scene {scene_id} after {max_retries} retries. "
                    f"Last error: {error_msg}"
                )
    
    logger.info(f"✓ Successfully generated and validated code for scene {scene_id}")
    return manim_code


def auto_fix_common_issues(code: str, scene_id: int) -> str:
    """
    Attempt to automatically fix common issues in generated Manim code.
    
    Args:
        code: Original Manim code
        scene_id: Scene ID
    
    Returns:
        Fixed code (may still be invalid)
    """
    fixed = code
    
    # Fix 1: Ensure imports at top
    if "from manim import *" not in fixed:
        fixed = "from manim import *\n\n" + fixed
    
    # Fix 2: Replace FRAME_WIDTH/FRAME_HEIGHT with config equivalents
    if "FRAME_WIDTH" in fixed or "FRAME_HEIGHT" in fixed:
        # Add config import if not present
        if "from manim import config" not in fixed and "from manim import *" in fixed:
            fixed = fixed.replace("from manim import *", "from manim import *\nfrom manim import config")
        
        # Replace usages
        fixed = fixed.replace("FRAME_WIDTH", "config.frame_width")
        fixed = fixed.replace("FRAME_HEIGHT", "config.frame_height")
        logger.info("Auto-fixed FRAME_WIDTH/FRAME_HEIGHT usage")
    
    # Fix 3: Replace config.background_color with self.camera.background_color
    if "config.background_color" in fixed:
        fixed = fixed.replace("config.background_color", "self.camera.background_color")
        logger.info("Auto-fixed background_color usage")
    
    # Fix 4: Remove SVGMobject with path_string (replace with simple comment)
    import re
    svg_pattern = r"(\w+)\s*=\s*SVGMobject\s*\([^)]*path_string\s*=[^)]*\)"
    matches = re.finditer(svg_pattern, fixed)
    
    for match in matches:
        var_name = match.group(1)
        full_match = match.group(0)
        
        # Replace with a simple placeholder shape
        replacement = f"{var_name} = Circle(radius=0.3, color=GREEN, fill_opacity=0.8)  # Auto-fixed: SVGMobject path_string not supported"
        fixed = fixed.replace(full_match, replacement)
        logger.info(f"Auto-fixed SVGMobject path_string usage for variable '{var_name}'")
    
    # Fix 5: Ensure correct class name
    class_pattern = r"class\s+\w+\s*\(Scene\)"
    match = re.search(class_pattern, fixed)
    if match:
        old_class_def = match.group()
        new_class_def = f"class Scene{scene_id}(Scene)"
        fixed = fixed.replace(old_class_def, new_class_def, 1)
        logger.info(f"Auto-fixed class name to Scene{scene_id}")
    
    return fixed


def run_stage2_moa(scenes_data: dict, script: list[dict], video_id: str) -> Path:
    """
    Generate Manim code for all scenes and save to individual Python files.
    
    Args:
        scenes_data: Output from stage1_moa_scenes
        script: Output from stage3_script (narration per scene)
        video_id: Unique video identifier
    
    Returns:
        Path to directory containing all Manim scene files
    
    Raises:
        RuntimeError: If scene generation fails for critical scenes
    """
    scenes = scenes_data.get("scenes", [])
    
    # Create output directory for this video's Manim scenes
    manim_scenes_dir = MANIM_DIR / video_id / "scenes"
    manim_scenes_dir.mkdir(parents=True, exist_ok=True)
    
    # Create script mapping
    script_map = {s["scene_id"]: s["script"] for s in script}
    
    # Generate Manim code for each scene
    scene_files = []
    failed_scenes = []
    
    for scene in scenes:
        scene_id = scene["scene_id"]
        
        # Add narration to scene data for context
        scene["narration"] = script_map.get(scene_id, "")
        
        try:
            logger.info(f"Generating Manim code for scene {scene_id}...")
            manim_code = generate_manim_scene(scene)
            
            # Save to individual Python file
            scene_file = manim_scenes_dir / f"scene_{scene_id}.py"
            scene_file.write_text(manim_code, encoding="utf-8")
            scene_files.append(scene_file)
            
            logger.info(f"✓ Saved Manim code to {scene_file}")
            
        except Exception as e:
            logger.error(f"✗ Failed to generate code for scene {scene_id}: {e}")
            failed_scenes.append({"scene_id": scene_id, "error": str(e)})
            # Continue with other scenes instead of crashing
            continue
    
    # Save metadata
    metadata = {
        "video_id": video_id,
        "total_scenes": len(scenes),
        "successful_scenes": len(scene_files),
        "failed_scenes": failed_scenes,
        "scenes_data": scenes_data
    }
    
    (manim_scenes_dir / "scenes_data.json").write_text(
        json.dumps(metadata, indent=2), encoding="utf-8"
    )
    
    # Check if we have enough successful scenes
    if not scene_files:
        raise RuntimeError(
            f"Failed to generate any valid Manim scenes. "
            f"All {len(scenes)} scenes failed. Check logs for details."
        )
    
    if len(failed_scenes) > 0:
        logger.warning(
            f"Generated {len(scene_files)}/{len(scenes)} scenes successfully. "
            f"Failed scenes: {[s['scene_id'] for s in failed_scenes]}"
        )
    else:
        logger.info(f"✓ Generated all {len(scene_files)} Manim scene files successfully")
    
    return manim_scenes_dir