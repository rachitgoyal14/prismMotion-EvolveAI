from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
PROMPTS_DIR = BASE_DIR / "prompts"
OUTPUTS_DIR = BASE_DIR / "outputs"
MEDIA_DIR = BASE_DIR / "media"

# Remotion project (sibling to backend)
PROJECT_ROOT = BASE_DIR.parents[1]
REMOTION_DIR = PROJECT_ROOT / "remotion"

PROMPTS_DIR.mkdir(exist_ok=True)
OUTPUTS_DIR.mkdir(exist_ok=True)
