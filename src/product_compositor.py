"""Master-image preparation for exact-product Kayra campaigns."""
from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Optional
from PIL import Image, ImageOps

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}

MODEL_REFERENCE_NAMES = (
    "model_reference.jpg", "model_reference.jpeg", "model_reference.png",
    "model_reference.webp", "model-wearing-jewellery.jpg",
    "model-wearing-jewellery.jpeg", "model-wearing-jewellery.png",
    "model-wearing-jewellery.webp", "model.jpg", "model.jpeg",
    "model.png", "model.webp",
)

def find_model_reference(product_image: str | Path) -> Optional[Path]:
    product = Path(product_image).expanduser().resolve()
    folder = product.parent
    by_name = {p.name.lower(): p for p in folder.iterdir()
               if p.is_file() and p.suffix.lower() in IMAGE_EXTENSIONS}
    for name in MODEL_REFERENCE_NAMES:
        candidate = by_name.get(name)
        if candidate and candidate.resolve() != product:
            return candidate.resolve()
    candidates = sorted(
        (p for p in folder.iterdir()
         if p.is_file() and p.suffix.lower() in IMAGE_EXTENSIONS
         and p.resolve() != product
         and p.stem.lower().startswith(("model_", "model-", "model "))),
        key=lambda p: p.name.lower(),
    )
    return candidates[0].resolve() if len(candidates) == 1 else None

def prepare_master_reference(
    product_image: str | Path,
    project_dir: str | Path,
    *,
    required: bool = True,
) -> dict:
    product = Path(product_image).expanduser().resolve()
    if not product.is_file():
        raise FileNotFoundError(f"Product reference not found: {product}")
    model = find_model_reference(product)
    if model is None:
        if required:
            raise FileNotFoundError(
                "No model reference image found beside the product image. "
                "Add model_reference.jpg (or model-wearing-jewellery.jpg) "
                "to the same input/<product-folder>/ directory."
            )
        model = product

    assets_dir = Path(project_dir).expanduser().resolve() / "assets"
    assets_dir.mkdir(parents=True, exist_ok=True)
    master_path = assets_dir / f"master_model_reference{model.suffix.lower()}"
    if model != master_path:
        shutil.copy2(model, master_path)

    metadata = {
        "product_reference": str(product),
        "model_reference_source": str(model),
        "master_reference": str(master_path),
        "strategy": "original_model_photo_with_scene_specific_framing",
        "product_preservation": (
            "Original jewellery pixels are preserved in the master still. "
            "Generated video frames are model-generated; exact pixel-level "
            "preservation across motion is not guaranteed."
        ),
    }
    (assets_dir / "master_reference.json").write_text(
        json.dumps(metadata, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    return metadata

def create_scene_model_references(master_image, output_dir):
    """Create alternate crops for scene framing. Does not invent new poses."""
    master = Path(master_image).resolve()
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    specs = [
        (1.00, 0.50, 0.50), (0.88, 0.52, 0.56), (0.78, 0.50, 0.46),
        (0.92, 0.60, 0.50), (0.96, 0.42, 0.54), (0.72, 0.50, 0.43),
    ]
    results = []
    with Image.open(master) as source:
        image = ImageOps.exif_transpose(source).convert("RGB")
        w, h = image.size
        for idx, (scale, cx, cy) in enumerate(specs, 1):
            cw, ch = int(w * scale), int(h * scale)
            left = max(0, min(w - cw, int(cx * w - cw / 2)))
            top = max(0, min(h - ch, int(cy * h - ch / 2)))
            dest = output_dir / f"model_scene_{idx:02d}.jpg"
            image.crop((left, top, left + cw, top + ch)).save(dest, quality=95)
            results.append(dest)
    return results
