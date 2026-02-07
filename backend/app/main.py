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
from typing import Annotated, Optional
import mimetypes
import logging

from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv())

from fastapi import (
    FastAPI,
    HTTPException,
    Request,
    UploadFile,
    File,
    Form,
    Depends
)
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import io

# Logging setup
from app.utils.logging_config import setup_logging, StageLogger

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
    quality: str = "high"

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
    quality: str = "high"

# ---------------------------------------------------------------------
# File helpers - FIXED
# ---------------------------------------------------------------------

ALLOWED_TYPES = {
    "image/png",
    "image/jpeg", 
    "image/jpg",
    "image/webp",
}

def filter_valid_files(files: list[UploadFile]) -> list[UploadFile]:
    """Filter out invalid files (no filename or no content_type)"""
    return [
        f for f in files 
        if f.filename and f.content_type and f.content_type in ALLOWED_TYPES
    ]

async def save_files(files: list[UploadFile] | None, target_dir: Path):
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

@app.post("/create")
async def create_video(
    video_type: str = Form("product_ad"),
    topic: str = Form(...),
    brand_name: str = Form(""),
    persona: str = Form("professional narrator"),
    tone: str = Form("clear and reassuring"),
    logo: Optional[UploadFile] = File(None),
    image: Optional[UploadFile] = File(None),
    documents: list[UploadFile] = File(default=[]),
    user_id: Optional[str] = Form(None),
):
    pipeline_start = time.time()
    video_id = generate_video_id()

    # ✅ FILTER FILES FIRST - BULLETPROOF
    logos = [logo] if logo and logo.filename and logo.content_type else []
    images = [image] if image and image.filename and logo.content_type else []
    valid_docs = [doc for doc in documents if doc.filename and doc.content_type]
    
    logger.info(f"Valid logos: {len(logos)}, images: {len(images)}, docs: {len(valid_docs)}")

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
        # Stage 1 - USE valid_docs
        scenes_data = generate_scenes(
            topic=topic,
            video_type=video_type,
            brand_name=brand_name or "Our Brand",
            reference_docs=extract_documents_text(valid_docs) if valid_docs else "",
        )

        scenes = scenes_data.get("scenes", [])
        if not scenes:
            raise HTTPException(500, "No scenes generated")

        # Script - USE valid_docs
        script = generate_script(
            scenes,
            persona=persona,
            tone=tone,
            reference_docs=extract_documents_text(valid_docs) if valid_docs else None,
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
    documents: list[UploadFile] = File(default=[]),
    logo: Optional[UploadFile] = File(None),
    images: list[UploadFile] = File(default=[]),
):
    # ✅ FILTER FILES FIRST
    valid_docs = filter_valid_files(documents)
    valid_logo = logo if logo and logo.filename and logo.content_type else None
    valid_images = filter_valid_files(images)
    
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
    quality: str = Form("high"),
    user_id: Optional[str] = Form(None),
    documents: list[UploadFile] = File(default=[]),
    logo: Optional[UploadFile] = File(None),
    images: list[UploadFile] = File(default=[]),
):
    pipeline_start = time.time()
    video_id = generate_video_id()

    # ✅ FILTER FILES FIRST
    valid_docs = filter_valid_files(documents)
    valid_logo = logo if logo and logo.filename and logo.content_type else None
    valid_images = filter_valid_files(images)

    logger.info(f"MoA: {len(valid_docs)} docs, logo: {valid_logo is not None}, {len(valid_images)} images")

    try:
        uid = await db.ensure_user(user_id)
        session_id = await db.create_session(
            uid, video_id, status="processing", 
            metadata={"drug_name": drug_name, "condition": condition}
        )
        await db.create_video_record(video_id, session_id, path=None, state="processing")
    except Exception as e:
        logger.warning(f"DB record creation failed: {e}")

        stage_logger = StageLogger("MoA Scene Planning")
        stage_logger.start()

        scenes_data = generate_moa_scenes(
            drug_name=drug_name,
            condition=condition,
            target_audience=target_audience,
            reference_docs=extract_documents_text(valid_docs) if valid_docs else None,
            logo_path=valid_logo.filename if valid_logo else None,
            image_paths=[img.filename for img in valid_images],
        )

        scenes = scenes_data.get("scenes", [])
        stage_logger.complete(f"{len(scenes)} MoA scenes planned")

        if not scenes:
            raise HTTPException(500, "No MoA scenes generated")

        stage_logger = StageLogger("Script Writing")
        stage_logger.start()

        script = generate_script(scenes, persona=persona, tone=tone)
        stage_logger.complete(f"{len(script)} scripts generated")

        run_stage2_moa(scenes_data, script, video_id, max_workers=4)
        scene_ids = [s["scene_id"] for s in scenes]
        tts_generate(script=script, video_id=video_id, scene_ids=scene_ids, max_workers=5)
        final_path = render_moa_video(video_id, quality=quality)

        await db.update_video_state(video_id, state="complete", path=str(final_path))
        
        total_time = time.time() - pipeline_start
        return {
            "status": "complete",
            "video_id": video_id,
            "video_type": "mechanism_of_action",
            "video_path": str(final_path),
            "elapsed_seconds": round(total_time, 1),
        }

    except Exception as e:
        logger.error(f"MoA pipeline failed: {e}")
        raise HTTPException(500, f"MoA render failed: {e}")

@app.post("/create-doctor")
async def create_doctor_video(
    drug_name: str = Form(...),
    indication: str = Form(...),
    moa_summary: str = Form(""),
    clinical_data: str = Form(""),
    pexels_query: str = Form("doctor consultation"),
    persona: str = Form("professional medical narrator"),
    tone: str = Form("scientific and professional"),
    quality: str = Form("high"),
    user_id: Optional[str] = Form(None),
    video_id: Optional[str] = Form(None),
    documents: list[UploadFile] = File(default=[]),
    logo: Optional[UploadFile] = File(None),
    images: list[UploadFile] = File(default=[]),
):
    from app.doctor_ad_stages.stage1_doctor_scenes import generate_doctor_scenes
    from app.doctor_ad_stages.stage2_doctor_manim import run_stage2_doctor
    from app.doctor_ad_stages.stage3_pexels_fetch import run_stage3_pexels
    from app.doctor_ad_stages.stage5_doctor_render import render_doctor_video

    pipeline_start = time.time()
    if not video_id:
        video_id = generate_video_id()

    # ✅ FILTER FILES FIRST
    valid_docs = filter_valid_files(documents)
    valid_logo = logo if logo and logo.filename and logo.content_type else None
    valid_images = filter_valid_files(images)

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

@app.get("/video/{video_id}")
async def get_video(video_id: str, request: Request):
    """Stream final video with range request support."""
    for filename in ["final.mp4", "final_moa.mp4", "final_doctor.mp4"]:
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
                "description": "HCP promotional videos with clinical data",
                "uses": "Manim + Pexels hybrid"
            },
            "compliance": {
                "endpoint": "/create-compliance",
                "description": "Compliance videos with reference document adherence",
                "uses": "Remotion with strict validation"
            }
        }
    }
