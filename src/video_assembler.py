from pathlib import Path
import subprocess
import json

def _run(cmd):
    subprocess.run(cmd, check=True, capture_output=True, text=True)


def media_duration(path):
    probe = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "json", str(path)],
        check=True, capture_output=True, text=True,
    )
    return float(json.loads(probe.stdout)["format"]["duration"])


def slow_motion_clip(source_path, output_path, cfg, speed=0.60, target_duration=None):
    """Retiming an existing generated scene with interpolated frames, without audio."""
    source, target = Path(source_path), Path(output_path)
    fps = int(cfg["video"]["fps"])
    width, height = int(cfg["video"]["width"]), int(cfg["video"]["height"])
    preset, crf = cfg["video"]["preset"], str(cfg["video"]["crf"])
    factor = 1 / float(speed)
    vf = (f"minterpolate=fps={fps * 2}:mi_mode=mci,setpts={factor}*PTS,fps={fps},"
          f"scale={width}:{height}:force_original_aspect_ratio=increase,crop={width}:{height},setsar=1")
    if target_duration:
        vf += ",tpad=stop_mode=clone:stop_duration=1"
    target.parent.mkdir(parents=True, exist_ok=True)
    cmd = ["ffmpeg", "-y", "-i", str(source), "-vf", vf]
    if target_duration:
        cmd.extend(["-t", str(float(target_duration))])
    cmd.extend(["-an", "-c:v", "libx264", "-preset", preset, "-crf", crf,
                "-pix_fmt", "yuv420p", "-r", str(fps), str(target)])
    _run(cmd)
    return target


def prepare_product_clip(product_clip, output_path, cfg):
    """Prepare the supplied product video as one silent slow-motion clip."""
    source, target = Path(product_clip), Path(output_path)
    if not source.is_file():
        raise FileNotFoundError(f"Product video clip not found: {source}")
    duration = media_duration(source)
    if duration <= 0:
        raise ValueError(f"Product video has invalid duration: {duration}")

    target.parent.mkdir(parents=True, exist_ok=True)
    target_duration = float(cfg["video"].get("product_clip_duration_seconds", 12.0))
    base_speed = float(cfg["video"].get("product_speed", 0.5))
    if not 0 < target_duration <= 15:
        raise ValueError("video.product_clip_duration_seconds must be greater than 0 and at most 15.")
    if not 0 < base_speed <= 1:
        raise ValueError("video.product_speed must be greater than 0 and at most 1.")
    source_window = min(duration, target_duration * base_speed)
    start = max(0.0, duration - source_window)
    speed = source_window / target_duration
    slow_factor = 1 / speed
    fps = int(cfg["video"]["fps"])
    width, height = int(cfg["video"]["width"]), int(cfg["video"]["height"])
    preset, crf = cfg["video"]["preset"], str(cfg["video"]["crf"])
    vf = (
        f"minterpolate=fps={fps * 2}:mi_mode=mci,setpts={slow_factor}*PTS,"
        f"fps={fps},scale={width}:{height}:force_original_aspect_ratio=increase,"
        f"crop={width}:{height},setsar=1,"
        # Retiming can lose a frame or two at the endpoint; clone the last
        # frame so the fixed-duration export always reaches its 12-second mark.
        f"tpad=stop_mode=clone:stop_duration=1"
    )
    _run(["ffmpeg", "-y", "-ss", f"{start:.6f}", "-i", str(source), "-t", str(target_duration),
          "-vf", vf, "-an", "-c:v", "libx264",
          "-preset", preset, "-crf", crf, "-pix_fmt", "yuv420p", "-r", str(fps), str(target)])
    return target

