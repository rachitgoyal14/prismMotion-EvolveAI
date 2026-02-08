"""
Stage 1 Doctor Ad: Plan scenes for HCP-focused promotional video.
Mix of Manim (scientific) + Product image + Logo (closing branding).
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
    logo_path: str | None = None,
    product_image_path: str | None = None,
    image_paths: list[str] | None = None,
    reference_docs: str | None = None
) -> dict:
    """
    Generate scene breakdown for doctor-facing video.
    
    Args:
        drug_name: Name of drug
        indication: Medical indication
        moa_summary: Optional mechanism summary
        clinical_data: Optional clinical trial data
        logo_path: Path to company logo for final scene
        product_image_path: Path to product image for product scene
        image_paths: Optional list of paths to images that can be referenced in scenes
        reference_docs: Optional text from documents to inform scene planning
    
    Returns:
        dict with structure:
        {
            "video_type": "doctor_ad",
            "drug_name": "...",
            "scenes": [
                {"scene_id": 1, "type": "manim", "duration_sec": 10, ...},
                {"scene_id": 2, "type": "product", "duration_sec": 7, "product_name": "..."},
                {"scene_id": 3, "type": "logo", "duration_sec": 6, "tagline": "..."}
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
    if reference_docs:
        context += f"\nReference Docs: {reference_docs[:6000]}"  # Truncate for prompt
    if logo_path:
        context += f"\nLogo: {logo_path}"
    if product_image_path:
        context += f"\nProduct Image: {product_image_path}"
    if image_paths:
        context += f"\nImages: {', '.join(image_paths)}"
    if context:
        prompt_template += f"\n\nCONTEXT:\n{context}"
    
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
    if logo_path:
        scenes_data["logo_path"] = logo_path
    if product_image_path:
        scenes_data["product_image_path"] = product_image_path
    if image_paths:
        scenes_data["image_paths"] = image_paths
    if reference_docs:
        scenes_data["reference_docs"] = reference_docs[:6000]  # Store a truncated version for reference
    

    # Ensure correct scene order: Manim scenes → Product → Logo
    scenes = scenes_data["scenes"]
    has_product = any(s.get("type") == "product" for s in scenes)
    has_logo = any(s.get("type") == "logo" for s in scenes)
    
    # Add missing product scene before logo if needed
    if not has_product and scenes:
        logger.warning("No Product scene found, adding product scene")
        # Insert product scene before logo (or at the end if no logo)
        if has_logo:
            # Find logo scene and insert product before it
            logo_idx = next(i for i, s in enumerate(scenes) if s.get("type") == "logo")
            scenes.insert(logo_idx, {
                "scene_id": len(scenes) + 1,
                "type": "product",
                "duration_sec": 7,
                "concept": "Product showcase",
                "product_name": drug_name,
                "narration_key_points": [
                    f"{drug_name} - Available for your patients",
                    "Contact your medical representative"
                ]
            })
            # Renumber scenes
            for i, scene in enumerate(scenes, 1):
                scene["scene_id"] = i
        else:
            # Add at end
            scenes.append({
                "scene_id": len(scenes) + 1,
                "type": "product",
                "duration_sec": 7,
                "concept": "Product showcase",
                "product_name": drug_name,
                "narration_key_points": [
                    f"{drug_name} - Available for your patients",
                    "Contact your medical representative"
                ]
            })
    
    # Add missing logo scene at the end if needed
    if not has_logo and scenes:
        logger.warning("No Logo scene found, adding closing scene")
        scenes.append({
            "scene_id": len(scenes) + 1,
            "type": "logo",
            "duration_sec": 6,
            "concept": "Company branding closure",
            "tagline": "Innovating Healthcare Solutions",
            "narration_key_points": [
                "Full prescribing information available"
            ]
        })
    
    logger.info(f"Generated {len(scenes)} scenes ({len([s for s in scenes if s['type']=='manim'])} Manim, {len([s for s in scenes if s['type']=='product'])} Product, {len([s for s in scenes if s['type']=='logo'])} Logo)")
    
    return scenes_data