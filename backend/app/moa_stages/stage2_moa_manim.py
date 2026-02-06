"""
Stage 2 MoA: Generate Manim animation code for each scene.
OPTIMIZED with parallel processing and detailed logging.
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

# Import validator
try:
    from app.utils.validate_manim import validate_manim_code
except ImportError:
    logger.warning("validate_manim not found, skipping validation")
    validate_manim_code = None


def generate_manim_scene(scene: dict, retry_count: int = 0, max_retries: int = 2) -> tuple[int, str]:
    """Generate Manim code for a single scene with validation."""
    prompt_path = PROMPTS_DIR / "manim_generator.txt"
    prompt_template = prompt_path.read_text(encoding="utf-8")
    
    scene_id = scene.get("scene_id", 1)
    duration = scene.get("duration_sec", 10)
    visual_elements = scene.get("visual_elements", [])
    
    retry_context = ""
    if retry_count > 0:
        retry_context = f"\n\nIMPORTANT: Retry #{retry_count}. Fix: imports, no FRAME_WIDTH, no SVGMobject path_string, class=Scene{scene_id}\n"
    
    prompt = prompt_template.replace("{scene_json}", json.dumps(scene, indent=2)) \
                           .replace("{duration}", str(duration)) \
                           .replace("{visual_elements}", ", ".join(visual_elements)) \
                           .replace("{scene_id}", str(scene_id)) + retry_context
    
    logger.info(f"Scene {scene_id}: Generating code (attempt {retry_count + 1})", extra={'progress': True})
    
    output = call_llm(prompt, temperature=0.3 if retry_count > 0 else 0)
    result = extract_json(output)
    
    manim_code = result.get("manim_code", "")
    if not manim_code:
        raise ValueError(f"No code returned for scene {scene_id}")
    
    # Validate
    if validate_manim_code:
        is_valid, error_msg = validate_manim_code(manim_code, scene_id)
        
        if not is_valid:
            logger.warning(f"Scene {scene_id}: Validation failed - {error_msg[:80]}", extra={'progress': True})
            
            if retry_count < max_retries:
                return generate_manim_scene(scene, retry_count + 1, max_retries)
            else:
                logger.warning(f"Scene {scene_id}: Auto-fixing...", extra={'progress': True})
                fixed_code = auto_fix_common_issues(manim_code, scene_id)
                
                if validate_manim_code:
                    is_fixed_valid, _ = validate_manim_code(fixed_code, scene_id)
                    if is_fixed_valid:
                        logger.info(f"Scene {scene_id}: Auto-fix OK ✓", extra={'progress': True})
                        return (scene_id, fixed_code)
                
                raise ValueError(f"Scene {scene_id} validation failed after retries: {error_msg}")
    
    logger.info(f"Scene {scene_id}: Validated ✓", extra={'progress': True})
    return (scene_id, manim_code)


def auto_fix_common_issues(code: str, scene_id: int) -> str:
    """Auto-fix common Manim code issues."""
    fixed = code
    fixes = []
    
    if "from manim import *" not in fixed:
        fixed = "from manim import *\n\n" + fixed
        fixes.append("imports")
    
    if "FRAME_WIDTH" in fixed or "FRAME_HEIGHT" in fixed:
        if "from manim import config" not in fixed:
            fixed = fixed.replace("from manim import *", "from manim import *\nfrom manim import config")
        fixed = fixed.replace("FRAME_WIDTH", "config.frame_width").replace("FRAME_HEIGHT", "config.frame_height")
        fixes.append("FRAME_*")
    
    if "config.background_color" in fixed:
        fixed = fixed.replace("config.background_color", "self.camera.background_color")
        fixes.append("bg_color")
    
    import re
    svg_matches = list(re.finditer(r"(\w+)\s*=\s*SVGMobject\s*\([^)]*path_string\s*=[^)]*\)", fixed))
    for match in svg_matches:
        var_name = match.group(1)
        fixed = fixed.replace(match.group(0), f"{var_name} = Circle(radius=0.3, color=GREEN, fill_opacity=0.8)")
        fixes.append(f"SVG({var_name})")
    
    class_match = re.search(r"class\s+\w+\s*\(Scene\)", fixed)
    if class_match and f"Scene{scene_id}" not in class_match.group(0):
        fixed = fixed.replace(class_match.group(0), f"class Scene{scene_id}(Scene)", 1)
        fixes.append("class_name")
    
    if fixes:
        logger.info(f"Scene {scene_id}: Fixed {', '.join(fixes)}", extra={'progress': True})
    
    return fixed


def run_stage2_moa(scenes_data: dict, script: list[dict], video_id: str, max_workers: int = 4) -> Path:
    """Generate Manim code for all scenes in PARALLEL."""
    stage_logger = StageLogger("Code Generation")
    stage_logger.start()
    
    scenes = scenes_data.get("scenes", [])
    manim_scenes_dir = MANIM_DIR / video_id / "scenes"
    manim_scenes_dir.mkdir(parents=True, exist_ok=True)
    
    script_map = {s["scene_id"]: s["script"] for s in script}
    for scene in scenes:
        scene["narration"] = script_map.get(scene["scene_id"], "")
    
    stage_logger.progress(f"Generating {len(scenes)} scenes in parallel (workers={max_workers})...")
    
    scene_files = []
    failed_scenes = []
    completed = 0
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_scene = {executor.submit(generate_manim_scene, scene): scene for scene in scenes}
        
        for future in as_completed(future_to_scene):
            scene = future_to_scene[future]
            scene_id = scene["scene_id"]
            
            try:
                scene_id, manim_code = future.result()
                scene_file = manim_scenes_dir / f"scene_{scene_id}.py"
                scene_file.write_text(manim_code, encoding="utf-8")
                scene_files.append(scene_file)
                completed += 1
                stage_logger.progress(f"Scene {scene_id}: Saved ✓ ({completed}/{len(scenes)})")
            except Exception as e:
                logger.error(f"Scene {scene_id}: Failed - {str(e)[:100]}", extra={'progress': True})
                failed_scenes.append({"scene_id": scene_id, "error": str(e)})
                completed += 1
    
    # Save metadata
    metadata = {
        "video_id": video_id,
        "total_scenes": len(scenes),
        "successful_scenes": len(scene_files),
        "failed_scenes": failed_scenes,
        "scenes_data": scenes_data
    }
    (manim_scenes_dir / "scenes_data.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    
    if not scene_files:
        stage_logger.error(f"All {len(scenes)} scenes failed")
        raise RuntimeError("Failed to generate any valid Manim scenes")
    
    if failed_scenes:
        stage_logger.complete(f"{len(scene_files)}/{len(scenes)} OK, {len(failed_scenes)} failed")
    else:
        stage_logger.complete(f"All {len(scene_files)} scenes OK")
    
    return manim_scenes_dir