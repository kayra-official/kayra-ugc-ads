from pathlib import Path
import subprocess

def _run(cmd):
    subprocess.run(cmd, check=True, capture_output=True, text=True)

def assemble_video(clips_dir, outro, output, cfg):
    """Concatenate numbered scene clips and Kayra outro. Always outputs silent video."""
    clips, outro, output = Path(clips_dir), Path(outro), Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    temp = Path(cfg["app"]["temp_dir"])
    temp.mkdir(parents=True, exist_ok=True)
    width, height = int(cfg["video"]["width"]), int(cfg["video"]["height"])
    fps = int(cfg["video"]["fps"])
    scene_count = int(cfg["video"].get("scene_count", 9))
    preset, crf = cfg["video"]["preset"], str(cfg["video"]["crf"])
    normalized = []
    for i in range(1, scene_count + 1):
        src = clips / f"scene_{i:02d}.mp4"
        if not src.is_file():
            raise FileNotFoundError(f"Missing scene clip: {src}")
        dst = temp / f"norm_{i:02d}.mp4"
        _run(["ffmpeg","-y","-i",str(src),"-vf",
              f"scale={width}:{height}:force_original_aspect_ratio=increase,"
              f"crop={width}:{height},fps={fps},setsar=1",
              "-an","-c:v","libx264","-preset",preset,"-crf",crf,
              "-pix_fmt","yuv420p","-r",str(fps),str(dst)])
        normalized.append(dst)
    if not outro.is_file():
        raise FileNotFoundError(f"Missing Kayra outro: {outro}")
    norm_outro = temp / "norm_outro.mp4"
    _run(["ffmpeg","-y","-i",str(outro),"-vf",
          f"scale={width}:{height}:force_original_aspect_ratio=increase,"
          f"crop={width}:{height},fps={fps},setsar=1",
          "-an","-c:v","libx264","-preset",preset,"-crf",crf,
          "-pix_fmt","yuv420p","-r",str(fps),str(norm_outro)])
    concat = temp / "concat.txt"
    concat.write_text("".join(f"file '{p.resolve().as_posix()}'\n"
                              for p in normalized+[norm_outro]), encoding="utf-8")
    silent = temp / "silent_final.mp4"
    _run(["ffmpeg","-y","-f","concat","-safe","0","-i",str(concat),
          "-c:v","libx264","-preset",preset,"-crf",crf,"-pix_fmt","yuv420p",
          "-r",str(fps),"-an","-movflags","+faststart",str(silent)])
    if output.exists():
        output.unlink()
    silent.replace(output)
    return output
