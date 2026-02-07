"""
Pharma video generation pipeline with logging, timing,
and company asset upload support.
"""
import json
from pathlib import Path
import time
import os
import shutil
import uuid
from typing import Annotated, Optional, List
import mimetypes
import logging
import subprocess
import requests
import base64
import tempfile
from typing import Union

from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv())

from fastapi import (
    FastAPI,
    HTTPException,
    Request,
    File,
    UploadFile,
    Form,
    Depends
)
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import io

# Logging setup
from app.utils.logging_config import setup_logging, StageLogger
from app.utils.video_utils import convert_to_portrait_9_16

from app.utils.video_utils import convert_to_portrait_9_16
from app.utils.video_utils import convert_to_portrait_9_16
from app.chat.routes import router as chat_router
setup_logging(level=logging.INFO)
logger = logging.getLogger(__name__)

from app.utils.generate_uid import generate_video_id

# Utils
from app.utils.documents import extract_documents_text

# Compliance pipeline
from app.pipelines.compliance import run_compliance_pipeline

# Remotion pipeline
from app.stages.stage1_scenes import generate_scenes
from app.stages.stage3_script import generate_script
from app.stages.stage2_remotion import run_stage2
from app.stages.stage2_5_animations import generate_animations
from app.stages.stage4_tts import tts_generate
from app.stages.stage5_render import render_remotion

# MoA / Manim pipeline
from app.moa_stages.stage1_moa_scenes import generate_moa_scenes
from app.moa_stages.stage2_moa_manim import run_stage2_moa
from app.moa_stages.stage5_moa_render import render_moa_video

from app.paths import OUTPUTS_DIR
from app import db

# ---------------------------------------------------------------------

app = FastAPI(title="Pharma Video Generator")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

VIDEOS_DIR = OUTPUTS_DIR / "videos"

@app.on_event("startup")
async def startup_event():
    try:
        await db.init_db()
        logger.info("Database initialized")
    except Exception as e:
        logger.warning(f"DB init failed: {e}")

@app.on_event("shutdown")
async def shutdown_event():
    try:
        await db.close_db()
    except Exception:
        pass

# Pydantic models for documentation
class CreateRequest(BaseModel):
    """Pexels + Remotion video config."""
    video_type: str = "product_ad"
    topic: str
    brand_name: str = ""
    persona: str = "professional narrator"
    tone: str = "clear and reassuring"

class CreateMoARequest(BaseModel):
    """Mechanism of Action video using Manim."""
    drug_name: str
    condition: str
    target_audience: str = "healthcare professionals"
    persona: str = "professional medical narrator"
    tone: str = "clear and educational"
    quality: str = "low"

class CreateComplianceRequest(BaseModel):
    """Compliance video using Remotion with strict adherence to reference documents"""
    video_type: str = "compliance_video"
    prompt: str
    brand_name: str = ""
    persona: str = "compliance officer"
    tone: str = "formal and precise"

class CreateDoctorRequest(BaseModel):
    """Doctor-facing HCP promotional video using Manim + Pexels."""
    drug_name: str
    indication: str
    moa_summary: str = ""
    clinical_data: str = ""
    pexels_query: str = "doctor consultation"
    persona: str = "professional medical narrator"
    tone: str = "scientific and professional"
    quality: str = "low"


class CreateSocialMediaRequest(BaseModel):
    """Social media short-form video (Instagram Reels, TikTok) using Manim + Pexels."""
    drug_name: str
    indication: str
    key_benefit: str = ""
    target_audience: str = "patients"
    persona: str = "friendly health narrator"
    tone: str = "engaging and conversational"
    quality: str = "low"


class CreateSocialMediaRemotionRequest(BaseModel):
    """Social media short-form video (Instagram Reels, TikTok) using Remotion + Pexels."""
    topic: str
    brand_name: str = ""
    persona: str = "friendly brand narrator"
    tone: str = "engaging and conversational"


class CreateVideoForm:
    def __init__(
        self,
        video_type: str = Form("product_ad"),
        topic: str = Form(...),
        brand_name: str = Form(""),
        persona: str = Form("professional narrator"),
        tone: str = Form("clear and reassuring"),
        logo: UploadFile | None = File(default=None),
        image: UploadFile | None = File(default=None),
    ):
        self.video_type = video_type
        self.topic = topic
        self.brand_name = brand_name
        self.persona = persona
        self.tone = tone

        # Convert to lists internally
        self.logos = [logo] if logo else []
        self.images = [image] if image else []



# ---------------------------------------------------------------------
# File helpers - FIXED
# ---------------------------------------------------------------------

ALLOWED_TYPES = {
    "image/png",
    "image/jpeg", 
    "image/jpg",
    "image/webp",
}

