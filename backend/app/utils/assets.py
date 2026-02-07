from pathlib import Path
import shutil

from app.paths import REMOTION_DIR
from app.utils.file_utils import sanitize_filename


def save_uploaded_assets(video_id: str, logo=None, images=None) -> dict:
    """
    Save uploaded assets to:
    remotion/public/media/{video_id}/
    
    Filenames are sanitized to remove problematic characters
    (non-breaking spaces, special characters, etc.)

    Returns lightweight asset context (sanitized filenames only).
    """

    assets_dir = REMOTION_DIR / "public" / "media" / video_id
    assets_dir.mkdir(parents=True, exist_ok=True)

    context = {
        "logo": None,
        "images": []
    }

    if logo and logo.filename:
        # Sanitize the filename before saving
        clean_name = sanitize_filename(logo.filename)
        path = assets_dir / clean_name
        
        with open(path, "wb") as f:
            shutil.copyfileobj(logo.file, f)
        
        context["logo"] = clean_name

    if images:
        for img in images:
            if img and img.filename:
                # Sanitize each image filename
                clean_name = sanitize_filename(img.filename)
                path = assets_dir / clean_name
                
                with open(path, "wb") as f:
                    shutil.copyfileobj(img.file, f)
                
                context["images"].append(clean_name)

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