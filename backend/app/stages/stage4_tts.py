# # from pathlib import Path
# # import os
# # import logging
# # import azure.cognitiveservices.speech as speechsdk

# # from app.paths import OUTPUTS_DIR

# # AUDIO_DIR = OUTPUTS_DIR / "audio"
# # logger = logging.getLogger(__name__)


# # def _synthesize_to_file(
# #     synthesizer: speechsdk.SpeechSynthesizer, text: str, scene_key: str
# # ) -> bool:
# #     """
# #     Helper: Run synthesis once and return True on success, False on failure.
# #     Logs details but does not raise.
# #     """
# #     result = synthesizer.speak_text_async(text).get()
# #     if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
# #         return True

# #     details = ""
# #     if result.reason == speechsdk.ResultReason.Canceled:
# #         cancel = result.cancellation_details
# #         if cancel:
# #             details = f" | cancellation_reason={cancel.reason}"
# #             if cancel.error_details:
# #                 details += f" | error_details={cancel.error_details}"

# #     logger.warning("TTS failed for %s%s", scene_key, details)
# #     return False


# # def tts_generate(script: list[dict], video_id: str, scene_ids: list[int | str]):
# #     """
# #     Generate WAV per scene using Azure Speech.

# #     Behavior on failure:
# #     - We now log errors and keep going instead of raising immediately.
# #     - Scenes whose TTS repeatedly fails will simply not get an audio file.
# #       Downstream, stage5 will treat `audio_src` as None for those scenes.
# #     """
# #     output_dir = AUDIO_DIR / video_id
# #     output_dir.mkdir(parents=True, exist_ok=True)

# #     # Build scene_id -> text map
# #     script_map: dict[str, str] = {}
# #     for s in script:
# #         sid = s.get("scene_id")
# #         key = f"scene_{sid}" if isinstance(sid, int) else sid
# #         script_map[key] = s.get("script", "")

# #     speech_key = os.getenv("AZURE_SPEECH_KEY")
# #     region = os.getenv("AZURE_SPEECH_REGION")
# #     if not speech_key or not region:
# #         raise RuntimeError("AZURE_SPEECH_KEY and AZURE_SPEECH_REGION must be set")

# #     speech_config = speechsdk.SpeechConfig(subscription=speech_key, region=region)
# #     speech_config.speech_synthesis_voice_name = "en-IN-NeerjaNeural"

# #     for scene_id in scene_ids:
# #         key = f"scene_{scene_id}" if isinstance(scene_id, int) else scene_id
# #         if key not in script_map:
# #             raise RuntimeError(f"No script for {scene_id}")

# #         text = script_map[key]
# #         audio_path = output_dir / f"{key}.wav"
# #         audio_config = speechsdk.audio.AudioOutputConfig(filename=str(audio_path))
# #         synthesizer = speechsdk.SpeechSynthesizer(
# #             speech_config=speech_config,
# #             audio_config=audio_config,
# #         )

# #         # Retry a few times on transient Azure issues (like timeouts),
# #         # but don't fail the whole request if one scene keeps failing.
# #         max_attempts = 3
# #         success = False
# #         for attempt in range(1, max_attempts + 1):
# #             if _synthesize_to_file(synthesizer, text, key):
# #                 success = True
# #                 break
# #             logger.warning(
# #                 "Retrying TTS for %s (attempt %d/%d)", key, attempt, max_attempts
# #             )

# #         if not success:
# #             logger.error(
# #                 "Giving up on TTS for %s after %d attempts; continuing without audio",
# #                 key,
# #                 max_attempts,
# #             )
# #             # Do not raise – leave this scene without an audio file.
# #             continue

# #     return output_dir

# """
# Stage 4: Text-to-Speech (TTS) generation.
# OPTIMIZED with parallel processing and detailed logging.
# """
# import os
# from pathlib import Path
# from concurrent.futures import ThreadPoolExecutor, as_completed
# from openai import AzureOpenAI
# from dotenv import load_dotenv
# from app.paths import OUTPUTS_DIR
# from app.utils.logging_config import StageLogger

# import logging
# logger = logging.getLogger(__name__)

# load_dotenv()

# AUDIO_DIR = OUTPUTS_DIR / "audio"

# # Initialize Azure OpenAI client for TTS
# api_version = os.getenv("AZURE_OPENAI_API_VERSION")
# endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
# subscription_key = os.getenv("AZURE_API_KEY")

# client = AzureOpenAI(
#     api_version=api_version,
#     azure_endpoint=endpoint,
#     api_key=subscription_key,
# )


# def generate_tts_for_scene(scene_id: int, text: str, output_dir: Path) -> tuple[int, Path]:
#     """Generate TTS audio for a single scene."""
#     output_file = output_dir / f"scene_{scene_id}.wav"
    
#     try:
#         logger.info(f"Scene {scene_id}: Generating audio ({len(text)} chars)...", extra={'progress': True})
        
#         response = client.audio.speech.create(
#             model="tts-1",
#             voice="alloy",
#             input=text,
#             response_format="wav"
#         )
        
#         response.stream_to_file(output_file)
#         logger.info(f"Scene {scene_id}: Audio saved ✓", extra={'progress': True})
#         return (scene_id, output_file)
        
#     except Exception as e:
#         logger.error(f"Scene {scene_id}: TTS failed - {e}", extra={'progress': True})
#         raise


# def tts_generate(script: list[dict], video_id: str, scene_ids: list[int], max_workers: int = 5) -> Path:
#     """Generate TTS audio for all scenes IN PARALLEL."""
#     stage_logger = StageLogger("TTS Generation")
#     stage_logger.start()
    
#     output_dir = AUDIO_DIR / video_id
#     output_dir.mkdir(parents=True, exist_ok=True)
    
#     script_map = {s["scene_id"]: s["script"] for s in script}
    
#     stage_logger.progress(f"Generating audio for {len(scene_ids)} scenes in parallel (workers={max_workers})...")
    
#     audio_files = []
#     failed_scenes = []
#     completed = 0
    
#     with ThreadPoolExecutor(max_workers=max_workers) as executor:
#         future_to_scene = {
#             executor.submit(generate_tts_for_scene, sid, script_map.get(sid, ""), output_dir): sid
#             for sid in scene_ids
#         }
        
#         for future in as_completed(future_to_scene):
#             scene_id = future_to_scene[future]
            
#             try:
#                 scene_id, audio_file = future.result()
#                 audio_files.append(audio_file)
#                 completed += 1
#                 stage_logger.progress(f"Scene {scene_id}: Complete ✓ ({completed}/{len(scene_ids)})")
#             except Exception as e:
#                 logger.error(f"Scene {scene_id}: Failed", extra={'progress': True})
#                 failed_scenes.append(scene_id)
#                 completed += 1
    
#     if failed_scenes:
#         stage_logger.complete(f"{len(audio_files)}/{len(scene_ids)} OK, {len(failed_scenes)} failed")
#     else:
#         stage_logger.complete(f"All {len(audio_files)} audio files generated")
    
#     return output_dir

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
