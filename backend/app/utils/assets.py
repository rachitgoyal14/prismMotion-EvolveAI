from pathlib import Path
import shutil

from app.paths import REMOTION_DIR


def save_uploaded_assets(video_id: str, logo=None, images=None) -> dict:
    """
    Save uploaded assets to:
    remotion/public/media/{video_id}/

    Returns lightweight asset context (filenames only).
    """

    assets_dir = REMOTION_DIR / "public" / "media" / video_id
    assets_dir.mkdir(parents=True, exist_ok=True)

    context = {
        "logo": None,
        "images": []
    }

    if logo:
        path = assets_dir / logo.filename
        with open(path, "wb") as f:
            shutil.copyfileobj(logo.file, f)
        context["logo"] = logo.filename

    if images:
        for img in images:
            path = assets_dir / img.filename
            with open(path, "wb") as f:
                shutil.copyfileobj(img.file, f)
            context["images"].append(img.filename)

    return context


def assets_to_prompt_text(ctx: dict) -> str:
    """
    Convert asset info into LLM-readable context.
    """
    if not ctx:
        return ""

    lines = ["AVAILABLE VISUAL ASSETS:"]

    if ctx.get("logo"):
        lines.append(f"- Brand logo: {ctx['logo']}")

    if ctx.get("images"):
        lines.append("- Uploaded images:")
        for img in ctx["images"]:
            lines.append(f"  - {img}")

    lines.append("")
    lines.append("GUIDELINES:")
    lines.append("- Prefer using the logo in intro or outro scenes")
    lines.append("- Prefer uploaded images over stock visuals when relevant")

    return "\n".join(lines)