def assemble_video(clips_dir, outro, output, cfg, scene_count=None, scene_numbers=None,
                   clip_durations=None, hold_after=None):
    """Concatenate normalized silent scenes followed by the Kayra logo."""
    clips, outro, output = Path(clips_dir), Path(outro), Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    temp = Path(cfg["app"]["temp_dir"])
    temp.mkdir(parents=True, exist_ok=True)
    width, height = int(cfg["video"]["width"]), int(cfg["video"]["height"])
    fps = int(cfg["video"]["fps"])
    scene_count = int(scene_count if scene_count is not None else cfg["video"].get("scene_count", 9))
    scene_numbers = scene_numbers or range(1, scene_count + 1)
    preset, crf = cfg["video"]["preset"], str(cfg["video"]["crf"])
    clip_durations = clip_durations or {}
    hold_after = hold_after or {}
    normalized = []
    for i in scene_numbers:
        src = clips / f"scene_{i:02d}.mp4"
        if not src.is_file():
            raise FileNotFoundError(f"Missing scene clip: {src}")
        dst = temp / f"norm_{i:02d}.mp4"
        duration = clip_durations.get(i)
        start = max(0.0, (media_duration(src) - float(duration)) / 2) if duration else 0.0
        cmd = ["ffmpeg", "-y"]
        if start:
            cmd.extend(["-ss", f"{start:.6f}"])
        cmd.extend(["-i", str(src)])
        if duration:
            cmd.extend(["-t", str(duration)])
        video_filter = (f"scale={width}:{height}:force_original_aspect_ratio=increase,"
                        f"crop={width}:{height},fps={fps},setsar=1")
        if hold_after.get(i, 0):
            video_filter += f",tpad=stop_mode=clone:stop_duration={float(hold_after[i]):.6f}"
        cmd.extend(["-vf", video_filter,
              "-an","-c:v","libx264","-preset",preset,"-crf",crf,
              "-pix_fmt","yuv420p","-r",str(fps),str(dst)])
        _run(cmd)
        normalized.append(dst)
    if not outro.is_file():
        raise FileNotFoundError(f"Missing Kayra outro: {outro}")
    norm_outro = temp / "norm_outro.mp4"
    target_seconds = float(cfg["video"].get("target_seconds", 28))
    scene_duration = sum(media_duration(path) for path in normalized)
    logo_duration = media_duration(outro)
    logo_pad = max(0.0, target_seconds - scene_duration - logo_duration)
    logo_filter = (f"scale={width}:{height}:force_original_aspect_ratio=increase,"
                   f"crop={width}:{height},fps={fps},setsar=1")
    if logo_pad > 0:
        logo_filter += f",tpad=stop_mode=clone:stop_duration={logo_pad:.6f}"
    outro_seconds = float(cfg["video"].get("outro_seconds", 2.0))
    _run(["ffmpeg","-y","-i",str(outro),"-t",str(outro_seconds),"-vf",logo_filter,
          "-an","-c:v","libx264","-preset",preset,"-crf",crf,
          "-pix_fmt","yuv420p","-r",str(fps),str(norm_outro)])
    concat = temp / "concat.txt"
    concat.write_text("".join(f"file '{p.resolve().as_posix()}'\n"
                              for p in normalized+[norm_outro]), encoding="utf-8")
    silent = temp / "silent_final.mp4"
    _run(["ffmpeg","-y","-f","concat","-safe","0","-i",str(concat),
          "-c:v","libx264","-preset",preset,"-crf",crf,"-pix_fmt","yuv420p",
          "-r",str(fps),"-an","-t",str(target_seconds),"-movflags","+faststart",str(silent)])
    if output.exists():
        output.unlink()
    silent.replace(output)
    return output


def fit_model_scene_durations(product_clip, outro, target_seconds, fps, scene_numbers=(5, 6),
                              outro_seconds=None, hold_seconds=0):
    """Allocate the remaining final-video frames evenly across cached model clips."""
    target_frames = round(float(target_seconds) * int(fps))
    logo_duration = media_duration(outro) if outro_seconds is None else float(outro_seconds)
    fixed_frames = (round(media_duration(product_clip) * int(fps))
                    + round(logo_duration * int(fps))
                    + round(float(hold_seconds) * int(fps)))
    available = target_frames - fixed_frames
    if available < len(scene_numbers):
        raise ValueError("Target video duration is too short for the product clip and logo outro.")
    base, extra = divmod(available, len(scene_numbers))
    return {
        scene: (base + (index < extra)) / int(fps)
        for index, scene in enumerate(scene_numbers)
    }
