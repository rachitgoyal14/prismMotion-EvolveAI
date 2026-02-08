import os
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Optional
import azure.cognitiveservices.speech as speechsdk
from dotenv import load_dotenv

from app.paths import OUTPUTS_DIR
from app.utils.logging_config import StageLogger

import logging
logger = logging.getLogger(__name__)

load_dotenv()

AUDIO_DIR = OUTPUTS_DIR / "audio"

# Region-based voice mapping for Azure Neural TTS
# All voices speak English, but with regionally appropriate accents
REGION_VOICE_MAP = {
    "india": "en-IN-NeerjaNeural",           # Indian English (Female)
    "africa": "en-ZA-LeahNeural",            # South African English (Female)
    "europe": "en-GB-SoniaNeural",           # British English (Female)
    "east_asia": "en-SG-LunaNeural",         # Singaporean English (Female)
    "middle_east": "en-AE-FatimaNeural",     # UAE English (Female)
    "latin_america": "en-US-JennyNeural",    # US English (Female) - neutral for LatAm
    "north_america": "en-US-JennyNeural",    # US English (Female)
    "southeast_asia": "en-PH-RosaNeural",    # Philippine English (Female)
    "global": "en-US-JennyNeural",           # US English (Female) - neutral/global
}


def get_voice_for_region(region: Optional[str]) -> str:
    """
    Get the appropriate Azure Neural TTS voice based on region.
    All voices speak English with regionally appropriate accents.
    
    Args:
        region: Region code (e.g., "india", "africa", "europe")
    
    Returns:
        Azure Neural TTS voice name
    """
    if not region:
        return "en-US-JennyNeural"  # Default: US English
    
    region_key = region.lower().strip()
    voice = REGION_VOICE_MAP.get(region_key, "en-US-JennyNeural")
    
    logger.info(f"Selected voice '{voice}' for region '{region}'")
    return voice


def generate_tts_for_scene(
    scene_id: int, 
    text: str, 
    output_dir: Path,
    region: Optional[str] = None
) -> tuple[int, Path]:
    """
    Generate TTS audio for a single scene using Azure Speech.
    Thread-safe because we create fresh configs per call.
    
    Args:
        scene_id: Scene identifier
        text: Script text to synthesize
        output_dir: Directory to save audio file
        region: Optional region code for voice selection
    """

    if not text.strip():
        raise ValueError(f"Scene {scene_id} has empty script")

    speech_key = os.getenv("AZURE_SPEECH_KEY")
    azure_region = os.getenv("AZURE_SPEECH_REGION")

    if not speech_key or not azure_region:
        raise RuntimeError("AZURE_SPEECH_KEY and AZURE_SPEECH_REGION must be set")

    output_file = output_dir / f"scene_{scene_id}.wav"

    try:
        logger.info(f"Scene {scene_id}: Generating audio ({len(text)} chars)...",
                    extra={'progress': True})

        speech_config = speechsdk.SpeechConfig(
            subscription=speech_key,
            region=azure_region
        )

        # Select voice based on region (English with appropriate accent)
        voice_name = get_voice_for_region(region)
        speech_config.speech_synthesis_voice_name = voice_name
        
        logger.info(f"Scene {scene_id}: Using voice '{voice_name}'")

        audio_config = speechsdk.audio.AudioOutputConfig(
            filename=str(output_file)
        )

        synthesizer = speechsdk.SpeechSynthesizer(
            speech_config=speech_config,
            audio_config=audio_config
        )

        result = synthesizer.speak_text_async(text).get()

        if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
            logger.info(f"Scene {scene_id}: Audio saved ✓",
                        extra={'progress': True})
            return (scene_id, output_file)

        # Handle cancellation
        if result.reason == speechsdk.ResultReason.Canceled:
            details = result.cancellation_details

            error_msg = f"Scene {scene_id} canceled: {details.reason}"

            if details.error_details:
                error_msg += f" | {details.error_details}"

            raise RuntimeError(error_msg)

        raise RuntimeError(f"Scene {scene_id}: Unknown TTS failure")

    except Exception as e:
        logger.error(f"Scene {scene_id}: TTS failed - {e}",
                     extra={'progress': True})
        raise


def tts_generate(
    script: list[dict],
    video_id: str,
    scene_ids: list[int],
    max_workers: int = 4,
    region: Optional[str] = None,
) -> Path:
    """
    Parallel Azure Speech TTS generation with region-based voice selection.

    Args:
        script: List of scene scripts
        video_id: Video identifier
        scene_ids: List of scene IDs to generate audio for
        max_workers: Number of parallel workers (default: 4)
        region: Optional region code for voice selection (e.g., "india", "africa")

    Why max_workers=4?
    Azure Speech scales well, but beyond 4 you hit diminishing returns.
    """

    stage_logger = StageLogger("TTS Generation")
    stage_logger.start()

    output_dir = AUDIO_DIR / video_id
    output_dir.mkdir(parents=True, exist_ok=True)

    script_map = {s["scene_id"]: s["script"] for s in script}
    
    # Log voice selection
    voice_name = get_voice_for_region(region)
    stage_logger.progress(
        f"Using voice '{voice_name}' for region '{region or 'default'}'"
    )

    stage_logger.progress(
        f"Generating audio for {len(scene_ids)} scenes in parallel (workers={max_workers})..."
    )

    audio_files = []
    failed_scenes = []
    completed = 0

    with ThreadPoolExecutor(max_workers=max_workers) as executor:

        future_to_scene = {
            executor.submit(
                generate_tts_for_scene,
                sid,
                script_map.get(sid, ""),
                output_dir,
                region  # Pass region to each scene
            ): sid
            for sid in scene_ids
        }

        for future in as_completed(future_to_scene):
            scene_id = future_to_scene[future]

            try:
                _, audio_file = future.result()
                audio_files.append(audio_file)

            except Exception:
                failed_scenes.append(scene_id)

            completed += 1
            stage_logger.progress(
                f"Scene {scene_id}: Complete ({completed}/{len(scene_ids)})"
            )

    if failed_scenes:
        stage_logger.complete(
            f"{len(audio_files)}/{len(scene_ids)} OK, {len(failed_scenes)} failed"
        )
    else:
        stage_logger.complete("All audio files generated")

    return output_dir
