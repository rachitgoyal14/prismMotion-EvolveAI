import json
from pathlib import Path

from app.paths import PROMPTS_DIR, OUTPUTS_DIR
from app.utils.llm import call_llm


def generate_script(
    scenes: list[dict],
    persona: str = "professional narrator",
    tone: str = "clear and reassuring",
    reference_docs: str | None = None,
    language: str = "english",
) -> list[dict]:
    """Generate narration script per scene."""

    prompt_path = PROMPTS_DIR / "script_writer_pharma.txt"

    scenes_json = json.dumps(
        [
            {
                "scene_id": s["scene_id"],
                "concept": s.get("concept", ""),
                "duration_sec": s.get("duration_sec", 6),
            }
            for s in scenes
        ],
        indent=2,
    )

    # Add language instruction
    language_note = ""
    if language.lower() != "english":
        language_note = f"\n\nIMPORTANT: Generate the script in {language.upper()}. All narration text must be in {language}."

    prompt = prompt_path.read_text(encoding="utf-8").format(
        scenes=scenes_json,
        persona=persona,
        tone=tone,
        reference_docs=(reference_docs[:6000] if reference_docs else ""),
    ) + language_note

    output = call_llm(prompt)
    script = json.loads(output)

    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    (OUTPUTS_DIR / "script.json").write_text(json.dumps(script, indent=2))

    return script
