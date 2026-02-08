import json
from pathlib import Path
from typing import Optional

from app.paths import PROMPTS_DIR, OUTPUTS_DIR
from app.utils.llm import call_llm


def generate_scenes(
    topic: str,
    video_type: str = "product_ad",
    brand_name: str = "",
    reference_docs: Optional[str] = None,
    region: Optional[str] = None,
) -> dict:
    """Plan pharma video scenes. video_type: brand_ad | patient_awareness | product_ad."""

    prompt_path = PROMPTS_DIR / "scene_planner_pharma.txt"

    # Add region context to the prompt if provided
    region_note = ""
    if region:
        region_note = f"\n\nREGION CONTEXT: {region.upper()}\n" \
                     f"Please generate search terms that would fetch media featuring people " \
                     f"from {region}. Incorporate regional/demographic context naturally."

    prompt = prompt_path.read_text(encoding="utf-8").format(
        video_type=video_type,
        brand_name=brand_name or "Our Brand",
        topic=topic,
        reference_docs=(reference_docs[:6000] if reference_docs else ""),
    ) + region_note

    output = call_llm(prompt)
    data = json.loads(output)

    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    (OUTPUTS_DIR / "scenes.json").write_text(json.dumps(data, indent=2))

    return data
