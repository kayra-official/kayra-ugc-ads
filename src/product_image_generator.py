"""Locally segment supplier photos and relight them with a ComfyUI workflow."""
from __future__ import annotations

import hashlib
from pathlib import Path

from PIL import Image, ImageFilter, ImageOps

from .comfyui_client import run_product_workflow, validate_comfyui_product_setup


PRODUCT_BACKGROUND_PROMPT = (
    "Photorealistic vertical 9:16 close overhead photograph of an empty warm ivory linen "
    "fabric surface, soft natural window light, very subtle woven texture, gentle natural "
    "tonal variation, elegant minimal Brazilian jewellery product photography backdrop, "
    "clean uncluttered composition, evenly lit neutral beige surface. The entire scene is "
    "empty. Absolutely no jewelry, no objects, no props, no text, no logo, no watermark, "
    "no people, no hands, no packaging."
)


def _workflow_path(cfg) -> Path:
    path = Path(cfg.get("generation", {}).get(
        "comfyui_product_workflow", "assets/workflows/product_snapshot_api.json"
    )).expanduser()
    return path.resolve() if path.is_absolute() else (Path.cwd() / path).resolve()


def product_snapshot_signature(cfg) -> str:
    generation = cfg.get("generation", {})
    workflow = _workflow_path(cfg)
    parts = [
        PRODUCT_BACKGROUND_PROMPT,
        generation.get("comfyui_url", "http://127.0.0.1:8188"),
        generation.get("comfyui_image_node_id", ""),
        generation.get("comfyui_prompt_node_id", ""),
        generation.get("product_segmenter_model", "u2net"),
    ]
    if workflow.is_file():
        parts.append(hashlib.sha256(workflow.read_bytes()).hexdigest())
    return hashlib.sha256("\n".join(map(str, parts)).encode()).hexdigest()


def _segment_to_rgba(source_path: Path, cutout_path: Path, model_name: str) -> None:
    try:
        from rembg import new_session, remove
    except ImportError as exc:
        raise RuntimeError("Install local CPU segmentation with `pip install 'rembg[cpu]'`.") from exc

    with Image.open(source_path) as opened:
        source = ImageOps.exif_transpose(opened).convert("RGB")
    session = new_session(model_name)
    cutout = remove(source, session=session)
    if not isinstance(cutout, Image.Image):
        cutout = Image.open(cutout)
    cutout = cutout.convert("RGBA")
    if cutout.size != source.size:
        raise RuntimeError("The local segmenter returned a mask with unexpected dimensions.")
    cutout_path.parent.mkdir(parents=True, exist_ok=True)
    cutout.save(cutout_path)


def _composite_source_product(background_path: Path, cutout_path: Path, output_path: Path) -> None:
    """Overlay the unchanged source product on the generated background."""
    with Image.open(cutout_path) as opened:
        product = opened.convert("RGBA")
    alpha = product.getchannel("A")
    bounds = alpha.getbbox()
    if not bounds:
        raise RuntimeError("Local segmentation could not detect the product in the source image.")
    product = product.crop(bounds)
    alpha = product.getchannel("A")

    with Image.open(background_path) as opened:
        background = ImageOps.fit(opened.convert("RGB"), (768, 1344), method=Image.Resampling.LANCZOS)
    width, height = background.size

    max_size = (int(width * 0.80), int(height * 0.64))
    product.thumbnail(max_size, Image.Resampling.LANCZOS)
    alpha = product.getchannel("A")
    x = (width - product.width) // 2
    y = int(height * 0.50 - product.height / 2)

    # Add a subtle contact shadow below the cutout so it sits on the surface.
    shadow_mask = Image.new("L", (width, height), 0)
    shadow_mask.paste(alpha, (x, y + 12))
    shadow_mask = shadow_mask.filter(ImageFilter.GaussianBlur(18))
    shadow = Image.new("RGB", (width, height), (82, 66, 46))
    background.paste(shadow, (0, 0), shadow_mask.point(lambda value: value // 4))
    background.paste(product.convert("RGB"), (x, y), alpha)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    background.save(output_path, format="PNG")


def generate_product_snapshot(source_path, output_path, cfg, progress=None):
    source, output = Path(source_path).resolve(), Path(output_path).resolve()
    generation = cfg.get("generation", {})
    work_dir = output.parent.parent / "ugc_snapshot_generation"
    cutout = work_dir / "product_hero_cutout.png"
    generated_background = output.with_name(f".{output.stem}.background.png")
    temp = output.with_name(f".{output.stem}.generated{output.suffix}")
    work_dir.mkdir(parents=True, exist_ok=True)

    validate_comfyui_product_setup(cfg)
    if progress:
        progress("Separating the product locally and preserving its source pixels")
    _segment_to_rgba(source, cutout, generation.get("product_segmenter_model", "u2net"))
    if progress:
        progress("Generating a clean linen background locally; keeping jewelry unchanged")
    run_product_workflow(None, generated_background, PRODUCT_BACKGROUND_PROMPT, cfg, progress)

    if progress:
        progress("Compositing the original jewelry onto the generated background")
    _composite_source_product(generated_background, cutout, temp)

    if not temp.is_file() or temp.stat().st_size < 1024:
        raise RuntimeError("The ComfyUI workflow did not create a valid product still.")
    with Image.open(temp) as image:
        image.verify()
    temp.replace(output)
    generated_background.unlink(missing_ok=True)
    return output
