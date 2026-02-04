"""
Pharma video generation pipeline with TWO modes:
1. Pexels + Remotion: Product ads, brand videos, patient awareness
2. Manim: Mechanism of Action (MoA) educational videos
"""
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os

from app.utils.generate_uid import generate_video_id

# Remotion pipeline
from app.stages.stage1_scenes import generate_scenes
from app.stages.stage3_script import generate_script
from app.stages.stage2_remotion import run_stage2
from app.stages.stage4_tts import tts_generate
from app.stages.stage5_render import render_remotion

# MoA/Manim pipeline
from app.stages.stage1_moa_scenes import generate_moa_scenes
from app.stages.stage2_moa_manim import run_stage2_moa
from app.stages.stage5_moa_render import render_moa_video

from app.paths import OUTPUTS_DIR, REMOTION_DIR

app = FastAPI(title="Pharma Video Generator")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

VIDEOS_DIR = OUTPUTS_DIR / "videos"


class CreateRequest(BaseModel):
    """Pexels + Remotion video (product ads, patient awareness)"""
    video_type: str = "product_ad"  # brand_ad | patient_awareness | product_ad
    topic: str
    brand_name: str = ""
    persona: str = "professional narrator"
    tone: str = "clear and reassuring"


class CreateMoARequest(BaseModel):
    """Mechanism of Action video using Manim"""
    drug_name: str
    condition: str
    target_audience: str = "healthcare professionals"  # patients | healthcare professionals | medical students
    persona: str = "professional medical narrator"
    tone: str = "clear and educational"
    quality: str = "high"  # low | medium | high | production


#### REMOTION
@app.post("/create")
def create_video(body: CreateRequest):
    """
    Run Pexels + Remotion pipeline: plan scenes → script → Pexels + Remotion TSX → TTS → render.
    For: product ads, brand videos, patient awareness videos
    """
    video_id = generate_video_id()

    # Stage 1: Scene planning
    scenes_data = generate_scenes(
        topic=body.topic,
        video_type=body.video_type,
        brand_name=body.brand_name or "Our Brand",
    )
    scenes = scenes_data.get("scenes", [])

    if not scenes:
        raise HTTPException(status_code=500, detail="No scenes generated")

    # Stage 3: Script
    script = generate_script(
        scenes,
        persona=body.persona,
        tone=body.tone,
    )

    # Stage 2: Pexels + Remotion
    run_stage2(scenes_data, script, video_id)

    # Stage 4: TTS
    scene_ids = [s["scene_id"] for s in scenes]
    tts_generate(script=script, video_id=video_id, scene_ids=scene_ids)

    # Stage 5: Remotion render
    try:
        final_path = render_remotion(video_id)
    except FileNotFoundError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Render failed: {e}")

    return {
        "status": "complete",
        "video_id": video_id,
        "video_type": body.video_type,
        "video_path": str(final_path),
    }


#### MANIM
@app.post("/create-moa")
def create_moa_video(body: CreateMoARequest):
    """
    Generate a Mechanism of Action video using Manim.
    For: educational medical content explaining how drugs work
    
    Pipeline:
    1. Plan MoA scenes (LLM)
    2. Generate Manim animation code (LLM)
    3. Generate narration script (LLM, reused)
    4. Generate TTS audio (reused)
    5. Render Manim + combine with audio
    """
    video_id = generate_video_id()
    
    # Stage 1: MoA Scene planning
    scenes_data = generate_moa_scenes(
        drug_name=body.drug_name,
        condition=body.condition,
        target_audience=body.target_audience,
    )
    scenes = scenes_data.get("scenes", [])
    
    if not scenes:
        raise HTTPException(status_code=500, detail="No MoA scenes generated")
    
    # Stage 3: Script (reuse existing)
    script = generate_script(
        scenes,
        persona=body.persona,
        tone=body.tone,
    )
    
    # Stage 2: Generate Manim code
    try:
        manim_scenes_dir = run_stage2_moa(scenes_data, script, video_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Manim code generation failed: {e}")
    
    # Stage 4: TTS (reuse existing)
    scene_ids = [s["scene_id"] for s in scenes]
    tts_generate(script=script, video_id=video_id, scene_ids=scene_ids)
    
    # Stage 5: Render Manim + combine with audio
    try:
        final_path = render_moa_video(video_id, quality=body.quality)
    except FileNotFoundError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"MoA render failed: {e}")
    
    return {
        "status": "complete",
        "video_id": video_id,
        "video_type": "mechanism_of_action",
        "drug_name": body.drug_name,
        "condition": body.condition,
        "video_path": str(final_path),
    }


@app.get("/video/{video_id}")
async def get_video(video_id: str, request: Request):
    """
    Stream final video with range request support.
    Works for both Pexels/Remotion videos and MoA/Manim videos.
    """
    # Try regular video first
    video_path = VIDEOS_DIR / video_id / "final.mp4"
    
    # If not found, try MoA video
    if not video_path.exists():
        video_path = VIDEOS_DIR / video_id / "final_moa.mp4"
    
    if not video_path.exists():
        raise HTTPException(status_code=404, detail="Video not found")

    file_size = os.path.getsize(video_path)
    range_header = request.headers.get("range")

    if range_header:
        byte_range = range_header.replace("bytes=", "").split("-")
        start = int(byte_range[0])
        end = int(byte_range[1]) if byte_range[1] else file_size - 1
        end = min(end, file_size - 1)
        chunk_size = end - start + 1

        def iterfile():
            with open(video_path, "rb") as f:
                f.seek(start)
                remaining = chunk_size
                while remaining:
                    read_size = min(65536, remaining)
                    data = f.read(read_size)
                    if not data:
                        break
                    remaining -= len(data)
                    yield data

        return StreamingResponse(
            iterfile(),
            status_code=206,
            headers={
                "Content-Range": f"bytes {start}-{end}/{file_size}",
                "Accept-Ranges": "bytes",
                "Content-Length": str(chunk_size),
                "Content-Type": "video/mp4",
                "Cache-Control": "public, max-age=3600",
            },
            media_type="video/mp4",
        )

    return FileResponse(
        video_path,
        media_type="video/mp4",
        headers={
            "Accept-Ranges": "bytes",
            "Content-Length": str(file_size),
            "Cache-Control": "public, max-age=3600",
        },
    )


@app.get("/")
def root():
    return {
        "service": "Pharma Video Generator",
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