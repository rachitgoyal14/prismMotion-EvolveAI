"""
Stage 1 Doctor Ad: Plan scenes for HCP-focused promotional video.
Mix of Manim (scientific) + 1 Pexels (closing visual).
"""
from pathlib import Path
from app.utils.llm import call_llm
from app.utils.json_safe import extract_json
from app.paths import PROMPTS_DIR

import logging
logger = logging.getLogger(__name__)


def generate_doctor_scenes(
    drug_name: str,
    indication: str,
    moa_summary: str = "",
    clinical_data: str = "",
    pexels_query: str = "doctor consultation"
) -> dict:
    """
    Generate scene breakdown for doctor-facing video.
    
    Args:
        drug_name: Name of drug
        indication: Medical indication
        moa_summary: Optional mechanism summary
        clinical_data: Optional clinical trial data
        pexels_query: Query for final Pexels scene
    
    Returns:
        dict with structure:
        {
            "video_type": "doctor_ad",
            "drug_name": "...",
            "scenes": [
                {"scene_id": 1, "type": "manim", "duration_sec": 10, ...},
                {"scene_id": 2, "type": "pexels", "duration_sec": 6, "pexels_query": "..."}
            ]
        }
    """
    prompt_path = PROMPTS_DIR / "scene_planner_doctor.txt"
    
    if not prompt_path.exists():
        raise FileNotFoundError(f"Prompt not found: {prompt_path}")
    
    prompt_template = prompt_path.read_text(encoding="utf-8")
    
    # Build context string
    context = f"Drug: {drug_name}\nIndication: {indication}"
    if moa_summary:
        context += f"\nMechanism: {moa_summary}"
    if clinical_data:
        context += f"\nClinical Data: {clinical_data}"
    
    prompt = prompt_template.replace("{drug_name}", drug_name) \
                           .replace("{indication}", indication)
    
    logger.info(f"Generating doctor ad scenes for {drug_name}...")
    
    output = call_llm(prompt)
    scenes_data = extract_json(output)
    
    # Validate structure
    if "scenes" not in scenes_data:
        raise ValueError("LLM did not return valid scenes structure")
    
    # Add metadata
    scenes_data["drug_name"] = drug_name
    scenes_data["indication"] = indication
    scenes_data["video_type"] = "doctor_ad"
    
    # Ensure last scene is Pexels
    scenes = scenes_data["scenes"]
    if scenes and scenes[-1]["type"] != "pexels":
        # Add Pexels closing scene if missing
        logger.warning("No Pexels scene found, adding closing scene")
        scenes.append({
            "scene_id": len(scenes) + 1,
            "type": "pexels",
            "duration_sec": 6,
            "concept": "Professional closing",
            "pexels_query": pexels_query,
            "narration_key_points": [
                "Contact your medical representative for more information"
            ]
        })
    
    logger.info(f"Generated {len(scenes)} scenes ({len([s for s in scenes if s['type']=='manim'])} Manim, {len([s for s in scenes if s['type']=='pexels'])} Pexels)")
    
    return scenes_data