ALLOWED_DOC_TYPES = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",  # .docx
    "text/plain",
}


def filter_valid_files(
    files: List[UploadFile] | None,
    allowed_types: set = None
) -> List[UploadFile]:
    """Filter out invalid items and return only valid `UploadFile` objects."""
    if allowed_types is None:
        allowed_types = ALLOWED_TYPES
    
    # Define document extensions for fallback validation
    DOC_EXTENSIONS = {'.pdf', '.docx', '.doc', '.txt'}
    is_doc_filter = allowed_types == ALLOWED_DOC_TYPES
    
    valid = []
    
    # Handle None input
    if files is None:
        return valid
    
    # Handle non-list input
    if not isinstance(files, list):
        return valid
    
    # Handle empty list
    if not files:
        return valid
    
    logger.info(f"filter_valid_files: Processing {len(files)} items")
    
    for i, f in enumerate(files):
        # Check if it has the UploadFile interface
        if not hasattr(f, 'filename') or not hasattr(f, 'content_type') or not hasattr(f, 'file'):
            logger.info(f"  [{i}] -> Skipping: not an UploadFile-like object")
            continue
        
        logger.info(f"  [{i}] -> Is UploadFile-like object")
        logger.info(f"  [{i}]    filename: {f.filename}")
        logger.info(f"  [{i}]    content_type: {f.content_type}")
            
        if not f.filename:
            logger.warning(f"  [{i}] -> REJECTED: filename is empty")
            continue
        
        # PRIMARY: Check content_type
        is_valid_by_type = f.content_type and f.content_type in allowed_types
        
        # FALLBACK: For documents, also check file extension
        is_valid_by_ext = False
        if is_doc_filter and f.filename:
            file_ext = Path(f.filename).suffix.lower()
            is_valid_by_ext = file_ext in DOC_EXTENSIONS
            logger.info(f"  [{i}]    file extension: {file_ext}, valid: {is_valid_by_ext}")
        
        logger.info(f"  [{i}]    valid by content_type: {is_valid_by_type}")
        logger.info(f"  [{i}]    valid by extension: {is_valid_by_ext}")
        
        if is_valid_by_type or is_valid_by_ext:
            logger.info(f"  [{i}] ✓ ACCEPTED: {f.filename}")
            valid.append(f)
        else:
            logger.warning(f"  [{i}] ✗ REJECTED: {f.filename}, content_type={f.content_type}")
    
    logger.info(f"filter_valid_files: Returning {len(valid)} valid files")
    return valid


def _call_sadtalker_service(audio_path: str, image_path: Optional[str], sadtalker_url: str) -> str:
    """
    Call the external Sadtalker HTTP service and return the path to the generated video.
    Expects the service to accept multipart form with 'audio' and optional 'image'.
    The service may return a raw video body or JSON containing a base64-encoded video field named 'video'.
    """
    # Upload audio and optional image to the Sadtalker service, poll for completion,
    # then download the resulting video and return its path.
    files = {}
    f_audio = open(audio_path, "rb")
    files["audio"] = (Path(audio_path).name, f_audio)
    f_image = None
    if image_path:
        f_image = open(image_path, "rb")
        files["image"] = (Path(image_path).name, f_image)

    try:
        # Accept either a base URL (e.g. http://127.0.0.1:8001) or a full path
        # (e.g. http://127.0.0.1:8001/video/generate). Normalize to base.
        provided = sadtalker_url.rstrip("/")
        if provided.endswith("/video/generate"):
            base = provided[: -len("/video/generate")]
        elif provided.endswith("/video"):
            base = provided[: -len("/video")]
        else:
            base = provided

        endpoint = base + "/video/generate"
        resp = requests.post(endpoint, files=files, timeout=300)
    finally:
        try:
            f_audio.close()
        except Exception:
            pass
        if f_image:
            try:
                f_image.close()
            except Exception:
                pass

    if resp.status_code != 200:
        raise HTTPException(500, f"Sadtalker service error: {resp.status_code} - {resp.text}")

    data = resp.json()
    job_id = data.get("job_id")
    if not job_id:
        raise HTTPException(500, "Sadtalker service did not return job_id")

    # Poll status (use normalized base)
    status_url = base + f"/video/status/{job_id}"
    result_url = base + f"/video/result/{job_id}"

    timeout_secs = 2400  # 40 minutes (Sadtalker can take 30+ minutes)
    poll_interval = 5
    waited = 0
    while waited < timeout_secs:
        s = requests.get(status_url)
        if s.status_code == 200:
            sdata = s.json()
            if sdata.get("status") == "completed":
                # fetch the resulting video
                r = requests.get(result_url, timeout=300)
                if r.status_code == 200:
                    out_video_path = str(Path(audio_path).parent / "sadtalker_output.mp4")
                    with open(out_video_path, "wb") as f:
                        f.write(r.content)
                    return out_video_path
                else:
                    raise HTTPException(500, f"Failed fetching sadtalker result: {r.status_code}")
        else:
            logger.debug(f"Sadtalker job {job_id} polling... (waited {waited}s/{timeout_secs}s)")
        time.sleep(poll_interval)
        waited += poll_interval

    raise HTTPException(504, "Sadtalker service timeout waiting for job completion")


