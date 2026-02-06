"""
Stage 2.5: Generate animation metadata for scenes using LLM.
This stage creates animation configurations for entrance, exit, and transition animations.
"""
import json
import logging
from pathlib import Path


logger = logging.getLogger(__name__)

from app.paths import OUTPUTS_DIR
from app.utils.llm import call_llm

ANIMATION_PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "animation_generator.txt"


def generate_animations(video_id: str) -> dict:
    """
    Load scenes_with_media.json and generate animation metadata for each scene using LLM.
    Returns: animations dict with scene_id -> animation config mapping.
    """
    scenes_path = OUTPUTS_DIR / "scenes_with_media.json"
    if not scenes_path.exists():
        raise FileNotFoundError("Run stage 2 first: scenes_with_media.json not found")

    scenes_data = json.loads(scenes_path.read_text(encoding="utf-8"))
    
    # Load the animation prompt template
    if ANIMATION_PROMPT_PATH.exists():
        prompt_template = ANIMATION_PROMPT_PATH.read_text(encoding="utf-8")
    else:
        # Fallback prompt if file doesn't exist
        prompt_template = get_default_animation_prompt()

    # Prepare scenes data for the LLM
    scenes_json_str = json.dumps(scenes_data, indent=2)
    prompt = prompt_template.replace("{scenes_with_media_json}", scenes_json_str)

    logger.info("Calling LLM to generate animation metadata...")
    response = call_llm(prompt, temperature=0.7)

    try:
        # Parse the LLM response - should be JSON with "animations" key
        animation_data = json.loads(response)
        animations = animation_data.get("animations", [])
        
        # Convert list to dict for easier lookup
        animation_map = {}
        for anim in animations:
            scene_id = anim.get("scene_id")
            if scene_id:
                animation_map[scene_id] = anim.get("animation", {})
        
        # Save animations to file
        animations_path = OUTPUTS_DIR / "animations.json"
        animations_path.write_text(
            json.dumps({"animations": animation_map}, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )
        
        logger.info(f"Generated animations for {len(animation_map)} scenes")
        return animation_map
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse animation response from LLM: {e}")
        logger.error(f"Response was: {response}")
        raise


def get_default_animation_prompt() -> str:
    """Fallback prompt if animation_generator.txt is not found."""
    return """You are an expert at designing animations for pharmaceutical video presentations.

TASK:
Generate smooth, professional animation metadata for pharmaceutical video scenes. Each scene should have entrance, exit, and transition animations that enhance the viewing experience without being distracting.

ANIMATION TYPES AVAILABLE:
Entrance: fade, slideIn, slideUp, slideDown, slideLeft, slideRight, zoomIn
Exit: fade, slideOut, slideUp, slideDown, slideLeft, slideRight, zoomOut
Transition: fade, slideLeft, slideRight, slideUp, slideDown, zoomFade
Easing: linear, easeInOut, easeIn, easeOut
Duration: 0.3-1.0 seconds (suggest 0.5 for most cases)

GUIDELINES FOR PHARMACEUTICAL VIDEOS:
- Entrance animations: Use fade or slideIn for product reveals (0.5s), zoom for close-ups
- Exit animations: Use fade or subtle slide to smoothly transition to next scene (0.5s)
- Transitions: Use fade or slideLeft for main transitions (0.5s), keep professional
- Avoid jarring or overly complex animations
- Match animation style to scene content

INPUT (scenes with media and script):
{scenes_with_media_json}

OUTPUT: Return ONLY a JSON object:
{{
  "animations": [
    {{
      "scene_id": 1,
      "animation": {{
        "entrance": {{"type": "fade", "duration_sec": 0.5, "easing": "easeOut"}},
        "exit": {{"type": "fade", "duration_sec": 0.5, "easing": "easeIn"}},
        "transition": {{"type": "slideLeft", "duration_sec": 0.5, "easing": "easeInOut"}}
      }}
    }}
  ]
}}"""
