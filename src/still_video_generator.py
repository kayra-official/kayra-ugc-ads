"""Create precise, identity-safe camera moves from the supplied model photo."""
from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path


def _digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def generate_model_motion(reference_image, output_path, scene, cfg):
    """Render a 7-second Ken Burns camera move without synthesizing new pixels."""
    source, output = Path(reference_image).resolve(), Path(output_path)
    if not source.is_file():
        raise FileNotFoundError(f"Original model reference not found: {source}")

    fps = int(cfg["video"]["fps"])
    width, height = int(cfg["video"]["width"]), int(cfg["video"]["height"])
    duration = float(scene.get("duration_seconds", 7.0))
    frames = round(duration * fps)
    last = max(frames - 1, 1)
    eased = f"(on/{last})*(on/{last})*(3-2*(on/{last}))"
    breathing = f"0.008*sin(PI*on/{last})"
    number = int(scene["scene_number"])

    # Source portrait landmarks after 9:16 center crop: pendant around (.46,.83),
    # visible earring around (.22,.23). Ease smoothly between those landmarks.
    if number == 2:
        zoom = f"1.8*(1+{breathing})"
        x = f"(iw-iw/zoom)*(0.41*(1-{eased}))"
        y = f"(ih-ih/zoom)*(1-{eased})"
    elif number == 3:
        zoom = f"(1.8-0.8*{eased})*(1+{breathing})"
        # Keep the crop anchored near the pendant while widening to the full
        # portrait; letting the anchor travel upward made the face jump in early tests.
        x = "(iw-iw/zoom)*0.41"
        y = "ih-ih/zoom"
    else:
        raise ValueError(f"No still-photo motion path is defined for Scene {number}.")

    vf = (
        f"scale={width}:{height}:force_original_aspect_ratio=increase,"
        f"crop={width}:{height},"
        f"zoompan=z='{zoom}':x='{x}':y='{y}':d=1:s={width}x{height}:fps={fps},"
        "setsar=1"
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        ["ffmpeg", "-y", "-loop", "1", "-framerate", str(fps), "-i", str(source),
         "-vf", vf, "-frames:v", str(frames), "-an", "-c:v", "libx264",
         "-preset", cfg["video"]["preset"], "-crf", str(cfg["video"]["crf"]),
         "-pix_fmt", "yuv420p", "-r", str(fps), str(output)],
        check=True, capture_output=True, text=True,
    )
    metadata = output.with_suffix(".motion.json")
    metadata.write_text(json.dumps({
        "scene_number": number,
        "reference_image": str(source),
        "reference_sha256": _digest(source),
        "scene_name": scene.get("scene_name", ""),
        "prompt": scene.get("video_prompt", ""),
        "duration_seconds": duration,
        "motion_renderer": "ffmpeg_zoompan_still_v4",
    }, indent=2, ensure_ascii=False), encoding="utf-8")
    return output