def _merge_videos_side_by_side(left_video: str, right_video: str, out_video: str, height: int = 720):
    """Merge two videos side-by-side using ffmpeg. Requires `ffmpeg` in PATH."""
    cmd = [
        "ffmpeg", "-y",
        "-i", left_video,
        "-i", right_video,
        "-filter_complex",
        f"[0:v]scale=-1:{height}[left];[1:v]scale=-1:{height}[right];[left][right]hstack=inputs=2[v]",
        "-map", "[v]",
        "-map", "0:a?",
        "-c:v", "libx264", "-crf", "23", "-preset", "veryfast",
        "-c:a", "aac", "-b:a", "128k",
        out_video,
    ]

    try:
        subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except subprocess.CalledProcessError as e:
        raise HTTPException(500, f"ffmpeg merge failed: {e.stderr.decode('utf-8', errors='ignore')}")

async def save_files(files: List[UploadFile] | None, target_dir: Path):
    if not files:
        return []

    saved_paths = []
    
    for file in files:
        # Skip ANY invalid file completely
        if not file.filename or not file.content_type:
            logger.warning(f"Skipping invalid file: {file.filename}, type: {file.content_type}")
            continue
            
        if file.content_type not in ALLOWED_TYPES:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid file type: {file.content_type}. Allowed: {ALLOWED_TYPES}"
            )

        ext = Path(file.filename).suffix
        safe_name = f"{uuid.uuid4()}{ext}"
        file_path = target_dir / safe_name

        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        saved_paths.append(str(file_path))

    return saved_paths

# ---------------------------------------------------------------------
# ENDPOINTS - ALL FIXED
# ---------------------------------------------------------------------

app.include_router(chat_router)

@app.post("/create")
async def create_video(
    video_type: str = Form("product_ad"),
    topic: str = Form(...),
    brand_name: str = Form(""),
    persona: str = Form("professional narrator"),
    tone: str = Form("clear and reassuring"),
    logo: Optional[UploadFile] = File(None),
    image: Optional[UploadFile] = File(None),
    documents: Union[List[UploadFile], List[str], None] = File(None),  # ✅ Accept strings too
    user_id: Optional[str] = Form(None),
):
    pipeline_start = time.time()
    video_id = generate_video_id()
    
    # ✅ Filter out strings and None, keep only UploadFile-like objects
    docs = []
    if documents is not None:
        for d in documents:
            # Skip strings
            if isinstance(d, str):
                continue
            # Check if it has UploadFile interface (duck typing)
            if hasattr(d, 'filename') and hasattr(d, 'file') and hasattr(d, 'content_type'):
                if d.filename:  # Has a real filename
                    docs.append(d)
    
    # ✅ FILTER FILES WITH CORRECT TYPES
    logos = [logo] if logo and logo.filename and logo.content_type else []
    images = [image] if image and image.filename and image.content_type else []
    
    logger.info(f"DEBUG: Received {len(docs)} document(s) after filtering")
    if docs:
        for i, d in enumerate(docs):
            logger.info(f"  Document {i}: {d.filename} ({d.content_type})")
    
    valid_docs = filter_valid_files(docs, allowed_types=ALLOWED_DOC_TYPES)
    
    logger.info(f"Valid logos: {len(logos)}, images: {len(images)}, docs: {len(valid_docs)}")
    
    # ✅ Extract document text
    if valid_docs:
        logger.info(f"Valid documents: {[d.filename for d in valid_docs]}")
        reference_text = extract_documents_text(valid_docs)
        logger.info(f"Extracted reference text: {len(reference_text)} characters")
    else:
        logger.info("No valid documents found after filtering")
        reference_text = ""
    
    # DB setup
    try:
        uid = await db.ensure_user(user_id)
        session_id = await db.create_session(
            uid, video_id, status="processing", 
            metadata={"topic": topic, "video_type": video_type}
        )
        await db.create_video_record(video_id, session_id, path=None, state="processing")
    except Exception as e:
        logger.warning(f"DB record creation failed: {e}")

    logger.info(f"Starting Remotion pipeline - Video ID: {video_id}")

    # Save assets
    assets_dir = VIDEOS_DIR / video_id / "assets"
    logos_dir = assets_dir / "logos"
    images_dir = assets_dir / "images"

    logos_dir.mkdir(parents=True, exist_ok=True)
    images_dir.mkdir(parents=True, exist_ok=True)

    logo_paths = await save_files(logos, logos_dir)
    image_paths = await save_files(images, images_dir)

    logger.info(f"Saved {len(logo_paths)} logos and {len(image_paths)} images")

    try:
        # Stage 1
        scenes_data = generate_scenes(
            topic=topic,
            video_type=video_type,
            brand_name=brand_name or "Our Brand",
            reference_docs=reference_text,
        )

        scenes = scenes_data.get("scenes", [])
        if not scenes:
            raise HTTPException(500, "No scenes generated")

        # Script
        script = generate_script(
            scenes,
            persona=persona,
            tone=tone,
            reference_docs=reference_text if reference_text else None,
        )

        # Stage 2
        run_stage2(
            scenes_data,
            script,
            video_id,
            assets={"logos": logo_paths, "images": image_paths},
        )

        try:
            generate_animations(video_id)
        except Exception as e:
            logger.warning(f"Animation skipped: {e}")

        scene_ids = [s["scene_id"] for s in scenes]
        tts_generate(script=script, video_id=video_id, scene_ids=scene_ids)
        final_path = render_remotion(video_id)

        # Update DB
        try:
            await db.update_video_state(video_id, state="complete", path=str(final_path))
        except Exception as e:
            logger.warning(f"DB update failed: {e}")
        
        total_time = time.time() - pipeline_start
        return {
            "status": "complete",
            "video_id": video_id,
            "video_type": video_type,
            "video_path": str(final_path),
            "assets": {"logos": logo_paths, "images": image_paths},
            "elapsed_seconds": round(total_time, 1),
        }

    except Exception as e:
        logger.error(f"Pipeline failed: {e}", extra={"stage": "PIPELINE ERROR"})
        raise HTTPException(500, f"Pipeline failed: {e}")

