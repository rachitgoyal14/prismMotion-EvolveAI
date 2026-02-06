"""
Pharma video generation pipeline with logging, timing,
and company asset upload support.
"""

from pathlib import Path
import time
import os
import json
import shutil
import uuid
from typing import Annotated

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

# Logging setup
from app.utils.logging_config import setup_logging, StageLogger
import logging

setup_logging(level=logging.INFO)
logger = logging.getLogger(__name__)

from app.utils.generate_uid import generate_video_id

# Remotion pipeline
from app.stages.stage1_scenes import generate_scenes
from app.stages.stage3_script import generate_script
from app.stages.stage2_remotion import run_stage2
from app.stages.stage2_5_animations import generate_animations
from app.stages.stage4_tts import tts_generate
from app.stages.stage5_render import render_remotion

# MoA / Manim pipeline
from app.stages.stage1_moa_scenes import generate_moa_scenes
from app.stages.stage2_moa_manim import run_stage2_moa
from app.stages.stage5_moa_render import render_moa_video

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


class CreateRequest(BaseModel):
    """Pexels + Remotion video config (sent as JSON string in form)."""
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
# File helpers
# ---------------------------------------------------------------------

ALLOWED_TYPES = {
    "image/png",
    "image/jpeg",
    "image/jpg",
    "image/webp",
}



async def save_files(files: list[UploadFile] | None, target_dir: Path):
    if not files:
        return []

    saved_paths = []

    for file in files:

        if not file.filename:
            continue

        if file.content_type not in ALLOWED_TYPES:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid file type: {file.content_type}",
            )

        ext = Path(file.filename).suffix
        safe_name = f"{uuid.uuid4()}{ext}"
        file_path = target_dir / safe_name

        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        saved_paths.append(str(file_path))

    return saved_paths




@app.post("/create")
async def create_video(
    video_type: str = Form("product_ad"),
    topic: str = Form(...),
    brand_name: str = Form(""),
    persona: str = Form("professional narrator"),
    tone: str = Form("clear and reassuring"),
    logo: UploadFile | None = File(default=None),
    image: UploadFile | None = File(default=None),
    user_id: str | None = Form(None),
    video_id: str | None = Form(None),
):

    

    body = CreateRequest(
        video_type=video_type,
        topic=topic,
        brand_name=brand_name,
        persona=persona,
        tone=tone,
    )

    logos = [logo] if logo else []
    images = [image] if image else []
    logger.info(f"Logos: {logos}")
    logger.info(f"Images: {images}")



    pipeline_start = time.time()
    # Use provided video_id or generate a new one
    if not video_id:
        video_id = generate_video_id()

    # Ensure user + session + video record in DB
    try:
        uid = await db.ensure_user(user_id)
        session_id = await db.create_session(uid, video_id, status="processing", metadata={"topic": topic, "video_type": video_type})
        await db.create_video_record(video_id, session_id, path=None, state="processing")
    except Exception as e:
        logger.warning(f"DB record creation failed: {e}")

    logger.info(
        f"Starting Remotion pipeline - Video ID: {video_id}",
        extra={"stage": "PIPELINE START"},
    )

    # ---------------- Save assets ----------------

    assets_dir = VIDEOS_DIR / video_id / "assets"
    logos_dir = assets_dir / "logos"
    images_dir = assets_dir / "images"

    logos_dir.mkdir(parents=True, exist_ok=True)
    images_dir.mkdir(parents=True, exist_ok=True)

    logo_paths = await save_files(logos, logos_dir)
    image_paths = await save_files(images, images_dir)

    logger.info(
        f"Saved {len(logo_paths)} logos and {len(image_paths)} images",
        extra={"stage": "ASSET UPLOAD"},
    )

    try:
        # Stage 1
        scenes_data = generate_scenes(
            topic=body.topic,
            video_type=body.video_type,
            brand_name=body.brand_name or "Our Brand",
        )

        scenes = scenes_data.get("scenes", [])
        if not scenes:
            raise HTTPException(500, "No scenes generated")

        # Script
        script = generate_script(
            scenes,
            persona=body.persona,
            tone=body.tone,
        )

        # Stage 2
        run_stage2(
            scenes_data,
            script,
            video_id,
            assets={
                "logos": logo_paths,
                "images": image_paths,
            },
        )

        try:
            generate_animations(video_id)
        except Exception as e:
            logger.warning(f"Animation skipped: {e}")

        scene_ids = [s["scene_id"] for s in scenes]

        tts_generate(
            script=script,
            video_id=video_id,
            scene_ids=scene_ids,
        )

        final_path = render_remotion(video_id)

        # Update DB record to complete
        try:
            await db.update_video_state(video_id, state="complete", path=str(final_path))
        except Exception as e:
            logger.warning(f"DB update failed: {e}")

        total_time = time.time() - pipeline_start

        return {
            "status": "complete",
            "video_id": video_id,
            "video_type": body.video_type,
            "video_path": str(final_path),
            "assets": {
                "logos": logo_paths,
                "images": image_paths,
            },
            "elapsed_seconds": round(total_time, 1),
        }

    except Exception as e:
        logger.error(
            f"Pipeline failed: {e}",
            extra={"stage": "PIPELINE ERROR"},
        )
        raise HTTPException(500, f"Pipeline failed: {e}")



