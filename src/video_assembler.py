from pathlib import Path
import subprocess

def _run(cmd):
    subprocess.run(cmd, check=True, capture_output=True, text=True)

def assemble_video(clips_dir, outro, output, cfg):
    clips = Path(clips_dir)
    temp = Path(cfg["app"]["temp_dir"]); temp.mkdir(parents=True, exist_ok=True)
    scene_count = int(cfg["video"].get("scene_count", 6))
    normalized = []
    for i in range(1, scene_count + 1):
        src = clips / f"scene_{i:02d}.mp4"
        if not src.exists():
            raise FileNotFoundError(f"Missing scene clip: {src}")
        dst = temp / f"norm_{i:02d}.mp4"
        _run(["ffmpeg", "-y", "-i", str(src), "-vf",
              f"scale={cfg['video']['width']}:{cfg['video']['height']}:force_original_aspect_ratio=increase,crop={cfg['video']['width']}:{cfg['video']['height']},fps={cfg['video']['fps']}",
              "-an", "-c:v", "libx264", "-preset", cfg["video"]["preset"],
              "-crf", str(cfg["video"]["crf"]), "-pix_fmt", "yuv420p", str(dst)])
        normalized.append(dst)
    concat = temp / "concat.txt"
    concat.write_text("".join(f"file '{p.as_posix()}'\\n" for p in normalized + [Path(outro).resolve()]), encoding="utf-8")
    _run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(concat),
          "-c:v", "libx264", "-preset", cfg["video"]["preset"], "-crf", str(cfg["video"]["crf"]),
          "-pix_fmt", "yuv420p", "-r", str(cfg["video"]["fps"]), "-an",
          "-movflags", "+faststart", str(output)])
    return Path(output)
