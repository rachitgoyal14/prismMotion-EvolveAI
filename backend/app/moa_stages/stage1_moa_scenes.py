"""
Stage 1 MoA: Plan scenes for Mechanism of Action video.
Reuses existing infrastructure but with MoA-specific prompt.
"""
from pathlib import Path
from app.utils.llm import call_llm
from app.utils.json_safe import extract_json
from app.paths import PROMPTS_DIR
import logging


def generate_moa_scenes(
    drug_name: str,
    condition: str,
    target_audience: str = "healthcare professionals",
    logo_path: str | None = None,
    image_paths: list[str] | None = None,
    reference_docs: str | None = None,
) -> dict:
    """
    Generate scene breakdown for MoA video.
    
    Args:
        drug_name: Name of the drug/medicine
        condition: Medical condition being treated
        target_audience: "patients" | "healthcare professionals" | "medical students"
        logo_path: Optional path to brand logo for inclusion in scenes
        image_paths: Optional list of paths to images that can be referenced in scenes
        reference_docs: Optional text from documents to inform scene planning

    
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
    
    prompt = prompt_template.format(
        drug_name=drug_name,
        condition=condition,
        target_audience=target_audience,
    )

    if logo_path:
        prompt += f"\n\nLOGO: {logo_path}"
    if image_paths:
        prompt += f"\n\nIMAGES: {', '.join(image_paths)}"
    if reference_docs:
        prompt += f"\n\nREFERENCE_DOCS: {reference_docs[:6000]}"
    
    output = call_llm(prompt)
    logger = logging.getLogger(__name__)
    preview = (output[:2000] + '...') if output and len(output) > 2000 else (output or '<empty>')
    logger.info(f"LLM output preview (first 2000 chars):\n{preview}")
    # Attempt to parse JSON returned by the LLM. If parsing fails, log the
    # raw output (truncated) to help debugging unpredictable LLM responses.
    try:
        scenes_data = extract_json(output)
        # Log parsed keys for quick insight
        if isinstance(scenes_data, dict):
            logger.info(f"Parsed LLM JSON keys: {list(scenes_data.keys())}")
        else:
            logger.info(f"Parsed LLM JSON type: {type(scenes_data)}, repr: {repr(scenes_data)[:200]}")
    except Exception as e:
        # Log a truncated version of the LLM output for debugging
        preview = output[:2000] if output else "<empty>"
        logger.error(f"Failed to parse LLM output for MoA scenes: {e}\n---LLM output preview---\n{preview}\n---END PREVIEW---")
        raise ValueError(f"LLM returned unparsable JSON for MoA scenes: {e}")
    
    # Ensure required fields
    if "scenes" not in scenes_data:
        raise ValueError("LLM did not return valid scenes structure")
    
    # Add metadata
    scenes_data["drug_name"] = drug_name
    scenes_data["condition"] = condition
    scenes_data["target_audience"] = target_audience
    scenes_data["video_type"] = "mechanism_of_action"
    if logo_path:
        scenes_data["logo_path"] = logo_path
    if image_paths:
        scenes_data["image_paths"] = image_paths
    if reference_docs:
        scenes_data["reference_docs"] = reference_docs[:6000]  # Store a truncated version for reference
    
    return scenes_data