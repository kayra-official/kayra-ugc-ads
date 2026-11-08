from pathlib import Path
import json
from PIL import Image, ImageOps

from .video_generator import generate_scene, VideoGenerationError


def _make_model_reference_variants(master_reference, project_dir, scene_count=6):
    """Create subtle framing variants from the same original model photo.
    These vary crop/scale, not the creator's actual pose or identity.
    """
    master = Path(master_reference).resolve()
    out_dir = Path(project_dir) / "assets" / "scene_references"
    out_dir.mkdir(parents=True, exist_ok=True)

    variants = {}
    with Image.open(master) as im:
        im = ImageOps.exif_transpose(im).convert("RGB")
        w, h = im.size
        # Different crop windows provide varied first-frame composition.
        specs = {
            1: (1.00, 0.50, 0.50),
            2: (0.88, 0.52, 0.56),
            3: (0.78, 0.50, 0.46),
            4: (0.92, 0.60, 0.50),
            5: (0.96, 0.42, 0.54),
            6: (0.72, 0.50, 0.43),
        }
        for number in range(1, scene_count + 1):
            scale, cx, cy = specs.get(number, (0.9, 0.5, 0.5))
            cw, ch = max(2, int(w * scale)), max(2, int(h * scale))
            left = max(0, min(w - cw, int(cx * w - cw / 2)))
            top = max(0, min(h - ch, int(cy * h - ch / 2)))
            crop = im.crop((left, top, left + cw, top + ch))
            path = out_dir / f"model_scene_{number:02d}.jpg"
            crop.save(path, quality=95)
            variants[number] = path
    return variants


def process_all(board, image_path, project_dir, cfg, progress=None):
    clips = Path(project_dir) / "clips"
    clips.mkdir(parents=True, exist_ok=True)

    manifest = Path(project_dir) / "manifest.json"
    pipeline = board.get("pipeline")
    if manifest.exists():
        state = json.loads(manifest.read_text(encoding="utf-8"))
        # Do not reuse old scene clips when storyboard/pipeline version changes.
        if state.get("pipeline") != pipeline:
            state = {"pipeline": pipeline, "completed": [], "failed": {}}
    else:
        state = {"pipeline": pipeline, "completed": [], "failed": {}}

    state.setdefault("completed", [])
    state.setdefault("failed", {})

    master_reference = Path(image_path).expanduser().resolve()
    if not master_reference.is_file():
        raise FileNotFoundError(f"Master model reference image not found: {master_reference}")

    product_reference = Path(board.get("product_reference", "")).expanduser()
    if not product_reference.is_file():
        raise FileNotFoundError(
            f"Product-only reference image not found: {product_reference}. "
            "Set board['product_reference'] to the original product image."
        )

    scenes = board["scenes"]
    model_count = int(board.get("model_scene_count", 6))
    model_variants = _make_model_reference_variants(master_reference, project_dir, model_count)
    retries = int(cfg["generation"].get("retries", 1))
    max_scenes = int(cfg["generation"].get("max_scenes_per_run", len(scenes)))

    # Select the next unfinished scenes, not always scenes 1..N.
    pending_scenes = [
        s for s in scenes
        if int(s["scene_number"]) not in state["completed"]
    ][:max_scenes]

    for scene in pending_scenes:
        number = int(scene["scene_number"])
        destination = clips / f"scene_{number:02d}.mp4"

        # Use original product-only photo for macro scenes.
        if scene.get("reference_role") == "product":
            scene_reference = product_reference.resolve()
        else:
            scene_reference = model_variants.get(number, master_reference)

        if (
            number in state["completed"]
            and destination.exists()
            and destination.stat().st_size > 1024
        ):
            continue

        last_error = None
        for attempt in range(retries + 1):
            try:
                generate_scene(
                    scene,
                    scene_reference,
                    destination,
                    cfg,
                    product_reference=product_reference,
                )
                state["completed"] = sorted(set(state["completed"] + [number]))
                state["failed"].pop(str(number), None)
                last_error = None
                break
            except Exception as exc:
                last_error = str(exc)

        if last_error:
            state["failed"][str(number)] = last_error
            manifest.write_text(json.dumps(state, indent=2), encoding="utf-8")
            raise VideoGenerationError(
                f"Scene {number:02d} failed after retries: {last_error}"
            )

        manifest.write_text(json.dumps(state, indent=2), encoding="utf-8")
        if progress:
            progress(
                len(state["completed"]),
                len(scenes),
                f"Scene {number:02d}/{len(scenes)} complete",
            )

    if len(state["completed"]) < len(scenes):
        print(
            f"Batch completed: {len(state['completed'])}/{len(scenes)} scenes. "
            "Run again to continue."
        )

    return clips
