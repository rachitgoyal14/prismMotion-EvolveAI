"""
Stage 1 Social Media: Plan short-form scenes for Instagram Reels.
Optimized for 15-60 second horizontal videos.
"""
from pathlib import Path
from app.utils.llm import call_llm
from app.utils.json_safe import extract_json
from app.paths import PROMPTS_DIR

import logging
logger = logging.getLogger(__name__)


def generate_sm_scenes(
    drug_name: str,
    indication: str,
    key_benefit: str = "",
    target_audience: str = "patients",
) -> dict:
    """
    Generate scene breakdown for social media (Instagram Reels, TikTok, etc).
    
    Args:
        drug_name: Name of drug
        indication: Medical indication
        key_benefit: Key benefit statement
        target_audience: Target audience (patients, doctors, etc)
        pexels_query: Query for visual assets
    
    Returns:
        dict with scenes list and metadata
    """
    
    # Load prompt template
    prompt_path = PROMPTS_DIR / "scene_planner_pharma.txt"
    if not prompt_path.exists():
        raise FileNotFoundError(f"Prompt not found: {prompt_path}")
    
    template = prompt_path.read_text(encoding="utf-8")
    
    prompt = template.replace("{topic}", drug_name) \
                     .replace("{indication}", indication) \
                     .replace("{key_benefit}", key_benefit) \
                     .replace("{target_audience}", target_audience)
    
    logger.info(f"Generating SM scenes for {drug_name} ({indication})")
    
    # Call LLM
    full_prompt = f"""You are a creative pharma video content planner. Design engaging short-form video scenes (15-60 sec) for social media.

{prompt}"""
    response = call_llm(full_prompt)
    
    # Extract JSON
    scenes_data = extract_json(response)
    
    if not isinstance(scenes_data, dict):
        scenes_data = {"scenes": []}
    
    # Ensure each scene has required fields
    scenes = scenes_data.get("scenes", [])
    for i, scene in enumerate(scenes):
        if "scene_id" not in scene:
            scene["scene_id"] = i
        if "type" not in scene:
            scene["type"] = "manim"  # Default to Manim for animations
    
    logger.info(f"Generated {len(scenes)} social media scenes")
    
    return {
        "scenes": scenes,
        "metadata": {
            "drug_name": drug_name,
            "indication": indication,
            "key_benefit": key_benefit,
            "target_audience": target_audience,
        }
    }
