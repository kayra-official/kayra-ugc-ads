from pathlib import Path
import subprocess


def _run(cmd):
    subprocess.run(cmd, check=True, capture_output=True, text=True)


def assemble_video(clips_dir, outro, output, cfg):
    """Concatenate all numbered scene clips and logo outro. Output is silent."""
    clips = Path(clips_dir)
    outro = Path(outro)
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)

    temp = Path(cfg["app"]["temp_dir"])
    temp.mkdir(parents=True, exist_ok=True)

    width = int(cfg["video"]["width"])
    height = int(cfg["video"]["height"])
    fps = int(cfg["video"]["fps"])
    scene_count = int(cfg["video"].get("scene_count", 9))
    preset = cfg["video"]["preset"]
    crf = str(cfg["video"]["crf"])

    normalized = []
    for i in range(1, scene_count + 1):
        src = clips / f"scene_{i:02d}.mp4"
        if not src.exists():
            raise FileNotFoundError(f"Missing scene clip: {src}")
        dst = temp / f"norm_{i:02d}.mp4"
        _run([
            "ffmpeg", "-y", "-i", str(src),
            "-vf",
            f"scale={width}:{height}:force_original_aspect_ratio=increase,"
            f"crop={width}:{height},fps={fps},setsar=1",
            "-an", "-c:v", "libx264", "-preset", preset,
            "-crf", crf, "-pix_fmt", "yuv420p", "-r", str(fps),
            str(dst)
        ])
        normalized.append(dst)

    if not outro.is_file():
        raise FileNotFoundError(f"Missing Kayra outro: {outro}")
    normalized_outro = temp / "norm_outro.mp4"
    _run([
        "ffmpeg", "-y", "-i", str(outro),
        "-vf",
        f"scale={width}:{height}:force_original_aspect_ratio=increase,"
        f"crop={width}:{height},fps={fps},setsar=1",
        "-an", "-c:v", "libx264", "-preset", preset,
        "-crf", crf, "-pix_fmt", "yuv420p", "-r", str(fps),
        str(normalized_outro)
    ])

    concat = temp / "concat.txt"
    concat.write_text(
        "".join(f"file '{p.resolve().as_posix()}'\n"
                for p in normalized + [normalized_outro]),
        encoding="utf-8"
    )
    silent_video = temp / "silent_final.mp4"
    _run([
        "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(concat),
        "-c:v", "libx264", "-preset", preset, "-crf", crf,
        "-pix_fmt", "yuv420p", "-r", str(fps), "-an",
        "-movflags", "+faststart", str(silent_video)
    ])

    # Always return a silent assembled video. music_manager.py adds music later.
    if output.exists():
        output.unlink()
    silent_video.replace(output)
    return output
