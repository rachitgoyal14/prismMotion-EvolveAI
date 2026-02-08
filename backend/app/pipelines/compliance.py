import time
from fastapi import UploadFile

from app.utils.logging_config import StageLogger
from app.utils.generate_uid import generate_video_id
from app.utils.assets import save_uploaded_assets, assets_to_prompt_text
from app.utils.documents import extract_documents_text

from app.compliance_stages.stage1_scenes import generate_scenes
from app.compliance_stages.stage2_assets import run_compliance_stage2
from app.stages.stage3_script import generate_script
from app.stages.stage4_tts import tts_generate
from app.compliance_stages.stage5_render import render_compliance_video


def run_compliance_pipeline(
    payload: dict,
    documents: list[UploadFile],
    logo: UploadFile | None,
    images: list[UploadFile],
) -> dict:
    """
    Full compliance video pipeline.
    Fancy, deterministic, and auditable.
    """

    pipeline_logger = StageLogger("Compliance Pipeline")
    pipeline_start = time.time()

    video_id = generate_video_id()

    # =====================
    # Stage 0: Context Prep
    # =====================
    document_context = extract_documents_text(documents) if documents else ""

    asset_ctx = save_uploaded_assets(
        video_id=video_id,
        logo=logo,
        images=images,
    )
    asset_context_text = assets_to_prompt_text(asset_ctx)

    # =====================
    # Stage 1: Scene Planning (LLM)
    # =====================
    stage_logger = StageLogger("Scene Planning")
    stage_logger.start()

    scenes_data = generate_scenes(
        topic=payload["prompt"],
        video_type=payload["video_type"],
        brand_name=payload.get("brand_name", ""),
        persona=payload.get("persona", ""),
        tone=payload.get("tone", ""),
        reference_docs=document_context,
        asset_context=asset_context_text,
    )

    stage_logger.complete(f"{len(scenes_data.get('scenes', []))} scenes planned")

    # =====================
    # Stage 2: Asset Resolution
    # =====================
    stage_logger = StageLogger("Asset Resolution")
    stage_logger.start()

    resolved_scenes = run_compliance_stage2(
        scenes_data=scenes_data,
        video_id=video_id,
        assets=asset_ctx,
    )

    stage_logger.complete("Assets resolved")

    # =====================
    # Stage 3: Script Writing
    # =====================
    stage_logger = StageLogger("Script Writing")
    stage_logger.start()

    script = generate_script(
        scenes=resolved_scenes["scenes"],
        persona=payload.get("persona", "compliance officer"),
        tone=payload.get("tone", "formal and precise"),
        reference_docs=document_context,
    )

    stage_logger.complete("Script generated")

    # =====================
    # Stage 4: Text-to-Speech
    # =====================
    scene_ids = [s["scene_id"] for s in resolved_scenes["scenes"]]
    tts_generate(
        script=script,
        video_id=video_id,
        scene_ids=scene_ids,
    )

    # =====================
    # Stage 5: Render (Remotion)
    # =====================
    stage_logger = StageLogger("Remotion Render")
    stage_logger.start()

    final_path = render_compliance_video(video_id)

    stage_logger.complete(f"Rendered {final_path.name}")

    elapsed = round(time.time() - pipeline_start, 1)

    return {
        "status": "complete",
        "video_id": video_id,
        "video_type": payload["video_type"],
        "video_path": str(final_path),
        "video_url": f"/outputs/videos/{video_id}/final.mp4",
        "elapsed_seconds": elapsed,
    }
