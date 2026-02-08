"""
Creator Mode WebSocket Implementation

Allows users to step through video generation pipeline stage-by-stage,
with ability to accept or regenerate each stage.

Architecture:
- One WebSocket connection per session
- In-memory state only (no persistence)
- Sequential stage execution with manual progression
- Reuses all existing pipeline functions

Stages:
1. scenes - Generate scene structure
2. script - Generate narration script
3. visuals - Generate animations/compositions
4. tts - Generate audio
5. render - Produce final video
"""

import json
import logging
import traceback
from typing import Dict, Any, Optional, List
from pathlib import Path
import asyncio
from fastapi import WebSocket, WebSocketDisconnect
from pydantic import BaseModel

from app.utils.generate_uid import generate_video_id
from app.utils.documents import extract_documents_text

# Import existing pipeline functions
from app.stages.stage1_scenes import generate_scenes
from app.stages.stage3_script import generate_script
from app.stages.stage2_remotion import run_stage2
from app.stages.stage2_5_animations import generate_animations
from app.stages.stage4_tts import tts_generate
from app.stages.stage5_render import render_remotion

from app.moa_stages.stage1_moa_scenes import generate_moa_scenes
from app.moa_stages.stage2_moa_manim import run_stage2_moa
from app.moa_stages.stage5_moa_render import render_moa_video

from app.doctor_ad_stages.stage1_doctor_scenes import generate_doctor_scenes
from app.doctor_ad_stages.stage2_doctor_manim import run_stage2_doctor
from app.doctor_ad_stages.stage3_pexels_fetch import run_stage3_pexels
from app.doctor_ad_stages.stage5_doctor_render import render_doctor_video

from app.social_media.stage1_sm_scenes import generate_sm_scenes
from app.social_media.stage2_sm_manim import run_stage2_sm
from app.social_media.stage3_sm_pexels_fetch import run_stage3_sm_pexels
from app.social_media.stage5_sm_render import render_sm_video

from app.paths import OUTPUTS_DIR

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------
# In-Memory Session State
# ---------------------------------------------------------------------

class CreatorSession:
    """
    Holds state for a single Creator Mode session.
    Lives only in memory, per WebSocket connection.
    """
    
    def __init__(self, video_id: str, video_type: str, payload: Dict[str, Any]):
        self.video_id = video_id
        self.video_type = video_type
        self.payload = payload
        
        # Pipeline state
        self.current_stage: Optional[str] = None
        self.stage_outputs: Dict[str, Any] = {}  # stage_name -> output
        self.stage_versions: Dict[str, int] = {}  # stage_name -> attempt count
        self.user_feedback: Optional[str] = None
        
        # Stage order based on video type
        self.stage_order = self._get_stage_order()
        self.stage_index = 0
        
        # Tracking
        self.is_active = True
        
    def _get_stage_order(self) -> List[str]:
        """Define stage progression based on video type."""
        if self.video_type in ["product_ad", "compliance_video"]:
            return ["scenes", "script", "visuals", "animations", "tts", "render"]
        elif self.video_type in ["moa", "doctor_ad", "social_media"]:
            # Manim-based pipelines
            return ["scenes", "script", "visuals", "tts", "render"]
        else:
            # Default fallback
            return ["scenes", "script", "visuals", "tts", "render"]
    
    def get_current_stage(self) -> Optional[str]:
        """Return current stage name or None if complete."""
        if self.stage_index >= len(self.stage_order):
            return None
        return self.stage_order[self.stage_index]
    
    def advance_stage(self):
        """Move to next stage."""
        self.stage_index += 1
        self.user_feedback = None
        self.current_stage = self.get_current_stage()
    
    def increment_version(self, stage: str):
        """Track regeneration attempts."""
        self.stage_versions[stage] = self.stage_versions.get(stage, 0) + 1


# ---------------------------------------------------------------------
# Stage Execution Logic
# ---------------------------------------------------------------------