@app.post("/create-compliance")
async def create_compliance_video(
    video_type: str = Form("compliance_video"),
    prompt: str = Form(...),
    brand_name: str = Form(""),
    persona: str = Form("compliance officer"),
    tone: str = Form("formal and precise"),
    user_id: Optional[str] = Form(None),
    documents: Union[List[UploadFile], List[str], None] = File(None),  # ✅ Accept strings
    logo: Optional[UploadFile] = File(None),
    images: Union[List[UploadFile], List[str], None] = File(None),  # ✅ Accept strings
):
    # ✅ Filter out strings using duck typing
    docs = []
    if documents is not None:
        for d in documents:
            if isinstance(d, str):
                continue
            if hasattr(d, 'filename') and hasattr(d, 'file') and hasattr(d, 'content_type'):
                if d.filename:
                    docs.append(d)
    
    imgs = []
    if images is not None:
        for i in images:
            if isinstance(i, str):
                continue
            if hasattr(i, 'filename') and hasattr(i, 'file') and hasattr(i, 'content_type'):
                if i.filename:
                    imgs.append(i)
    
    valid_docs = filter_valid_files(docs, allowed_types=ALLOWED_DOC_TYPES)
    valid_logo = logo if logo and logo.filename and logo.content_type else None
    valid_images = filter_valid_files(imgs, allowed_types=ALLOWED_TYPES)
    
    logger.info(f"Compliance: {len(valid_docs)} docs, logo: {valid_logo is not None}, {len(valid_images)} images")

    payload = {
        "video_type": video_type,
        "prompt": prompt,
        "brand_name": brand_name,
        "persona": persona,
        "tone": tone,
    }

    result = run_compliance_pipeline(
        payload=payload,
        documents=valid_docs,
        logo=valid_logo,
        images=valid_images,
    )

    return {"status": "ok", **result}

