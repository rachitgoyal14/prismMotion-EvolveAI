from pathlib import Path
import os
import logging
import azure.cognitiveservices.speech as speechsdk

from app.paths import OUTPUTS_DIR

AUDIO_DIR = OUTPUTS_DIR / "audio"
logger = logging.getLogger(__name__)


def _synthesize_to_file(
    synthesizer: speechsdk.SpeechSynthesizer, text: str, scene_key: str
) -> bool:
    """
    Helper: Run synthesis once and return True on success, False on failure.
    Logs details but does not raise.
    """
    result = synthesizer.speak_text_async(text).get()
    if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
        return True

    details = ""
    if result.reason == speechsdk.ResultReason.Canceled:
        cancel = result.cancellation_details
        if cancel:
            details = f" | cancellation_reason={cancel.reason}"
            if cancel.error_details:
                details += f" | error_details={cancel.error_details}"

    logger.warning("TTS failed for %s%s", scene_key, details)
    return False


def tts_generate(script: list[dict], video_id: str, scene_ids: list[int | str]):
    """
    Generate WAV per scene using Azure Speech.

    Behavior on failure:
    - We now log errors and keep going instead of raising immediately.
    - Scenes whose TTS repeatedly fails will simply not get an audio file.
      Downstream, stage5 will treat `audio_src` as None for those scenes.
    """
    output_dir = AUDIO_DIR / video_id
    output_dir.mkdir(parents=True, exist_ok=True)

    # Build scene_id -> text map
    script_map: dict[str, str] = {}
    for s in script:
        sid = s.get("scene_id")
        key = f"scene_{sid}" if isinstance(sid, int) else sid
        script_map[key] = s.get("script", "")

    speech_key = os.getenv("AZURE_SPEECH_KEY")
    region = os.getenv("AZURE_SPEECH_REGION")
    if not speech_key or not region:
        raise RuntimeError("AZURE_SPEECH_KEY and AZURE_SPEECH_REGION must be set")

    speech_config = speechsdk.SpeechConfig(subscription=speech_key, region=region)
    speech_config.speech_synthesis_voice_name = "en-IN-NeerjaNeural"

    for scene_id in scene_ids:
        key = f"scene_{scene_id}" if isinstance(scene_id, int) else scene_id
        if key not in script_map:
            raise RuntimeError(f"No script for {scene_id}")

        text = script_map[key]
        audio_path = output_dir / f"{key}.wav"
        audio_config = speechsdk.audio.AudioOutputConfig(filename=str(audio_path))
        synthesizer = speechsdk.SpeechSynthesizer(
            speech_config=speech_config,
            audio_config=audio_config,
        )

        # Retry a few times on transient Azure issues (like timeouts),
        # but don't fail the whole request if one scene keeps failing.
        max_attempts = 3
        success = False
        for attempt in range(1, max_attempts + 1):
            if _synthesize_to_file(synthesizer, text, key):
                success = True
                break
            logger.warning(
                "Retrying TTS for %s (attempt %d/%d)", key, attempt, max_attempts
            )

        if not success:
            logger.error(
                "Giving up on TTS for %s after %d attempts; continuing without audio",
                key,
                max_attempts,
            )
            # Do not raise – leave this scene without an audio file.
            continue

    return output_dir