async def execute_stage(session: CreatorSession, websocket: WebSocket) -> Dict[str, Any]:
    """
    Execute the current stage using existing pipeline functions.
    
    Returns stage output dict or raises exception on error.
    """
    stage = session.current_stage
    video_type = session.video_type
    payload = session.payload
    video_id = session.video_id
    
    logger.info(f"[Creator Mode] Executing stage: {stage} (video_type={video_type}, video_id={video_id})")
    
    try:
        if stage == "scenes":
            return await _execute_scenes_stage(session)
        
        elif stage == "script":
            return await _execute_script_stage(session)
        
        elif stage == "visuals":
            return await _execute_visuals_stage(session)
        
        elif stage == "animations":
            # Optional animations stage (Remotion only)
            if video_type in ["product_ad", "compliance_video"]:
                return await _execute_animations_stage(session)
            else:
                # Skip for Manim pipelines
                return {"status": "skipped", "message": "Animations not applicable for this video type"}
        
        elif stage == "tts":
            return await _execute_tts_stage(session)
        
        elif stage == "render":
            return await _execute_render_stage(session)
        
        else:
            raise ValueError(f"Unknown stage: {stage}")
    
    except Exception as e:
        logger.error(f"[Creator Mode] Stage {stage} failed: {e}")
        logger.error(traceback.format_exc())
        raise


async def _execute_scenes_stage(session: CreatorSession) -> Dict[str, Any]:
    """Stage 1: Generate scene structure."""
    video_type = session.video_type
    payload = session.payload
    
    # Run in thread pool to avoid blocking event loop
    loop = asyncio.get_event_loop()
    
    if video_type == "product_ad":
        scenes_data = await loop.run_in_executor(
            None,
            generate_scenes,
            payload.get("topic"),
            video_type,
            payload.get("brand_name", ""),
            payload.get("reference_docs", ""),
            payload.get("region"),
        )
    
    elif video_type == "compliance_video":
        scenes_data = await loop.run_in_executor(
            None,
            generate_scenes,
            payload.get("prompt"),
            video_type,
            payload.get("brand_name", ""),
            payload.get("reference_docs", ""),
            None,  # region
        )
    
    elif video_type == "moa":
        scenes_data = await loop.run_in_executor(
            None,
            generate_moa_scenes,
            payload.get("drug_name"),
            payload.get("condition"),
            payload.get("target_audience", "healthcare professionals"),
            payload.get("logo_path"),
            payload.get("image_paths"),
            payload.get("reference_docs"),
        )
    
    elif video_type == "doctor_ad":
        scenes_data = await loop.run_in_executor(
            None,
            generate_doctor_scenes,
            payload.get("drug_name"),
            payload.get("indication"),
            payload.get("moa_summary", ""),
            payload.get("clinical_data", ""),
            payload.get("logo_path"),
            payload.get("product_image_path"),
            payload.get("image_paths", []),
            payload.get("reference_docs"),
        )
    
    elif video_type == "social_media":
        scenes_data = await loop.run_in_executor(
            None,
            generate_sm_scenes,
            payload.get("drug_name"),
            payload.get("indication"),
            payload.get("key_benefit", ""),
            payload.get("target_audience", "patients"),
        )
    
    else:
        raise ValueError(f"Unsupported video_type: {video_type}")
    
    # Store scenes for next stage
    session.stage_outputs["scenes"] = scenes_data
    
    return {
        "scenes_data": scenes_data,
        "scene_count": len(scenes_data.get("scenes", [])),
    }