@app.post("/create-moa")
async def create_moa_video(
    drug_name: str = Form(...),
    condition: str = Form(...),
    target_audience: str = Form("healthcare professionals"),
    persona: str = Form("professional medical narrator"),
    tone: str = Form("clear and educational"),
    quality: str = Form("low"),
    user_id: Optional[str] = Form(None),
    documents: Union[List[UploadFile], List[str], None] = File(None),  # ✅ Accept strings
    logo: Optional[UploadFile] = File(None),
    images: Union[List[UploadFile], List[str], None] = File(None),  # ✅ Accept strings
):
    pipeline_start = time.time()
    video_id = generate_video_id()
    
    # ✅ Filter out strings using duck typing
    docs = []
    if documents is not None:
        for d in documents:
            if isinstance(d, str):
                continue
            if hasattr(d, 'filename') and hasattr(d, 'file') and hasattr(d, 'content_type'):
                if d.filename:
                    docs.append(d)
    
    imgs = []
    if images is not None:
        for i in images:
            if isinstance(i, str):
                continue
            if hasattr(i, 'filename') and hasattr(i, 'file') and hasattr(i, 'content_type'):
                if i.filename:
                    imgs.append(i)

    valid_docs = filter_valid_files(docs, allowed_types=ALLOWED_DOC_TYPES)
    valid_logo = logo if logo and logo.filename and logo.content_type else None
    valid_images = filter_valid_files(imgs, allowed_types=ALLOWED_TYPES)

    logger.info(f"MoA: {len(valid_docs)} docs, logo: {valid_logo is not None}, {len(valid_images)} images")

    return await create_doctor_video(
        drug_name=drug_name,
        indication=condition,
        moa_summary="",
        clinical_data="",
        pexels_query="",
        persona=persona,
        tone=tone,
        quality=quality,
        user_id=user_id,
        video_id=None,
        documents=docs,  # Pass the converted list
        logo=logo,
        images=imgs,  # Pass the converted list
    )

@app.post("/create-doctor")
async def create_doctor_video(
    drug_name: str = Form(...),
    indication: str = Form(...),
    moa_summary: str = Form(""),
    clinical_data: str = Form(""),
    pexels_query: str = Form("doctor consultation"),
    persona: str = Form("professional medical narrator"),
    tone: str = Form("scientific and professional"),
    quality: str = Form("low"),
    user_id: Optional[str] = Form(None),
    video_id: Optional[str] = Form(None),
    documents: Union[List[UploadFile], List[str], None] = File(None),  # ✅ Accept strings
    logo: Optional[UploadFile] = File(None),
    images: Union[List[UploadFile], List[str], None] = File(None),  # ✅ Accept strings
):
    from app.doctor_ad_stages.stage1_doctor_scenes import generate_doctor_scenes
    from app.doctor_ad_stages.stage2_doctor_manim import run_stage2_doctor
    from app.doctor_ad_stages.stage3_pexels_fetch import run_stage3_pexels
    from app.doctor_ad_stages.stage5_doctor_render import render_doctor_video

    pipeline_start = time.time()
    if not video_id:
        video_id = generate_video_id()
    
    # ✅ Filter out strings using duck typing
    docs = []
    if documents is not None:
        for d in documents:
            if isinstance(d, str):
                continue
            if hasattr(d, 'filename') and hasattr(d, 'file') and hasattr(d, 'content_type'):
                if d.filename:
                    docs.append(d)
    
    imgs = []
    if images is not None:
        for i in images:
            if isinstance(i, str):
                continue
            if hasattr(i, 'filename') and hasattr(i, 'file') and hasattr(i, 'content_type'):
                if i.filename:
                    imgs.append(i)

    valid_docs = filter_valid_files(docs, allowed_types=ALLOWED_DOC_TYPES)
    valid_logo = logo if logo and logo.filename and logo.content_type else None
    valid_images = filter_valid_files(imgs, allowed_types=ALLOWED_TYPES)

    logger.info(f"Doctor ad: {len(valid_docs)} docs, logo: {valid_logo is not None}, {len(valid_images)} images")

    try:
        uid = await db.ensure_user(user_id)
        session_id = await db.create_session(
            uid, video_id, status="processing",
            metadata={
                "drug_name": drug_name,
                "indication": indication,
                "video_type": "doctor_ad",
            }
        )
        await db.create_video_record(video_id, session_id, path=None, state="processing")
    except Exception as e:
        logger.warning(f"DB record creation failed: {e}")

    stage_logger = StageLogger("Doctor Scene Planning")
    stage_logger.start()

    scenes_data = generate_doctor_scenes(
        drug_name=drug_name,
        indication=indication,
        moa_summary=moa_summary,
        clinical_data=clinical_data,
        pexels_query=pexels_query,
        logo_path=valid_logo.filename if valid_logo else None,
        image_paths=[img.filename for img in valid_images],
        reference_docs=extract_documents_text(valid_docs) if valid_docs else None
    )

    scenes = scenes_data.get("scenes", [])
    stage_logger.complete(f"{len(scenes)} scenes planned")

    if not scenes:
        raise HTTPException(500, "No scenes generated")

    pexels_media = run_stage3_pexels(scenes_data, video_id)

    for scene in scenes:
        if scene.get("type") == "pexels":
            scene_id = scene["scene_id"]
            media = pexels_media.get(scene_id, {})
            image_path = media.get("image", {}).get("local_path")
            if image_path:
                scene["pexels_image_path"] = image_path
                scene["type"] = "manim"
            else:
                logger.warning(f"Scene {scene_id}: No Pexels image")

    stage_logger = StageLogger("Script Writing")
    stage_logger.start()

    script = generate_script(
        scenes, persona=persona, tone=tone,
        reference_docs=extract_documents_text(valid_docs) if valid_docs else None
    )
    stage_logger.complete(f"{len(script)} scripts generated")

    run_stage2_doctor(scenes_data, script, video_id, max_workers=3)
    scene_ids = [s["scene_id"] for s in scenes]
    tts_generate(script=script, video_id=video_id, scene_ids=scene_ids, max_workers=5)
    final_path = render_doctor_video(video_id, scenes_data, quality=quality)

    await db.update_video_state(video_id, state="complete", path=str(final_path))
    
    total_time = time.time() - pipeline_start
    return {
        "status": "complete",
        "video_id": video_id,
        "video_type": "doctor_ad",
        "drug_name": drug_name,
        "video_path": str(final_path),
        "elapsed_seconds": round(total_time, 1),
        "elapsed_formatted": f"{int(total_time//60)}m {int(total_time%60)}s"
    }

