from pathlib import Path
import os
import azure.cognitiveservices.speech as speechsdk

from app.paths import OUTPUTS_DIR

AUDIO_DIR = OUTPUTS_DIR / "audio"


def tts_generate(script: list[dict], video_id: str, scene_ids: list[int | str]):
    """Generate WAV per scene using Azure Speech."""
    output_dir = AUDIO_DIR / video_id
    output_dir.mkdir(parents=True, exist_ok=True)
    script_map = {}
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
        result = synthesizer.speak_text_async(text).get()
        if result.reason != speechsdk.ResultReason.SynthesizingAudioCompleted:
            raise RuntimeError(f"TTS failed for {key}")
    return output_dir
