import json
from string import Template

from app.paths import PROMPTS_DIR, OUTPUTS_DIR
from app.utils.llm import call_llm


def generate_scenes(
    topic: str,
    video_type: str = "compliance_video",
    brand_name: str = "",
    persona: str = "",
    tone: str = "",
    reference_docs: str | None = None,
    asset_context: str = "",
) -> dict:
    """Plan pharma/compliance video scenes."""

    prompt_path = PROMPTS_DIR / "compliance_prompts" / "scene_planner.txt"
    template = Template(prompt_path.read_text(encoding="utf-8"))

    prompt = template.substitute(
        video_type=video_type,
        brand_name=brand_name or "Our Brand",
        topic=topic,
        reference_docs=(reference_docs[:6000] if reference_docs else ""),
        asset_context=asset_context or "",
    )

    if persona or tone:
        prompt += f"\n\nPERSONA: {persona}\nTONE: {tone}"

    output = call_llm(prompt)

    try:
        data = json.loads(output)
    except json.JSONDecodeError:
        start = output.find("{")
        end = output.rfind("}") + 1
        data = json.loads(output[start:end])

    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    (OUTPUTS_DIR / "scenes.json").write_text(
        json.dumps(data, indent=2),
        encoding="utf-8",
    )

    return data
