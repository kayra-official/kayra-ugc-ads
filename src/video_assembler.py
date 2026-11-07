from pathlib import Path
import subprocess

outro = Path("assets/branding/kayra_logo.mp4")


def _run(cmd):
    subprocess.run(cmd, check=True, capture_output=True, text=True)


def assemble_video(clips_dir, outro, output, cfg, music=cfg["audio"]["background_music"]):
    clips = Path(clips_dir)
    outro = Path(outro)
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)

    temp = Path(cfg["app"]["temp_dir"])
    temp.mkdir(parents=True, exist_ok=True)

    width = int(cfg["video"]["width"])
    height = int(cfg["video"]["height"])
    fps = int(cfg["video"]["fps"])
    scene_count = int(cfg["video"].get("scene_count", 6))
    preset = cfg["video"]["preset"]
    crf = str(cfg["video"]["crf"])

    normalized = []

    # Normalize scene clips and remove all original audio.
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
            "-an",
            "-c:v", "libx264",
            "-preset", preset,
            "-crf", crf,
            "-pix_fmt", "yuv420p",
            "-r", str(fps),
            str(dst)
        ])

        normalized.append(dst)

    # Normalize the Kayra outro as well.
    if not outro.exists():
        raise FileNotFoundError(f"Missing Kayra outro: {outro}")

    normalized_outro = temp / "norm_outro.mp4"

    _run([
        "ffmpeg", "-y", "-i", str(outro),
        "-vf",
        f"scale={width}:{height}:force_original_aspect_ratio=increase,"
        f"crop={width}:{height},fps={fps},setsar=1",
        "-an",
        "-c:v", "libx264",
        "-preset", preset,
        "-crf", crf,
        "-pix_fmt", "yuv420p",
        "-r", str(fps),
        str(normalized_outro)
    ])

    # Concatenate all normalized silent video clips.
    concat = temp / "concat.txt"
    concat.write_text(
        "".join(
            f"file '{p.resolve().as_posix()}'\n"
            for p in normalized + [normalized_outro]
        ),
        encoding="utf-8"
    )

    silent_video = temp / "silent_final.mp4"

    _run([
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0",
        "-i", str(concat),
        "-c:v", "libx264",
        "-preset", preset,
        "-crf", crf,
        "-pix_fmt", "yuv420p",
        "-r", str(fps),
        "-an",
        "-movflags", "+faststart",
        str(silent_video)
    ])

    # Add background music only. No voice or scene audio.
    if music:
        music = Path(music)
        if not music.exists():
            raise FileNotFoundError(f"Missing background music: {music}")

        _run([
            "ffmpeg", "-y",
            "-i", str(silent_video),
            "-stream_loop", "-1", "-i", str(music),
            "-map", "0:v:0",
            "-map", "1:a:0",
            "-c:v", "copy",
            "-c:a", "aac",
            "-b:a", "192k",
            "-af", "volume=0.20",
            "-t", str(_get_duration(silent_video)),
            "-shortest",
            "-movflags", "+faststart",
            str(output)
        ])
    else:
        # Export silent video if no music file is supplied.
        silent_video.replace(output)

    return output


def _get_duration(video):
    result = subprocess.run(
        [
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(video)
        ],
        check=True,
        capture_output=True,
        text=True
    )
    return float(result.stdout.strip())