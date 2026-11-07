"""Master-image preparation for exact-product Kayra campaigns.

The supplied model reference already wears the target jewellery. For this case,
the safest product-preservation strategy is to keep that photograph as the
image-to-video conditioning image instead of asking an image model to redraw
the jewellery or pasting a flat-lay product card over the model.

This module does not claim that generated video frames are pixel-identical:
video diffusion can still alter small details. It preserves the original master
image and supplies it consistently to every scene.
"""
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
    "model-wearing-jewellery.webp", "model.jpg", "model.jpeg",
    "model.png", "model.webp",
)


def find_model_reference(product_image: str | Path) -> Optional[Path]:
    """Find a sibling model reference image in the product's input folder."""
    product = Path(product_image).expanduser().resolve()
    folder = product.parent
    by_name = {p.name.lower(): p for p in folder.iterdir()
               if p.is_file() and p.suffix.lower() in IMAGE_EXTENSIONS}
    for name in MODEL_REFERENCE_NAMES:
        candidate = by_name.get(name)
        if candidate and candidate.resolve() != product:
            return candidate.resolve()

    # Fallback: only accept an unambiguous filename beginning with model.
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
    """Copy the model master into project assets and write provenance metadata.

    If no model reference is found, required=True raises a clear actionable
    error instead of silently conditioning LTX on the flat-lay product photo.
    """
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
        "strategy": "use_original_model_photo_as_image_to_video_reference",
        "product_preservation": (
            "Original jewellery pixels are preserved in the master still. "
            "Generated video frames are model-generated and must be visually "
            "checked; exact pixel-level preservation across motion is not guaranteed."
        ),
    }
    (assets_dir / "master_reference.json").write_text(
        json.dumps(metadata, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    return metadata
