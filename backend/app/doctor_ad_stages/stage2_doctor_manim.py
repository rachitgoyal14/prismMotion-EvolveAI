"""
Stage 2 Doctor Ad: Generate Manim code for all scenes (including product and logo closing scenes).
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


def generate_logo_scene_code(scene: dict) -> str:
    """
    Generate Manim code for logo scene with optional tagline.
    """
    scene_id = scene.get("scene_id", 1)
    logo_path = scene.get("logo_path", "")
    tagline = scene.get("tagline", "")
    
    code = f'''from manim import *
from manim import config
from pathlib import Path

class Scene{scene_id}(Scene):
    def construct(self):
        # Set white background
        self.camera.background_color = WHITE
        
        # Define custom colors
        medical_blue = "#2E86AB"
        
'''
    
    if logo_path:
        code += f'''        # Load company logo
        try:
            logo = ImageMobject("{logo_path}")
            logo.height = config.frame_height * 0.4
            logo.move_to(ORIGIN)
            
'''
        
        if tagline:
            code += f'''            # Add tagline
            tagline = Text("{tagline}", font="Sans", font_size=32, color=BLACK)
            tagline.next_to(logo, DOWN, buff=0.8)
            
            self.play(FadeIn(logo, scale=0.9), run_time=1)
            self.wait(0.5)
            self.play(Write(tagline), run_time=0.8)
            self.wait(2)
            self.play(FadeOut(logo), FadeOut(tagline), run_time=1)
'''
        else:
            code += f'''            self.play(FadeIn(logo, scale=0.9), run_time=1)
            self.wait(3)
            self.play(FadeOut(logo), run_time=1)
'''
        
        code += f'''        except Exception as e:
            # Fallback: Show text if logo fails
            text = Text("Thank You", font="Sans", font_size=56, color=BLACK)
            text.move_to(ORIGIN)
            self.play(Write(text), run_time=1)
            self.wait(3)
            self.play(FadeOut(text), run_time=1)
'''
    else:
        # No logo provided - show thank you text
        code += f'''        text = Text("Thank You", font="Sans", font_size=56, color=BLACK)
        text.move_to(ORIGIN)
'''
        
        if tagline:
            code += f'''        tagline = Text("{tagline}", font="Sans", font_size=32, color=BLACK)
        tagline.next_to(text, DOWN, buff=0.8)
        
        self.play(Write(text), run_time=1)
        self.wait(0.5)
        self.play(Write(tagline), run_time=0.8)
        self.wait(2)
        self.play(FadeOut(text), FadeOut(tagline), run_time=1)
'''
        else:
            code += f'''        
        self.play(Write(text), run_time=1)
        self.wait(3)
        self.play(FadeOut(text), run_time=1)
'''
    
    code += '''        self.wait(0.3)
'''
    
    return code


def generate_product_scene_code(scene: dict) -> str:
    """
    Generate Manim code for product scene with product image.
    """
    scene_id = scene.get("scene_id", 1)
    product_image_path = scene.get("product_image_path", "")
    product_name = scene.get("product_name", "Product")
    
    code = f'''from manim import *
from manim import config
from pathlib import Path

class Scene{scene_id}(Scene):
    def construct(self):
        # Set white background
        self.camera.background_color = WHITE
        
        # Define custom colors
        medical_blue = "#2E86AB"
        
'''
    
    if product_image_path:
        code += f'''        # Load product image
        try:
            product = ImageMobject("{product_image_path}")
            product.height = config.frame_height * 0.5
            product.move_to(ORIGIN)
            
            # Add product name
            product_text = Text("{product_name}", font="Sans", font_size=40, color=BLACK)
            product_text.to_edge(UP, buff=0.5)
            
            self.play(Write(product_text), run_time=0.8)
            self.wait(0.3)
            self.play(FadeIn(product, scale=0.9), run_time=1.2)
            self.wait(2.5)
            self.play(FadeOut(product_text), FadeOut(product), run_time=1)
            
        except Exception as e:
            # Fallback: Show text if image fails
            text = Text("{product_name}", font="Sans", font_size=48, color=BLACK)
            text.move_to(ORIGIN)
            subtext = Text("Available Now", font="Sans", font_size=32, color=medical_blue)
            subtext.next_to(text, DOWN, buff=0.8)
            
            self.play(Write(text), run_time=1)
            self.wait(0.5)
            self.play(Write(subtext), run_time=0.8)
            self.wait(2)
            self.play(FadeOut(text), FadeOut(subtext), run_time=1)
'''
    else:
        # No product image provided - show product name text
        code += f'''        text = Text("{product_name}", font="Sans", font_size=48, color=BLACK)
        text.move_to(ORIGIN)
        subtext = Text("Available Now", font="Sans", font_size=32, color=medical_blue)
        subtext.next_to(text, DOWN, buff=0.8)
        
        self.play(Write(text), run_time=1)
        self.wait(0.5)
        self.play(Write(subtext), run_time=0.8)
        self.wait(2)
        self.play(FadeOut(text), FadeOut(subtext), run_time=1)
'''
    
    code += '''        self.wait(0.3)
'''
    
    return code


def generate_manim_scene(scene: dict, retry_count: int = 0, max_retries: int = 2) -> tuple[int, str]:
    """
    Generate Manim code with syntax validation only (runtime deferred to render).
    
    For logo scenes, generates simple logo display code.
    For product scenes, generates product image display code.
    For other scenes, uses LLM to generate code.
    
    Flow:
    1. Generate code
    2. Syntax validation
    3. Save
    """
    scene_id = scene.get("scene_id", 1)
    scene_type = scene.get("type", "manim")
    
    # Handle logo scenes specially
    if scene_type == "logo":
        logger.info(f"Scene {scene_id}: Generating logo scene code", extra={'progress': True})
        manim_code = generate_logo_scene_code(scene)
        return (scene_id, manim_code)
    
    # Handle product scenes specially
    if scene_type == "product":
        logger.info(f"Scene {scene_id}: Generating product scene code", extra={'progress': True})
        manim_code = generate_product_scene_code(scene)
        return (scene_id, manim_code)
    
    # Regular manim scene generation
    prompt_path = PROMPTS_DIR / "manim_generator.txt"
    prompt_template = prompt_path.read_text(encoding="utf-8")
    
    scene_id = scene.get("scene_id", 1)
    duration = scene.get("duration_sec", 10)
    visual_elements = scene.get("visual_elements", [])
    
    prompt = prompt_template.replace("{scene_json}", json.dumps(scene, indent=2)) \
                           .replace("{duration}", str(duration)) \
                           .replace("{visual_elements}", ", ".join(visual_elements)) \
                           .replace("{scene_id}", str(scene_id))
    
    logger.info(f"Scene {scene_id}: Generating code (attempt {retry_count + 1})", extra={'progress': True})
    
    output = call_llm(prompt, temperature=0)
    result = extract_json(output)
    
    manim_code = result.get("manim_code", "")
    if not manim_code:
        raise ValueError(f"No code returned for scene {scene_id}")
    
    # Step 1: Syntax validation (optional)
    if validate_manim_code:
        is_valid, error_msg = validate_manim_code(manim_code, scene_id)
        
        if not is_valid:
            logger.warning(f"Scene {scene_id}: Syntax validation failed - {error_msg[:100]}", extra={'progress': True})
            
            if retry_count < max_retries:
                return generate_manim_scene(scene, retry_count + 1, max_retries)
            else:
                raise ValueError(f"Syntax validation failed: {error_msg}")
    
    logger.info(f"Scene {scene_id}: Code generated ✓", extra={'progress': True})
    return (scene_id, manim_code)


def run_stage2_doctor(scenes_data: dict, script: list[dict], video_id: str, max_workers: int = 3) -> Path:
    """
    Generate Manim code for ALL scenes (no type filter).
    
    Args:
        scenes_data: Scene planning output
        script: Narration scripts
        video_id: Video ID
        max_workers: Parallel workers
    
    Returns:
        Path to Manim scenes directory
    """
    stage_logger = StageLogger("Doctor Manim Generation")
    stage_logger.start()
    
    scenes = scenes_data.get("scenes", [])
    
    if not scenes:
        logger.warning("No scenes found")
        return None
    
    manim_scenes_dir = MANIM_DIR / video_id / "scenes"
    manim_scenes_dir.mkdir(parents=True, exist_ok=True)
    
    # Add narration
    script_map = {s["scene_id"]: s["script"] for s in script}
    for scene in scenes:
        scene["narration"] = script_map.get(scene["scene_id"], "")
    
    stage_logger.progress(f"Generating {len(scenes)} Manim scenes (parallel, workers={max_workers})...")
    
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
                logger.error(f"Scene {scene_id}: Failed - {str(e)[:150]}", extra={'progress': True})
                failed_scenes.append({"scene_id": scene_id, "error": str(e)[:500]})
                completed += 1
    
    # Save metadata
    metadata = {
        "video_id": video_id,
        "total_manim_scenes": len(scenes),
        "successful_scenes": len(scene_files),
        "failed_scenes": failed_scenes,
        "scenes_data": scenes_data
    }
    (manim_scenes_dir / "scenes_data.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    
    if not scene_files:
        stage_logger.error("All Manim scenes failed")
        raise RuntimeError("Failed to generate any valid Manim scenes")
    
    if failed_scenes:
        stage_logger.complete(f"{len(scene_files)}/{len(scenes)} OK, {len(failed_scenes)} failed")
    else:
        stage_logger.complete(f"All {len(scene_files)} Manim scenes generated")
    
    return manim_scenes_dir