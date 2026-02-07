import json
import logging
from app.paths import OUTPUTS_DIR
from app.utils.file_utils import sanitize_filename
logger = logging.getLogger(__name__)


def run_compliance_stage2(
    scenes_data: dict,
    video_id: str,
    assets: dict,
) -> dict:
    """
    Resolve uploaded assets into Remotion-ready paths.
    """
    scenes = scenes_data.get("scenes", [])
    base = f"media/{video_id}"

    logo = assets.get("logo")
    images = assets.get("images", [])

    for s in scenes:
        s["image"] = None
        hint = s.get("asset_hint")
        preferred = s.get("preferred_asset")

        # Logo scene
        if hint == "logo" and logo:
            clean_logo = sanitize_filename(logo)
            s["image"] = {
                "src": f"{base}/{clean_logo}",
                "alt": "Brand logo",
            }

        # Uploaded image scene
        elif hint == "uploaded_image":
            filename = None

            if preferred and preferred in images:
                filename = preferred
            elif images:
                filename = images[0]

            if filename:
                clean_filename = sanitize_filename(filename)
                s["image"] = {
                    "src": f"{base}/{clean_filename}",
                    "alt": s.get("concept", ""),
                }

    enriched = {
        "video_type": scenes_data.get("video_type"),
        "brand_name": scenes_data.get("brand_name"),
        "scenes": scenes,
    }

    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    (OUTPUTS_DIR / "compliance_scenes_with_media.json").write_text(
        json.dumps(enriched, indent=2),
        encoding="utf-8",
    )

    logger.info("Compliance Stage 2 complete (assets mapped)")
    return enriched

