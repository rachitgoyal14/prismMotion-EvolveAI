import os
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
import azure.cognitiveservices.speech as speechsdk
from dotenv import load_dotenv

from app.paths import OUTPUTS_DIR
from app.utils.logging_config import StageLogger

import logging
logger = logging.getLogger(__name__)

load_dotenv()

AUDIO_DIR = OUTPUTS_DIR / "audio"


def generate_tts_for_scene(scene_id: int, text: str, output_dir: Path) -> tuple[int, Path]:
    """
    Generate TTS audio for a single scene using Azure Speech.
    Thread-safe because we create fresh configs per call.
    """

    if not text.strip():
        raise ValueError(f"Scene {scene_id} has empty script")

    speech_key = os.getenv("AZURE_SPEECH_KEY")
    region = os.getenv("AZURE_SPEECH_REGION")

    if not speech_key or not region:
        raise RuntimeError("AZURE_SPEECH_KEY and AZURE_SPEECH_REGION must be set")

    output_file = output_dir / f"scene_{scene_id}.wav"

    try:
        logger.info(f"Scene {scene_id}: Generating audio ({len(text)} chars)...",
                    extra={'progress': True})

        speech_config = speechsdk.SpeechConfig(
            subscription=speech_key,
            region=region
        )

        # ⭐ HIGHLY recommended voice for professional narration
        speech_config.speech_synthesis_voice_name = "en-US-JennyNeural"

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
    max_workers: int = 4,  # ⭐ safer default than 5
) -> Path:

    """
    Parallel Azure Speech TTS generation.

    Why max_workers=4?
    Azure Speech scales well, but beyond 4 you hit diminishing returns.
    """

    stage_logger = StageLogger("TTS Generation")
    stage_logger.start()

    output_dir = AUDIO_DIR / video_id
    output_dir.mkdir(parents=True, exist_ok=True)

    script_map = {s["scene_id"]: s["script"] for s in script}

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
                output_dir
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