async def _execute_script_stage(session: CreatorSession) -> Dict[str, Any]:
    """Stage 2: Generate narration script."""
    scenes_data = session.stage_outputs.get("scenes")
    if not scenes_data:
        raise ValueError("Scenes not found in session state")
    
    scenes = scenes_data.get("scenes", [])
    payload = session.payload
    
    # Run in thread pool
    loop = asyncio.get_event_loop()
    script = await loop.run_in_executor(
        None,
        generate_script,
        scenes,
        payload.get("persona", "professional narrator"),
        payload.get("tone", "clear and engaging"),
        payload.get("reference_docs"),
    )
    
    # Store script for next stage
    session.stage_outputs["script"] = script
    
    return {
        "script": script,
        "script_count": len(script),
    }


async def _execute_visuals_stage(session: CreatorSession) -> Dict[str, Any]:
    """Stage 3: Generate animations/compositions."""
    scenes_data = session.stage_outputs.get("scenes")
    script = session.stage_outputs.get("script")
    
    if not scenes_data or not script:
        raise ValueError("Scenes or script not found in session state")
    
    video_type = session.video_type
    video_id = session.video_id
    payload = session.payload
    
    loop = asyncio.get_event_loop()
    
    if video_type == "product_ad":
        await loop.run_in_executor(
            None,
            run_stage2,
            scenes_data,
            script,
            video_id,
            payload.get("assets", {}),
            payload.get("region"),
        )
        return {"status": "complete", "message": "Remotion compositions generated"}
    
    elif video_type == "compliance_video":
        await loop.run_in_executor(
            None,
            run_stage2,
            scenes_data,
            script,
            video_id,
            payload.get("assets", {}),
            None,  # region
        )
        return {"status": "complete", "message": "Compliance compositions generated"}
    
    elif video_type == "moa":
        await loop.run_in_executor(
            None,
            run_stage2_moa,
            scenes_data,
            script,
            video_id,
            3,  # max_workers
        )
        return {"status": "complete", "message": "MoA Manim animations generated"}
    
    elif video_type == "doctor_ad":
        # First fetch Pexels media
        scene_info = await loop.run_in_executor(
            None,
            run_stage3_pexels,
            scenes_data,
            video_id,
            payload.get("logo_path"),
            payload.get("product_image_path"),
        )
        
        # Inject paths into scenes
        scenes = scenes_data.get("scenes", [])
        for scene in scenes:
            scene_id = scene["scene_id"]
            info = scene_info.get(scene_id, {})
            
            if scene.get("type") == "product":
                if info.get("product_image_path"):
                    scene["product_image_path"] = info["product_image_path"]
                scene["product_name"] = info.get("product_name", payload.get("drug_name", ""))
            
            elif scene.get("type") == "logo":
                if info.get("logo_path"):
                    scene["logo_path"] = info["logo_path"]
                scene["tagline"] = info.get("tagline", "")
        
        await loop.run_in_executor(
            None,
            run_stage2_doctor,
            scenes_data,
            script,
            video_id,
            3,  # max_workers
        )
        return {"status": "complete", "message": "Doctor ad Manim animations generated"}
    
    elif video_type == "social_media":
        # Fetch Pexels media first
        pexels_media = await loop.run_in_executor(
            None,
            run_stage3_sm_pexels,
            scenes_data,
            video_id,
        )
        
        # Inject Pexels media paths into scenes
        scenes = scenes_data.get("scenes", [])
        for scene in scenes:
            scene_id = scene.get("scene_id")
            if scene_id is None:
                continue
            media = pexels_media.get(scene_id, {})
            image_path = media.get("image", {}).get("local_path")
            if image_path:
                scene["pexels_image_path"] = image_path
                scene["type"] = "manim"
        
        await loop.run_in_executor(
            None,
            run_stage2_sm,
            scenes_data,
            script,
            video_id,
            3,  # max_workers
        )
        return {"status": "complete", "message": "Social media Manim animations generated"}
    
    else:
        raise ValueError(f"Unsupported video_type: {video_type}")


