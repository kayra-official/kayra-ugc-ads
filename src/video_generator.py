from pathlib import Path
import json
import hashlib
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

    role = scene.get("reference_role", "model_ugc")
    is_product = role == "product" or role == "product_hero"
    is_snapshot_pass = scene.get("conditioning_stage") == "snapshot"
    selected_reference = product_reference if role == "product" else reference_image
    if not selected_reference:
        raise VideoGenerationError(f"Scene {scene['scene_number']:02d} requires a {role} reference image.")
    reference = Path(selected_reference).expanduser().resolve()
    if not reference.is_file():
        raise VideoGenerationError(f"Scene {scene['scene_number']:02d} {role} reference not found: {reference}")
    digest = hashlib.sha256(reference.read_bytes()).hexdigest()
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    contract = {
        "scene_number": scene["scene_number"],
        "prompt": scene["video_prompt"],
        "reference_image": str(reference),
        "reference_sha256": digest,
        "reference_role": role,
        "product_reference": str(Path(product_reference).resolve()) if product_reference else None,
        "output_video": str(out.resolve()),
        "duration_seconds": scene.get("duration_seconds", 1),
        "frames": round(float(scene.get("duration_seconds", 1)) * int(cfg["video"]["fps"])),
        "width": cfg["video"]["width"],
        "height": cfg["video"]["height"],
        "fps": cfg["video"]["fps"],
        "seed": 20261107 + int(scene["scene_number"]),
        "model": "LTX-2.3 MLX",
        "mode": "image-to-video",
        "preserve_model_identity": not is_product,
        "preserve_product_design": True,
        "reference_is_authoritative": True,
        "conditioning_stage": (
            "ugc_snapshot" if is_snapshot_pass else
            "scene_from_original_model_image" if role == "model_ugc" else
            "scene_from_ugc_snapshot"
        ),
        # Explicit guide conditioning anchors model scenes to the same cached
        # model-with-jewellery image instead of letting LTX freely reinterpret it.
        "image_binding": "guide",
        "image_strength": float(
            cfg["generation"].get("snapshot_product_image_strength", 0.95)
            if role == "product_hero"
            else cfg["generation"].get(
                "snapshot_image_strength" if is_snapshot_pass else "model_scene_image_strength",
                0.65 if is_snapshot_pass else 1.0,
            )
        ),
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
