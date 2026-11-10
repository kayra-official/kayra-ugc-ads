from pathlib import Path
import json
import hashlib
from .video_generator import VideoGenerationError, generate_scene
from .still_video_generator import generate_model_motion


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

    # Migrate old model clip names 05/06 to the compact final numbering 02/03.
    # Keep any existing renders and request files together under their new IDs.
    for old_number, new_number in ((5, 2), (6, 3)):
        old_prefix, new_prefix = f"scene_{old_number:02d}", f"scene_{new_number:02d}"
        for old_path in list(clips.glob(f"{old_prefix}*")):
            new_path = clips / (new_prefix + old_path.name[len(old_prefix):])
            if new_path.exists():
                archive = clips / "renumbered_legacy_scenes"
                archive.mkdir(exist_ok=True)
                new_path = archive / old_path.name
            old_path.replace(new_path)
    state["completed"] = sorted({
        {5: 2, 6: 3}.get(int(number), int(number))
        for number in state["completed"] if int(number) not in (7, 8)
    })
    state["failed"] = {
        str({"5": 2, "6": 3}.get(str(number), number)): error
        for number, error in state["failed"].items() if str(number) not in ("7", "8")
    }
    applied_state = state.get("slow_motion_applied", {})
    if isinstance(applied_state, dict):
        state["slow_motion_applied"] = {
            str({"5": 2, "6": 3}.get(str(number), number)): speed
            for number, speed in applied_state.items() if str(number) not in ("7", "8")
        }

    references = board.get("references", {})
    missing_refs = [key for key in ("product_hero", "model_ugc")
                    if not Path(references.get(key, "")).is_file()]
    if missing_refs:
        raise FileNotFoundError("Source references missing: " + ", ".join(missing_refs))
    def sha256_file(path):
        digest = hashlib.sha256()
        with path.open("rb") as source:
            for block in iter(lambda: source.read(1024 * 1024), b""):
                digest.update(block)
        return digest.hexdigest()

    for n in (2, 3):
        existing = clips / f"scene_{n:02d}.mp4"
        if existing.is_file() and existing.stat().st_size > 1024:
            scene = next((s for s in board["scenes"] if int(s["scene_number"]) == n), None)
            expected_ref = Path(
                (scene or {}).get("reference_image") or references.get("model_ugc", "")
            ).resolve()
            metadata_path = clips / (
                f"scene_{n:02d}.motion.json" if n == 2
                else f"scene_{n:02d}.request.json"
            )
            try:
                previous = json.loads(metadata_path.read_text())
            except (OSError, ValueError, TypeError):
                previous = {}
            current = (
                previous.get("model") == (
                    "FFmpeg deterministic still" if n == 2 else "LTX-2.3 MLX"
                )
                and previous.get("reference_image") == str(expected_ref)
                and previous.get("reference_sha256") == sha256_file(expected_ref)
                and previous.get("prompt") == (scene or {}).get("video_prompt")
                and float(previous.get("duration_seconds", 0)) == float((scene or {}).get("duration_seconds", 7.0))
            )
            if not current:
                # Preserve old LTX/mismatched renders, then recreate from the
                # exact supplied still with a deterministic camera path.
                archive = clips / "stale_model_scene"
                archive.mkdir(exist_ok=True)
                for stale in (existing, metadata_path, clips / f"scene_{n:02d}.motion.json", clips / f"scene_{n:02d}_ltx_source.mp4",
                              clips / f"scene_{n:02d}_ltx_source.request.json",
                              clips / f"scene_{n:02d}.request.json"):
                    if stale.is_file():
                        destination = archive / stale.name
                        if destination.exists():
                            destination = archive / f"{stale.stem}_{len(list(archive.iterdir()))}{stale.suffix}"
                        stale.replace(destination)
                state["completed"] = [done for done in state["completed"] if int(done) != n]
            else:
                state["completed"] = sorted(set(state["completed"] + [n]))

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
                if n == 2:
                    # A tightly framed, deterministic camera move prevents LTX
                    # from widening back out to the full portrait and revealing
                    # the model's face in this jewellery-detail scene.
                    generate_model_motion(ref, dest, scene, cfg)
                else:
                    generate_scene(scene, ref, dest, cfg)
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
