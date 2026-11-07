from pathlib import Path
import json

from .video_generator import generate_scene, VideoGenerationError


def process_all(board, image_path, project_dir, cfg, progress=None):
    clips = Path(project_dir) / "clips"
    clips.mkdir(parents=True, exist_ok=True)

    manifest = Path(project_dir) / "manifest.json"
    state = (
        json.loads(manifest.read_text(encoding="utf-8"))
        if manifest.exists()
        else {"pipeline": board.get("pipeline"), "completed": [], "failed": {}}
    )

    state.setdefault("pipeline", board.get("pipeline"))
    master_reference = Path(image_path).expanduser().resolve()
    if not master_reference.is_file():
        raise FileNotFoundError(
            f"Master model reference image not found: {master_reference}"
        )

    product_reference = board.get("product_reference")
    scenes = board["scenes"]
    retries = int(cfg["generation"].get("retries", 1))

    max_scenes = int(cfg["generation"].get("max_scenes_per_run", 5))
    pending_scenes = scenes[:max_scenes]

    for scene in pending_scenes:
        number = int(scene["scene_number"])
        destination = clips / f"scene_{number:02d}.mp4"

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
                    master_reference,
                    destination,
                    cfg,
                    product_reference=product_reference,
                )
                state["completed"] = sorted(
                    set(state["completed"] + [number])
                )
                state["failed"].pop(str(number), None)
                last_error = None
                break
            except Exception as exc:
                last_error = str(exc)

        if last_error:
            state["failed"][str(number)] = last_error
            manifest.write_text(
                json.dumps(state, indent=2), encoding="utf-8"
            )
            raise VideoGenerationError(
                f"Scene {number:02d} failed after retries: {last_error}"
            )

        manifest.write_text(
            json.dumps(state, indent=2), encoding="utf-8"
        )

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