@app.post("/create-sm")
async def create_sm_video(
    drug_name: str = Form(...),
    indication: str = Form(...),
    key_benefit: str = Form(""),
    target_audience: str = Form("patients"),
    persona: str = Form("friendly health narrator"),
    tone: str = Form("engaging and conversational"),
    quality: str = Form("low"),
    user_id: Optional[str] = Form(None),
):
    """
    Generate social media short-form video (Instagram Reels, TikTok).
    Mix of Manim (animations) + Pexels (visual assets).
    Optimized for 15-60 second videos.
    """
    from app.social_media.stage1_sm_scenes import generate_sm_scenes
    from app.social_media.stage2_sm_manim import run_stage2_sm
    from app.social_media.stage3_sm_pexels_fetch import run_stage3_sm_pexels
    from app.social_media.stage5_sm_render import render_sm_video
    
    pipeline_start = time.time()
    video_id = generate_video_id()
    
    logger.info(
        f"Starting Social Media pipeline - Video ID: {video_id}",
        extra={"stage": "PIPELINE START"}
    )
    
    try:
        # DB tracking
        try:
            uid = await db.ensure_user(user_id)
            session_id = await db.create_session(
                uid, video_id, status="processing",
                metadata={
                    "drug_name": drug_name,
                    "indication": indication,
                    "video_type": "social_media"
                }
            )
            await db.create_video_record(video_id, session_id, path=None, state="processing")
        except Exception as e:
            logger.warning(f"DB record creation failed: {e}")
        
        # Stage 1: Scene planning
        stage_logger = StageLogger("Social Media Scene Planning")
        stage_logger.start()
        
        scenes_data = generate_sm_scenes(
            drug_name=drug_name,
            indication=indication,
            key_benefit=key_benefit,
            target_audience=target_audience,
        )
        
        scenes = scenes_data.get("scenes", [])
        stage_logger.complete(f"{len(scenes)} scenes planned")
        
        if not scenes:
            raise HTTPException(500, "No scenes generated")
        
        # Stage 3: Fetch Pexels media
        pexels_media = run_stage3_sm_pexels(scenes_data, video_id)

        # Inject Pexels media paths into scenes
        for scene in scenes:
            scene_id = scene.get("scene_id")
            if scene_id is None:
                continue
            media = pexels_media.get(scene_id, {})
            image_path = media.get("image", {}).get("local_path")
            if image_path:
                scene["pexels_image_path"] = image_path
                scene["type"] = "manim"
            else:
                logger.debug(f"Scene {scene_id}: No Pexels media attached")

        # Stage: Script
        stage_logger = StageLogger("Script Writing")
        stage_logger.start()
        
        script = generate_script(scenes, persona=persona, tone=tone)
        
        stage_logger.complete(f"{len(script)} scripts generated")
        
        # Stage 2: Manim code generation
        run_stage2_sm(scenes_data, script, video_id, max_workers=3)
        
        # Stage 4: TTS
        scene_ids = [s["scene_id"] for s in scenes]
        tts_generate(script=script, video_id=video_id, scene_ids=scene_ids, max_workers=5)
        
        # Stage 5: Render
        final_path = render_sm_video(video_id, scenes_data, quality=quality)
        
        # Update DB
        try:
            await db.update_video_state(video_id, state="complete", path=str(final_path))
        except Exception as e:
            logger.warning(f"DB update failed: {e}")
        
        total_time = time.time() - pipeline_start
        
        return {
            "status": "complete",
            "video_id": video_id,
            "video_type": "social_media",
            "drug_name": drug_name,
            "video_path": str(final_path),
            "elapsed_seconds": round(total_time, 1),
            "elapsed_formatted": f"{int(total_time//60)}m {int(total_time%60)}s",
            "platform_hint": "Instagram Reels, TikTok, YouTube Shorts"
        }
        
    except Exception as e:
        logger.error(f"Social Media pipeline failed: {e}", extra={"stage": "PIPELINE ERROR"})
        raise HTTPException(500, f"Social Media render failed: {e}")


