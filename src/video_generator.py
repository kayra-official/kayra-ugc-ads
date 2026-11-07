from pathlib import Path
import json
import shlex
import subprocess


class VideoGenerationError(RuntimeError):
    pass


def generate_scene(scene, reference_image, output_path, cfg, product_reference=None):
    """Run one real LTX image-to-video scene using the scene's assigned reference image."""
    command = cfg["generation"].get("command", "").strip()
    if not command:
        raise VideoGenerationError(
            "LTX-2.3 MLX backend is not configured. Set generation.command "
            "to the local JSON-request wrapper before generating video."
        )

    role = scene.get("reference_role", "model")
    selected_reference = product_reference if role == "product" else reference_image
    if not selected_reference:
        raise VideoGenerationError(f"Scene {scene['scene_number']:02d} requires a {role} reference image.")
    reference = Path(selected_reference).expanduser().resolve()
    if not reference.is_file():
        raise VideoGenerationError(f"Scene {scene['scene_number']:02d} {role} reference not found: {reference}")

    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    contract = {
        "scene_number": scene["scene_number"],
        "prompt": scene["video_prompt"],
        "reference_image": str(reference),
        "reference_role": role,
        "product_reference": str(Path(product_reference).resolve()) if product_reference else None,
        "output_video": str(out.resolve()),
        "duration_seconds": scene.get("duration_seconds", 1),
        "width": cfg["video"]["width"],
        "height": cfg["video"]["height"],
        "fps": cfg["video"]["fps"],
        "seed": 20261107 + int(scene["scene_number"]),
        "model": "LTX-2.3 MLX",
        "mode": "image-to-video",
        "preserve_model_identity": role == "model",
        "preserve_product_design": True,
        "reference_is_authoritative": True,
    }
    request = out.with_suffix(".request.json")
    request.write_text(json.dumps(contract, indent=2, ensure_ascii=False), encoding="utf-8")

    cmd = shlex.split(command) + [str(request)]
    try:
        subprocess.run(
            cmd, check=True,
            timeout=cfg["generation"]["command_timeout_seconds"],
        )
    except subprocess.CalledProcessError as exc:
        raise VideoGenerationError(
            f"Scene {scene['scene_number']:02d} LTX adapter failed with exit code {exc.returncode}."
        ) from exc
    except subprocess.TimeoutExpired as exc:
        raise VideoGenerationError(
            f"Scene {scene['scene_number']:02d} exceeded the configured timeout."
        ) from exc

    if not out.exists() or out.stat().st_size < 1024:
        raise VideoGenerationError(
            f"Scene {scene['scene_number']:02d}: adapter did not create a valid video."
        )
    return out
