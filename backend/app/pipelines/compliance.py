import time
import json
from fastapi import UploadFile

from app.utils.logging_config import StageLogger
from app.utils.generate_uid import generate_video_id
from app.utils.assets import save_uploaded_assets, assets_to_prompt_text
from app.compliance_stages.stage1_scenes import generate_scenes
from app.utils.documents import extract_documents_text



def run_compliance_pipeline(
    payload: dict,
    documents: list[UploadFile],
    logo: UploadFile | None,
    images: list[UploadFile],
) -> dict:
    """
    Compliance pipeline (Stage 1 only for now).
    """

    pipeline_logger = StageLogger("Compliance Scene Planning")
    pipeline_start = time.time()

    video_id = generate_video_id()

    # --- Context ---
    document_context = extract_documents_text(documents) if documents else ""

    asset_ctx = save_uploaded_assets(
        video_id=video_id,
        logo=logo,
        images=images,
    )
    asset_context_text = assets_to_prompt_text(asset_ctx)

    # --- Stage 1 ---
    scenes_data = generate_scenes(
        topic=payload["prompt"],
        video_type=payload["video_type"],
        brand_name=payload.get("brand_name", ""),
        persona=payload.get("persona", ""),
        tone=payload.get("tone", ""),
        reference_docs=document_context,
        asset_context=asset_context_text,
    )

    elapsed = round(time.time() - pipeline_start, 1)

    return {
        "video_id": video_id,
        "video_type": payload["video_type"],
        "scenes": scenes_data,
        "elapsed_seconds": elapsed,
    }
