"""Generate and cache product-edit and creator UGC stills locally."""
from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

from .snapshot_manager import discover_snapshots, PROMPTS
from .product_image_generator import generate_product_snapshot, PRODUCT_BACKGROUND_PROMPT, product_snapshot_signature
from .video_generator import generate_scene

SNAPSHOT_PROMPTS = PROMPTS

def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def _extract_middle_frame(video: Path, image: Path, cfg) -> None:
    probe = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=nw=1:nk=1", str(video)],
        check=True, capture_output=True, text=True,
    )
    at = max(0.5, float(probe.stdout.strip()) * 0.55)
    w, h = int(cfg["generation"]["render_width"]), int(cfg["generation"]["render_height"])
    subprocess.run(
        ["ffmpeg", "-y", "-ss", str(at), "-i", str(video), "-frames:v", "1",
         "-vf", f"scale={w}:{h}:force_original_aspect_ratio=decrease,pad={w}:{h}:(ow-iw)/2:(oh-ih)/2",
         "-update", "1", str(image)], check=True, capture_output=True, text=True,
    )
    if not image.is_file() or image.stat().st_size < 1024:
        raise RuntimeError(f"LTX did not produce a usable UGC snapshot: {image}")

def ensure_ugc_snapshots(product_folder, project_dir, cfg, progress=None, roles=None):
    """Return product UGC stills and the original model-with-jewellery photo."""
    product_folder, project_dir = Path(product_folder).resolve(), Path(project_dir).resolve()
    source_refs = discover_snapshots(product_folder)
    product_source = source_refs.get("product_hero")
    model_source = source_refs.get("model_ugc")
    roles = list(roles or SNAPSHOT_PROMPTS)
    if "product_hero" in roles and not product_source:
        raise FileNotFoundError(f"Product source image not found under {product_folder}")
    if "model_ugc" in roles and not model_source:
        raise FileNotFoundError(f"Model-with-jewellery source image not found under {product_folder}; add model_reference.jpg")

    work = project_dir / "ugc_snapshot_generation"
    stills = project_dir / "ugc_snapshots"
    work.mkdir(parents=True, exist_ok=True)
    stills.mkdir(parents=True, exist_ok=True)
    manifest_path = stills / "manifest.json"
    manifest = json.loads(manifest_path.read_text()) if manifest_path.exists() else {}
    output = {}
    for i, role in enumerate(roles, 1):
        source = product_source if role == "product_hero" else model_source
        if role == "model_ugc":
            # Use the actual supplied model photo as LTX's reference. A generated
            # intermediate portrait can change the face and jewellery before the
            # video model even starts, so do not create or reuse that derivative.
            output[role] = str(source.resolve())
            if progress:
                progress(i, len(roles), "Using original model-with-jewellery image")
            continue
        target = stills / f"{role}.png"
        algorithm = "comfyui_iclight_local_v2" if role == "product_hero" else "model_ugc_v1"
        prompt = PRODUCT_BACKGROUND_PROMPT if role == "product_hero" else SNAPSHOT_PROMPTS[role]
        backend_signature = product_snapshot_signature(cfg) if role == "product_hero" else ""
        digest_input = _sha256(source) + prompt + algorithm + backend_signature
        digest = hashlib.sha256(digest_input.encode()).hexdigest()
        record = manifest.get(role, {})
        # The approved local model UGC still is expensive to recreate and its
        # source has not changed; preserve it when upgrading product handling.
        if role == "model_ugc" and target.is_file() and target.stat().st_size > 1024:
            output[role] = str(target.resolve())
            if progress:
                progress(i, len(roles), "Reusing existing model UGC snapshot")
            continue
        if target.is_file() and record.get("input_digest") == digest:
            output[role] = str(target.resolve())
            if progress:
                progress(i, len(roles), f"Reusing UGC snapshot {role}")
            continue

        if role == "product_hero":
            generate_product_snapshot(source, target, cfg,
                lambda message: progress(i - 1, len(roles), message) if progress else None)
            manifest[role] = {"input_digest": digest, "source_image": str(source), "snapshot_image": str(target),
                              "prompt": prompt, "generator": "local_comfyui_iclight"}
            manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
            output[role] = str(target.resolve())
            continue

        preview_clip = work / f"{role}.mp4"
        scene = {
            "scene_number": 90 + i,
            "duration_seconds": float(cfg["video"].get("scene_seconds", 3.7)),
            "scene_name": f"UGC_SNAPSHOT_{role.upper()}",
            "reference_role": role,
            "video_prompt": SNAPSHOT_PROMPTS[role],
            "conditioning_stage": "snapshot",
        }
        if progress:
            progress(i - 1, len(roles), f"Generating UGC snapshot {i}/{len(roles)}: {role}")
        generate_scene(scene, source, preview_clip, cfg, product_reference=source)
        _extract_middle_frame(preview_clip, target, cfg)
        manifest[role] = {"input_digest": digest, "source_image": str(source), "snapshot_image": str(target),
                          "prompt": SNAPSHOT_PROMPTS[role], "generator": "local_ltx_2_3_mlx"}
        manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
        output[role] = str(target.resolve())
        if progress:
            progress(i, len(roles), f"UGC snapshot ready: {role}")
    return output