async def _execute_animations_stage(session: CreatorSession) -> Dict[str, Any]:
    """Stage 3.5: Generate additional animations (Remotion only)."""
    video_id = session.video_id
    
    loop = asyncio.get_event_loop()
    
    try:
        await loop.run_in_executor(
            None,
            generate_animations,
            video_id,
        )
        return {"status": "complete", "message": "Additional animations generated"}
    except Exception as e:
        logger.warning(f"[Creator Mode] Animations failed (non-critical): {e}")
        return {"status": "skipped", "message": f"Animations skipped: {e}"}


async def _execute_tts_stage(session: CreatorSession) -> Dict[str, Any]:
    """Stage 4: Generate text-to-speech audio."""
    script = session.stage_outputs.get("script")
    scenes_data = session.stage_outputs.get("scenes")
    
    if not script or not scenes_data:
        raise ValueError("Script or scenes not found in session state")
    
    video_id = session.video_id
    scenes = scenes_data.get("scenes", [])
    scene_ids = [s["scene_id"] for s in scenes]
    
    payload = session.payload
    region = payload.get("region")
    
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(
        None,
        tts_generate,
        script,
        video_id,
        scene_ids,
        5,  # max_workers
        region,
    )
    
    return {
        "status": "complete",
        "message": f"Generated {len(scene_ids)} audio files",
        "audio_count": len(scene_ids),
    }


async def _execute_render_stage(session: CreatorSession) -> Dict[str, Any]:
    """Stage 5: Render final video."""
    scenes_data = session.stage_outputs.get("scenes")
    if not scenes_data:
        raise ValueError("Scenes not found in session state")
    
    video_id = session.video_id
    video_type = session.video_type
    payload = session.payload
    
    loop = asyncio.get_event_loop()
    
    if video_type in ["product_ad", "compliance_video"]:
        final_path = await loop.run_in_executor(
            None,
            render_remotion,
            video_id,
        )
    
    elif video_type == "moa":
        final_path = await loop.run_in_executor(
            None,
            render_moa_video,
            video_id,
            scenes_data,
            payload.get("quality", "low"),
        )
    
    elif video_type == "doctor_ad":
        final_path = await loop.run_in_executor(
            None,
            render_doctor_video,
            video_id,
            scenes_data,
            payload.get("quality", "low"),
        )
    
    elif video_type == "social_media":
        final_path = await loop.run_in_executor(
            None,
            render_sm_video,
            video_id,
            scenes_data,
            payload.get("quality", "low"),
        )
    
    else:
        raise ValueError(f"Unsupported video_type: {video_type}")
    
    # Store final path
    session.stage_outputs["final_video"] = str(final_path)
    
    return {
        "status": "complete",
        "message": "Video rendered successfully",
        "video_path": str(final_path),
        "video_id": video_id,
    }


# ---------------------------------------------------------------------
# WebSocket Handler
# ---------------------------------------------------------------------

