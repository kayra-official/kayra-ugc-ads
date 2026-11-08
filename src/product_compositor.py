"""Master model and product reference preparation for Kayra."""
from __future__ import annotations
import json
import shutil
from pathlib import Path
from typing import Optional

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
MODEL_REFERENCE_NAMES = (
    "model_reference.jpg", "model_reference.jpeg", "model_reference.png",
    "model_reference.webp", "model-wearing-jewellery.jpg",
    "model-wearing-jewellery.jpeg", "model-wearing-jewellery.png",
    "model-wearing-jewellery.webp", "model.jpg", "model.jpeg", "model.png", "model.webp",
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
        (p for p in folder.iterdir() if p.is_file()
         and p.suffix.lower() in IMAGE_EXTENSIONS and p.resolve() != product
         and p.stem.lower().startswith(("model_", "model-", "model "))),
        key=lambda p: p.name.lower())
    return candidates[0].resolve() if len(candidates) == 1 else None

def prepare_master_reference(product_image, project_dir, *, required=True):
    product = Path(product_image).expanduser().resolve()
    if not product.is_file():
        raise FileNotFoundError(f"Product reference not found: {product}")
    model = find_model_reference(product)
    if model is None:
        if required:
            raise FileNotFoundError(
                "No model reference image found beside product image. Add model_reference.jpg."
            )
        model = product
    assets = Path(project_dir).expanduser().resolve() / "assets"
    assets.mkdir(parents=True, exist_ok=True)
    master_path = assets / f"master_model_reference{model.suffix.lower()}"
    if model != master_path:
        shutil.copy2(model, master_path)
    meta = {
        "product_reference": str(product),
        "model_reference_source": str(model),
        "master_reference": str(master_path),
        "model_reference_folder": str(model.parent),
        "strategy": "scene_specific_model_reference_photos_then_close_crop_fallback",
        "note": "Crops change framing only; genuine pose variation requires multiple supplied model photos."
    }
    (assets / "master_reference.json").write_text(
        json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")
    return meta