@app.post("/create-sm-rm")
async def create_sm_remotion_video(
    topic: str = Form(...),
    brand_name: str = Form(""),
    persona: str = Form("friendly brand narrator"),
    tone: str = Form("engaging and conversational"),
    quality: str = Form("high"),
    logo: Optional[UploadFile] = File(None),
    image: Optional[UploadFile] = File(None),
    # Optional Sadtalker integration
    integrate_sadtalker: bool = Form(False),
    sadtalker_image: Optional[UploadFile] = File(None),
    sadtalker_url: str = Form("http://127.0.0.1:8001/video/generate"),
    user_id: Optional[str] = Form(None),
):
    """
    Generate social media short-form video using Remotion pipeline.
    Optimized for Instagram Reels, TikTok, YouTube Shorts.
    """
    pipeline_start = time.time()
    video_id = generate_video_id()

    # Filter files
    logos = [logo] if logo and logo.filename and logo.content_type else []
    images = [image] if image and image.filename and image.content_type else []
    
    logger.info(f"Starting Social Media Remotion pipeline - Video ID: {video_id}")

    # DB setup
    try:
        uid = await db.ensure_user(user_id)
        session_id = await db.create_session(
            uid, video_id, status="processing",
            metadata={"topic": topic, "video_type": "social_media_remotion"}
        )
        await db.create_video_record(video_id, session_id, path=None, state="processing")
    except Exception as e:
        logger.warning(f"DB record creation failed: {e}")

    # Save assets
    assets_dir = VIDEOS_DIR / video_id / "assets"
    logos_dir = assets_dir / "logos"
    images_dir = assets_dir / "images"

    logos_dir.mkdir(parents=True, exist_ok=True)
    images_dir.mkdir(parents=True, exist_ok=True)

    logo_paths = await save_files(logos, logos_dir)
    image_paths = await save_files(images, images_dir)

    logger.info(f"Saved {len(logo_paths)} logos and {len(image_paths)} images")

    try:
        # Stage 1: Generate scenes
        scenes_data = generate_scenes(
            topic=topic,
            video_type="product_ad",
            brand_name=brand_name or "Our Brand",
        )

        scenes = scenes_data.get("scenes", [])
        if not scenes:
            raise HTTPException(500, "No scenes generated")

        # Stage 2: Generate script
        script = generate_script(
            scenes,
            persona=persona,
            tone=tone,
        )

        # Stage 3: Remotion
        run_stage2(
            scenes_data,
            script,
            video_id,
            assets={"logos": logo_paths, "images": image_paths},
        )

        # Stage 4: Try animations
        try:
            generate_animations(video_id)
        except Exception as e:
            logger.warning(f"Animation skipped: {e}")

        # Stage 5: TTS
        scene_ids = [s["scene_id"] for s in scenes]
        tts_generate(script=script, video_id=video_id, scene_ids=scene_ids)

        # Stage 6: Render (landscape)
        landscape_path = render_remotion(video_id)

        current_final = landscape_path

        # ──────────────────────────────────────────────
        # Optional: SadTalker integration
        # ──────────────────────────────────────────────
        if integrate_sadtalker:
            logger.info(f"Integrating SadTalker at {sadtalker_url}")

            sadtalker_image_path = None
            if sadtalker_image and sadtalker_image.filename:
                ext = Path(sadtalker_image.filename).suffix
                s_name = f"sadtalker_{uuid.uuid4()}{ext}"
                s_path = images_dir / s_name
                with open(s_path, "wb") as buf:
                    shutil.copyfileobj(sadtalker_image.file, buf)
                sadtalker_image_path = str(s_path)

            audio_path = assets_dir / "audio_for_sadtalker.wav"
            try:
                subprocess.run([
                    "ffmpeg", "-y", "-i", str(landscape_path), "-vn",
                    "-acodec", "pcm_s16le", "-ar", "44100", "-ac", "2",
                    str(audio_path)
                ], check=True, capture_output=True)
            except subprocess.CalledProcessError as err:
                logger.error(f"Audio extraction failed: {err.stderr.decode(errors='ignore')}")
                raise HTTPException(500, "Failed to extract audio for SadTalker")

            try:
                sadtalker_video = _call_sadtalker_service(str(audio_path), sadtalker_image_path, sadtalker_url)
            except Exception as e:
                logger.exception("SadTalker failed")
                raise HTTPException(500, f"SadTalker integration failed: {str(e)}")

            merged_path = VIDEOS_DIR / video_id / "final_sadtalker_merged.mp4"
            try:
                _merge_videos_side_by_side(str(landscape_path), sadtalker_video, str(merged_path))
                current_final = merged_path
                logger.info(f"SadTalker merged video created: {merged_path}")
            except Exception as e:
                logger.exception("Side-by-side merge failed")
                # keep landscape as fallback
                current_final = landscape_path

        # ──────────────────────────────────────────────
        # FINAL STEP: Convert to 9:16 portrait (for Reels/Shorts/TikTok)
        # ──────────────────────────────────────────────
        portrait_path = VIDEOS_DIR / video_id / "final_sm_rm_portrait.mp4"

        try:
            final_output_path = convert_to_portrait_9_16(
                input_video=current_final,
                output_video=portrait_path,
                quality=quality,
                target_width=1080          # you can make this dynamic later
            )
            logger.info(f"Portrait 9:16 version ready: {final_output_path}")
        except Exception as e:
            logger.warning(f"Portrait conversion failed → falling back to original: {e}")
            final_output_path = current_final

        # Update DB
        try:
            await db.update_video_state(video_id, state="complete", path=str(final_output_path))
        except Exception as e:
            logger.warning(f"DB update failed: {e}")
        total_time = time.time() - pipeline_start

        return {
            "status": "complete",
            "video_id": video_id,
            "video_type": "social_media_remotion",
            "video_path": str(final_output_path),
            "is_portrait": final_output_path.name.endswith("_portrait.mp4"),
            "used_sadtalker": integrate_sadtalker and bool(final_output_path.name == "final_sadtalker_merged.mp4" or "portrait" not in final_output_path.name),
            "elapsed_seconds": round(total_time, 1),
            "elapsed_formatted": f"{int(total_time//60)}m {int(total_time%60)}s",
            "platform_hint": "Instagram Reels, TikTok, YouTube Shorts – 9:16 portrait optimized",
            "quality_used": quality,
        }
    except Exception as e:
        logger.error(f"Social Media Remotion pipeline failed: {e}", extra={"stage": "PIPELINE ERROR"})
        raise HTTPException(500, f"Social Media Remotion render failed: {e}")