async def handle_creator_websocket(websocket: WebSocket):
    """
    Main WebSocket handler for Creator Mode.
    
    Protocol:
    - Client sends "start" to begin
    - Server executes one stage, pauses
    - Client sends "accept" or "regenerate"
    - Repeat until pipeline complete
    """
    await websocket.accept()
    logger.info("[Creator Mode] WebSocket connected")
    
    session: Optional[CreatorSession] = None
    
    try:
        while True:
            # Wait for client message
            message = await websocket.receive_text()
            data = json.loads(message)
            action = data.get("action")
            
            logger.info(f"[Creator Mode] Received action: {action}")
            
            # ─────────────────────────────────────────────
            # ACTION: start
            # ─────────────────────────────────────────────
            if action == "start":
                video_id = generate_video_id()
                video_type = data.get("video_type", "product_ad")
                payload = data.get("payload", {})
                
                # Initialize session
                session = CreatorSession(video_id, video_type, payload)
                session.current_stage = session.get_current_stage()
                
                logger.info(f"[Creator Mode] Started session: video_id={video_id}, type={video_type}")
                
                await websocket.send_json({
                    "status": "session_started",
                    "video_id": video_id,
                    "video_type": video_type,
                    "stage_order": session.stage_order,
                    "current_stage": session.current_stage,
                })
                
                # Immediately execute first stage
                await _execute_and_respond(session, websocket)
            
            # ─────────────────────────────────────────────
            # ACTION: accept
            # ─────────────────────────────────────────────
            elif action == "accept":
                if not session or not session.is_active:
                    await websocket.send_json({
                        "status": "error",
                        "error": "No active session"
                    })
                    continue
                
                logger.info(f"[Creator Mode] User accepted stage: {session.current_stage}")
                
                # Move to next stage
                session.advance_stage()
                
                if session.current_stage is None:
                    # Pipeline complete
                    final_video = session.stage_outputs.get("final_video")
                    await websocket.send_json({
                        "status": "pipeline_complete",
                        "video_id": session.video_id,
                        "video_path": final_video,
                        "message": "All stages complete! Video is ready."
                    })
                    session.is_active = False
                    continue
                
                # Execute next stage
                await _execute_and_respond(session, websocket)
            
            # ─────────────────────────────────────────────
            # ACTION: regenerate
            # ─────────────────────────────────────────────
            elif action == "regenerate":
                if not session or not session.is_active:
                    await websocket.send_json({
                        "status": "error",
                        "error": "No active session"
                    })
                    continue
                
                # Optional user feedback
                feedback = data.get("feedback")
                if feedback:
                    session.user_feedback = feedback
                    logger.info(f"[Creator Mode] Regenerating with feedback: {feedback}")
                else:
                    logger.info(f"[Creator Mode] Regenerating stage: {session.current_stage}")
                
                # Increment version counter
                session.increment_version(session.current_stage)
                
                # Re-execute current stage
                await _execute_and_respond(session, websocket)
            
            # ─────────────────────────────────────────────
            # ACTION: stop
            # ─────────────────────────────────────────────
            elif action == "stop":
                logger.info("[Creator Mode] User requested stop")
                if session:
                    session.is_active = False
                await websocket.send_json({
                    "status": "stopped",
                    "message": "Session terminated by user"
                })
                break
            
            else:
                await websocket.send_json({
                    "status": "error",
                    "error": f"Unknown action: {action}"
                })
    
    except WebSocketDisconnect:
        logger.info("[Creator Mode] WebSocket disconnected")
    
    except Exception as e:
        logger.error(f"[Creator Mode] Unexpected error: {e}")
        logger.error(traceback.format_exc())
        try:
            await websocket.send_json({
                "status": "error",
                "error": str(e)
            })
        except:
            pass
    
    finally:
        logger.info("[Creator Mode] Session ended")


async def _execute_and_respond(session: CreatorSession, websocket: WebSocket):
    """
    Execute current stage and send response to client.
    Handles errors gracefully.
    """
    stage = session.current_stage
    version = session.stage_versions.get(stage, 0) + 1
    session.stage_versions[stage] = version
    
    try:
        # Execute stage
        await websocket.send_json({
            "status": "stage_running",
            "stage": stage,
            "version": version,
            "message": f"Executing {stage}..."
        })
        
        result = await execute_stage(session, websocket)
        
        # Success response
        await websocket.send_json({
            "stage": stage,
            "version": version,
            "status": "completed",
            "data": result,
            "next_actions": ["accept", "regenerate"],
            "progress": {
                "current": session.stage_index + 1,
                "total": len(session.stage_order),
            }
        })
    
    except Exception as e:
        # Error response
        error_msg = str(e)
        logger.error(f"[Creator Mode] Stage {stage} error: {error_msg}")
        logger.error(traceback.format_exc())
        
        try:
            await websocket.send_json({
                "stage": stage,
                "version": version,
                "status": "error",
                "error": error_msg,
                "next_actions": ["regenerate", "stop"],
            })
        except Exception as send_error:
            logger.error(f"[Creator Mode] Failed to send error response: {send_error}")
