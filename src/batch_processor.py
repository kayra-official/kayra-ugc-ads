from pathlib import Path
import json
from shutil import copy2
from .video_generator import generate_scene, VideoGenerationError
from .video_assembler import slow_motion_clip


def _find_model_reference_set(master_reference, project_dir):
    """Use separate supplied model photos when present; otherwise use master."""
    master = Path(master_reference).resolve()
    source_dir = master.parent.parent  # project/assets -> project
    # Also search the original product input folder recorded by product compositor.
    metadata = master.parent / "master_reference.json"
    if metadata.exists():
        try:
            info = json.loads(metadata.read_text(encoding="utf-8"))
            source_dir = Path(info.get("model_reference_source", master)).resolve().parent
        except Exception:
            pass

    candidates = []
    for pattern in ("model_reference_*.jpg", "model_reference_*.jpeg",
                    "model_reference_*.png", "model_pose_*.jpg",
                    "model_pose_*.jpeg", "model_pose_*.png",
                    "model_*.jpg", "model_*.jpeg", "model_*.png"):
        candidates.extend(source_dir.glob(pattern))
    candidates = sorted({p.resolve() for p in candidates if p.resolve() != master},
                        key=lambda p: p.name.lower())
    return [master] + candidates


def _make_framing_variants(master_reference, project_dir, count=6):
    """Create intentional scene-specific crops from the supplied model photo."""
    master = Path(master_reference).resolve()
    out = Path(project_dir) / "assets" / "scene_references"
    out.mkdir(parents=True, exist_ok=True)

    # Normalized crop windows: left, top, right, bottom.
    # Scene 2 targets the LEFT ear: the creator's face in the supplied
    # portrait faces right, so the previous right-side crop missed the earring.
    windows = [
        (0.12, 0.43, 0.88, 0.88),  # Scene 1: neckline / pendant / upper chest
        (0.04, 0.18, 0.50, 0.52),  # Scene 2: left ear / earring / cheek
        (0.14, 0.34, 0.86, 0.82),  # Scene 3: necklace / collarbone
        (0.08, 0.18, 0.92, 0.92),
        (0.08, 0.12, 0.92, 0.88),
        (0.14, 0.30, 0.86, 0.86),
    ]

    paths = []
    with Image.open(master) as source:
        im = ImageOps.exif_transpose(source).convert("RGB")
        w, h = im.size
        for idx in range(count):
            l, t, r, b = windows[idx % len(windows)]
            left, top = int(l * w), int(t * h)
            right, bottom = int(r * w), int(b * h)
            dest = out / f"model_scene_{idx+1:02d}.jpg"
            im.crop((left, top, right, bottom)).save(dest, quality=97)
            paths.append(dest)
    return paths



