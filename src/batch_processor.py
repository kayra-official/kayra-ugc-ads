from pathlib import Path
import json
from PIL import Image, ImageOps
from .video_generator import generate_scene, VideoGenerationError


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

    # New pipeline version invalidates old clips and manifest completions.
    if manifest.exists():
        state = json.loads(manifest.read_text(encoding="utf-8"))
        if state.get("pipeline") != pipeline:
            state = {"pipeline": pipeline, "completed": [], "failed": {}}
    else:
        state = {"pipeline": pipeline, "completed": [], "failed": {}}
    state.setdefault("completed", [])
    state.setdefault("failed", {})

    master = Path(image_path).expanduser().resolve()
    if not master.is_file():
        raise FileNotFoundError(f"Master model reference image not found: {master}")

    product = Path(board.get("product_reference", "")).expanduser()
    if not product.is_file():
        raise FileNotFoundError(f"Product-only reference image not found: {product}")

    model_count = int(board.get("model_scene_count", 6))
    model_sources = _find_model_reference_set(master, project_dir)
    fallback_crops = _make_framing_variants(master, project_dir, model_count)

    # Prioritize actual supplied pose photos. Crops are only fallback framing.
    scene_model_refs = []
    for idx in range(model_count):
        if idx < len(model_sources):
            scene_model_refs.append(model_sources[idx])
        else:
            scene_model_refs.append(fallback_crops[idx])

    retries = int(cfg["generation"].get("retries", 1))
    max_scenes = int(cfg["generation"].get("max_scenes_per_run", len(board["scenes"])))
    pending = [s for s in board["scenes"]
               if int(s["scene_number"]) not in state["completed"]][:max_scenes]

    for scene in pending:
        n = int(scene["scene_number"])
        dest = clips / f"scene_{n:02d}.mp4"
        if n in state["completed"] and dest.exists() and dest.stat().st_size > 1024:
            continue

        if scene.get("reference_role") == "product":
            ref = product.resolve()
        else:
            ref_index = int(scene.get("preferred_reference_index", n)) - 1
            ref = scene_model_refs[max(0, min(ref_index, len(scene_model_refs)-1))]

        last_error = None
        for _ in range(retries + 1):
            try:
                generate_scene(scene, ref, dest, cfg, product_reference=product)
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