@app.post("/create-moa")
async def create_moa_video(body: CreateMoARequest, user_id: str | None = None, video_id: str | None = None):
    pipeline_start = time.time()
    # Use provided video_id or generate a new one
    if not video_id:
        video_id = generate_video_id()

    logger.info(
        f"Starting MoA pipeline - Video ID: {video_id}",
        extra={"stage": "PIPELINE START"},
    )

    try:
        # create user/session/video tracking
        try:
            uid = await db.ensure_user(user_id)
            session_id = await db.create_session(uid, video_id, status="processing", metadata={"drug_name": body.drug_name, "condition": body.condition})
            await db.create_video_record(video_id, session_id, path=None, state="processing")
        except Exception as e:
            logger.warning(f"DB record creation failed: {e}")

        stage_logger = StageLogger("MoA Scene Planning")
        stage_logger.start()

        scenes_data = generate_moa_scenes(
            drug_name=body.drug_name,
            condition=body.condition,
            target_audience=body.target_audience,
        )

        scenes = scenes_data.get("scenes", [])
        stage_logger.complete(
            f"{len(scenes)} MoA scenes planned"
        )

        if not scenes:
            raise HTTPException(
                status_code=500,
                detail="No MoA scenes generated",
            )

        stage_logger = StageLogger("Script Writing")
        stage_logger.start()

        script = generate_script(
            scenes,
            persona=body.persona,
            tone=body.tone,
        )

        stage_logger.complete(
            f"{len(script)} scripts generated"
        )

        run_stage2_moa(
            scenes_data,
            script,
            video_id,
            max_workers=4,
        )

        scene_ids = [s["scene_id"] for s in scenes]

        tts_generate(
            script=script,
            video_id=video_id,
            scene_ids=scene_ids,
            max_workers=5,
        )

        final_path = render_moa_video(
            video_id,
            quality=body.quality,
        )

        try:
            await db.update_video_state(video_id, state="complete", path=str(final_path))
        except Exception as e:
            logger.warning(f"DB update failed: {e}")

        total_time = time.time() - pipeline_start

        return {
            "status": "complete",
            "video_id": video_id,
            "video_type": "mechanism_of_action",
            "video_path": str(final_path),
            "elapsed_seconds": round(total_time, 1),
        }

    except Exception as e:
        logger.error(
            f"MoA pipeline failed: {e}",
            extra={"stage": "PIPELINE ERROR"},
        )
        raise HTTPException(
            status_code=500,
            detail=f"MoA render failed: {e}",
        )



@app.get("/video/{video_id}")
async def get_video(video_id: str, request: Request):
    video_path = VIDEOS_DIR / video_id / "final.mp4"

    if not video_path.exists():
        video_path = VIDEOS_DIR / video_id / "final_moa.mp4"

    if not video_path.exists():
        raise HTTPException(404, "Video not found")

    return FileResponse(video_path, media_type="video/mp4")


@app.get("/generate-uuid")
def generate_uuid():
    """Generate UUIDs for a video session (user_id and video_id)."""
    user_id = str(uuid.uuid4())
    video_id = generate_video_id()
    return {
        "user_id": user_id,
        "video_id": video_id,
        "message": "Pass both user_id and video_id to /create or /create-moa endpoints"
    }


@app.get("/")
def root():
    return {
        "service": "Pharma Video Generator",
        "endpoints": {
            "generate_uuid": {
                "method": "GET",
                "path": "/generate-uuid",
                "description": "Generate a new UUID for tracking a video session"
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
            }
        }
    }