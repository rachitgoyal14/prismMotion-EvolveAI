import json
import subprocess
from pathlib import Path

from app.paths import OUTPUTS_DIR, REMOTION_DIR

VIDEOS_DIR = OUTPUTS_DIR / "videos"


def render_compliance_video(video_id: str) -> Path:
    """
    Render compliance video using Remotion and ComplianceVideo.tsx
    """

    scenes_path = OUTPUTS_DIR / "compliance_scenes_with_media.json"
    script_path = OUTPUTS_DIR / "script.json"

    if not scenes_path.exists():
        raise FileNotFoundError("Run compliance stage2 first")

    if not script_path.exists():
        raise FileNotFoundError("Run script generation first")

    scenes_data = json.loads(scenes_path.read_text(encoding="utf-8"))
    script_data = json.loads(script_path.read_text(encoding="utf-8"))

    script_map = {s["scene_id"]: s["script"] for s in script_data}

    for s in scenes_data["scenes"]:
        s["script"] = script_map.get(s["scene_id"], "")

    out_dir = VIDEOS_DIR / video_id
    out_dir.mkdir(parents=True, exist_ok=True)

    props_path = out_dir / "props.json"
    props_path.write_text(
        json.dumps({"scenes": scenes_data["scenes"]}, ensure_ascii=False),
        encoding="utf-8",
    )

    final_path = out_dir / "final.mp4"

    subprocess.run(
        [
            "npx",
            "remotion",
            "render",
            "src/index.ts",
            "ComplianceVideo",
            str(final_path),
            f"--props={props_path}",
            "--codec=h264",
            "--audio-codec=aac",
        ],
        cwd=REMOTION_DIR,
        check=True,
    )

    return final_path