@app.get("/video/{video_id}")
async def get_video(video_id: str, request: Request):
    """Stream final video with range request support."""
    for filename in ["final.mp4", "final_moa.mp4", "final_doctor.mp4", "final_sm.mp4"]:
        video_path = VIDEOS_DIR / video_id / filename
        if video_path.exists():
            return FileResponse(video_path, media_type="video/mp4")
    raise HTTPException(404, "Video not found")


@app.get("/generate-user-id")
def generate_user_id():
    """Generate a user ID for tracking multiple video generations."""
    return {
        "user_id": str(uuid.uuid4()),
        "message": "Pass this user_id to /create or /create-moa endpoints."
    }

@app.get("/")
def root():
    return {
        "service": "Pharma Video Generator",
        "endpoints": {
            "generate_user_id": {
                "method": "GET",
                "path": "/generate-user-id",
                "description": "Generate a new user ID for tracking multiple videos"
            }
        },
        "pipelines": {
            "pexels_remotion": {
                "endpoint": "/create",
                "description": "Product ads, brand videos, patient awareness",
                "uses": "Pexels stock media + Remotion"
            },
            "manim_moa": {
                "endpoint": "/create-moa",
                "description": "Mechanism of Action educational videos",
                "uses": "Manim animations + TTS"
            },
            "doctor_ad": {
                "endpoint": "/create-doctor",
                "description": "Doctor-facing HCP promotional videos",
                "uses": "Manim animations + Pexels + TTS"
            },
            "social_media_manim": {
                "endpoint": "/create-sm",
                "description": "Short-form social media videos (Instagram Reels, TikTok, YouTube Shorts) - Manim",
                "uses": "Manim animations + Pexels + TTS"
            },
            "social_media_remotion": {
                "endpoint": "/create-sm-rm",
                "description": "Short-form social media videos (Instagram Reels, TikTok, YouTube Shorts) - Remotion",
                "uses": "Remotion animations + Pexels + TTS"
            },
            "compliance": {
                "endpoint": "/create-compliance",
                "description": "Compliance videos with reference document adherence",
                "uses": "Remotion with strict validation"
            }
        }
    }