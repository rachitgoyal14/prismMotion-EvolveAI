"""
Stage 1 MoA: Plan scenes for Mechanism of Action video.
Reuses existing infrastructure but with MoA-specific prompt.
"""
from pathlib import Path
from app.utils.llm import call_llm
from app.utils.json_safe import extract_json
from app.paths import PROMPTS_DIR


def generate_moa_scenes(
    drug_name: str,
    condition: str,
    target_audience: str = "healthcare professionals"
) -> dict:
    """
    Generate scene breakdown for MoA video.
    
    Args:
        drug_name: Name of the drug/medicine
        condition: Medical condition being treated
        target_audience: "patients" | "healthcare professionals" | "medical students"
    
    Returns:
        dict with structure:
        {
            "video_type": "mechanism_of_action",
            "drug_name": "...",
            "condition": "...",
            "scenes": [{"scene_id": 1, "duration_sec": 10, ...}]
        }
    """
    prompt_path = PROMPTS_DIR / "scene_planner_moa.txt"
    prompt_template = prompt_path.read_text(encoding="utf-8")
    
    prompt = prompt_template.replace("{drug_name}", drug_name) \
                           .replace("{condition}", condition) \
                           .replace("{target_audience}", target_audience)
    
    output = call_llm(prompt)
    scenes_data = extract_json(output)
    
    # Ensure required fields
    if "scenes" not in scenes_data:
        raise ValueError("LLM did not return valid scenes structure")
    
    # Add metadata
    scenes_data["drug_name"] = drug_name
    scenes_data["condition"] = condition
    scenes_data["target_audience"] = target_audience
    scenes_data["video_type"] = "mechanism_of_action"
    
    return scenes_data