def process_all(board, image_path, project_dir, cfg, progress=None):
    clips = Path(project_dir) / "clips"
    clips.mkdir(parents=True, exist_ok=True)
    manifest = Path(project_dir) / "manifest.json"
    pipeline = board.get("pipeline")

    # Pipeline or prompt changes should only invalidate clips whose saved
    # generation request no longer matches the current scene specification.
    if manifest.exists():
        state = json.loads(manifest.read_text(encoding="utf-8"))
        if state.get("pipeline") != pipeline:
            state["pipeline"] = pipeline
            state.setdefault("failed", {})
    else:
        state = {"pipeline": pipeline, "completed": [], "failed": {}}
    state.setdefault("completed", [])
    state.setdefault("failed", {})

    references = board.get("references", {})
    missing_refs = [key for key in ("product_hero", "model_ugc")
                    if not Path(references.get(key, "")).is_file()]
    if missing_refs:
        raise FileNotFoundError("Source references missing: " + ", ".join(missing_refs))
    product = Path(references["product_hero"]).resolve()

    for n in (5, 6):
        existing = clips / f"scene_{n:02d}.mp4"
        if existing.is_file() and existing.stat().st_size > 1024:
            scene = next((s for s in board["scenes"] if int(s["scene_number"]) == n), None)
            expected_ref = Path(
                (scene or {}).get("reference_image") or references.get("model_ugc", "")
            ).resolve()
            request_path = clips / f"scene_{n:02d}_ltx_source.request.json"
            if not request_path.exists():
                request_path = clips / f"scene_{n:02d}.request.json"
            try:
                previous_request = json.loads(request_path.read_text())
                previous_ref_value = previous_request.get("reference_image")
                previous_ref = Path(previous_ref_value).resolve() if previous_ref_value else None
            except (OSError, ValueError, TypeError):
                previous_request = {}
                previous_ref = None

            expected_prompt = (scene or {}).get("video_prompt")
            prompt_changed = bool(expected_prompt and previous_request.get("prompt")
                                  and previous_request["prompt"] != expected_prompt)
            if previous_ref is not None and (previous_ref != expected_ref or prompt_changed):
                # Preserve old renders, but regenerate when the source or scene
                # direction changed so the new timeline uses the right footage.
                archive = clips / "stale_model_scene"
                archive.mkdir(exist_ok=True)
                for stale in (existing, clips / f"scene_{n:02d}_ltx_source.mp4",
                              request_path, clips / f"scene_{n:02d}.request.json"):
                    if stale.is_file():
                        destination = archive / stale.name
                        if destination.exists():
                            destination = archive / f"{stale.stem}_{len(list(archive.iterdir()))}{stale.suffix}"
                        stale.replace(destination)
                state["completed"] = [done for done in state["completed"] if int(done) != n]
                applied = state.get("slow_motion_applied", {})
                if isinstance(applied, dict):
                    applied.pop(str(n), None)
            else:
                state["completed"] = sorted(set(state["completed"] + [n]))

    applied = state.setdefault("slow_motion_applied", {})
    if isinstance(applied, list):
        applied = {str(n): 0.60 for n in applied}
        state["slow_motion_applied"] = applied
    model_speed = float(cfg["generation"].get("model_scene_speed", 0.5))

    # Retiming only the two retained model scenes avoids touching discarded clips.
    for n in (5, 6):
        dest = clips / f"scene_{n:02d}.mp4"
        if n in state["completed"] and dest.is_file() and applied.get(str(n)) != model_speed:
            source_clip = clips / f"scene_{n:02d}_ltx_source.mp4"
            source_speed = float(applied.get(str(n), 1.0))
            retime_speed = model_speed
            if not source_clip.is_file():
                copy2(dest, source_clip)
                retime_speed = model_speed / source_speed
            temp_slow = clips / f".scene_{n:02d}.slow.mp4"
            slow_motion_clip(source_clip, temp_slow, cfg, speed=retime_speed,
                             target_duration=cfg["video"].get("scene_seconds", 7.0))
            temp_slow.replace(dest)
            applied[str(n)] = model_speed
            manifest.write_text(json.dumps(state, indent=2), encoding="utf-8")

    retries = int(cfg["generation"].get("retries", 1))
    max_scenes = int(cfg["generation"].get("max_scenes_per_run", len(board["scenes"])))
    pending = [s for s in board["scenes"]
               if int(s["scene_number"]) not in state["completed"]][:max_scenes]

    for scene in pending:
        n = int(scene["scene_number"])
        dest = clips / f"scene_{n:02d}.mp4"
        if n in state["completed"] and dest.exists() and dest.stat().st_size > 1024:
            continue

        ref = Path(scene.get("reference_image") or references[scene["reference_role"]]).resolve()

        last_error = None
        for _ in range(retries + 1):
            try:
                raw = clips / f"scene_{n:02d}_ltx_source.mp4" if n in (5, 6) else dest
                generate_scene(scene, ref, raw, cfg, product_reference=product)
                if n in (5, 6):
                    slow_motion_clip(raw, dest, cfg, speed=model_speed,
                                     target_duration=float(scene.get("duration_seconds", 7.0)))
                    applied[str(n)] = model_speed
                state["completed"] = sorted(set(state["completed"] + [n]))
                state["failed"].pop(str(n), None)
                last_error = None
                break
            except Exception as exc:
                last_error = str(exc)

        if last_error:
            state["failed"][str(n)] = last_error
            manifest.write_text(json.dumps(state, indent=2), encoding="utf-8")
            raise VideoGenerationError(f"Scene {n:02d} failed: {last_error}")

        manifest.write_text(json.dumps(state, indent=2), encoding="utf-8")
        if progress:
            progress(len(state["completed"]), len(board["scenes"]),
                     f"Scene {n:02d}/{len(board['scenes'])} complete")

    if len(state["completed"]) < len(board["scenes"]):
        print(f"Batch completed: {len(state['completed'])}/{len(board['scenes'])}. Run again to continue.")
    return clips
