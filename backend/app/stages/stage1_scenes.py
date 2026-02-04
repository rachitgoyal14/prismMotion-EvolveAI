import json
from pathlib import Path

from app.paths import PROMPTS_DIR, OUTPUTS_DIR
from app.utils.llm import call_llm


def generate_scenes(
    topic: str,
    video_type: str = "product_ad",
    brand_name: str = "",
) -> dict:
    """Plan pharma video scenes. video_type: brand_ad | patient_awareness | product_ad."""
    prompt_path = PROMPTS_DIR / "scene_planner_pharma.txt"
    prompt = prompt_path.read_text(encoding="utf-8").format(
        video_type=video_type,
        brand_name=brand_name or "Our Brand",
        topic=topic,
    )
    output = call_llm(prompt)
    data = json.loads(output)
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    (OUTPUTS_DIR / "scenes.json").write_text(json.dumps(data, indent=2))
    return data
