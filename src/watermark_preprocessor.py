"""Free local watermark preprocessing for KAYRA.

- Uses DeMark's automatic detector when installed.
- Keeps source images unchanged.
- Writes cleaned copies into output/<product>/processed/.
- Optional same-size manual masks remain supported as a fallback.
- Product image cleanup can be disabled to protect fine jewellery details.

Install in the project's .venv:
    pip install demark
"""
from pathlib import Path
import json
import shutil

from PIL import Image
import numpy as np
import cv2

from .product_compositor import find_model_reference

try:
    from demark import remove_watermark
except Exception:
    remove_watermark = None


def _valid_image(path: Path):
    with Image.open(path) as im:
        im.verify()
    with Image.open(path) as im:
        return im.size, im.mode


def _manual_mask_cleanup(source: Path, mask_path: Path, destination: Path):
    image = cv2.imread(str(source), cv2.IMREAD_COLOR)
    mask = cv2.imread(str(mask_path), cv2.IMREAD_GRAYSCALE)
    if image is None or mask is None:
        raise ValueError(f"Cannot read image or watermark mask for {source.name}")
    if mask.shape != image.shape[:2]:
        raise ValueError(f"Watermark mask must match {source.name} dimensions exactly.")
    if not np.any(mask):
        raise ValueError(f"Watermark mask for {source.name} is empty.")
    cleaned = cv2.inpaint(image, mask, 5, cv2.INPAINT_TELEA)
    if not cv2.imwrite(str(destination), cleaned):
        raise OSError(f"Could not write cleaned image: {destination}")
    return {"method": "manual_mask_opencv", "cleaned": True}


def _auto_cleanup(source: Path, destination: Path):
    if remove_watermark is None:
        raise RuntimeError(
            "Automatic watermark removal is not installed. Activate the project .venv "
            "and run: pip install demark"
        )

    result = remove_watermark(
        input_path=str(source),
        output_path=str(destination),
        method="auto",
    )

    if not getattr(result, "success", False) or not destination.exists():
        raise RuntimeError(f"Automatic watermark removal failed for {source.name}: {result}")

    original_size, _ = _valid_image(source)
    cleaned_size, _ = _valid_image(destination)
    if original_size != cleaned_size:
        destination.unlink(missing_ok=True)
        raise RuntimeError(
            f"Automatic cleanup changed image dimensions for {source.name}; "
            "original retained and cleaned result rejected."
        )

    data = getattr(result, "data", {}) or {}
    return {
        "method": data.get("method", "demark_auto"),
        "elapsed": data.get("elapsed"),
        "cleaned": True,
    }


def _prepare_one(source: Path, mask_path: Path, destination: Path, *,
                 automatic: bool = True, require_cleanup: bool = True):
    destination.parent.mkdir(parents=True, exist_ok=True)
    if not source.exists():
        raise FileNotFoundError(f"Reference image not found: {source}")

    if mask_path.exists():
        details = _manual_mask_cleanup(source, mask_path, destination)
        return {
            "source": str(source), "processed": str(destination),
            "watermark_mask": str(mask_path), **details,
        }

    if automatic:
        details = _auto_cleanup(source, destination)
        return {
            "source": str(source), "processed": str(destination),
            "watermark_mask": None, **details,
        }

    if require_cleanup:
        raise RuntimeError(f"No cleanup method enabled for {source.name}")

    shutil.copy2(source, destination)
    return {
        "source": str(source), "processed": str(destination),
        "watermark_mask": None, "cleaned": False, "method": "original_copy",
    }


def preprocess_product_images(product_image, project_dir):
    product = Path(product_image).expanduser().resolve()
    model = find_model_reference(product)
    if model is None:
        raise FileNotFoundError(
            "Add model_reference.jpg beside the product image; "
            "human-led UGC requires a consistent creator reference."
        )

    out = Path(project_dir) / "processed"
    out.mkdir(parents=True, exist_ok=True)
    product_out = out / f"product_reference{product.suffix.lower()}"
    model_out = out / f"model_reference{model.suffix.lower()}"

    product_mask = product.with_name("product_reference_watermark_mask.png")
    model_mask = model.with_name("model_reference_watermark_mask.png")

    # Clean the model reference automatically. Leave the product image
    # untouched by default to avoid damaging stones, chains, or fine edges.
    # If a product mask is explicitly supplied, apply that exact mask.
    model_result = _prepare_one(
        model, model_mask, model_out, automatic=True, require_cleanup=True
    )
    if product_mask.exists():
        product_result = _prepare_one(
            product, product_mask, product_out, automatic=False, require_cleanup=True
        )
    else:
        shutil.copy2(product, product_out)
        product_result = {
            "source": str(product), "processed": str(product_out),
            "watermark_mask": None, "cleaned": False,
            "method": "original_preserved_for_jewellery_detail",
        }

    report = {
        "mode": "free_local_automatic",
        "automatic_engine": "DeMark" if remove_watermark is not None else "not_installed",
        "authorization_required": True,
        "originals_modified": False,
        "product_image_policy": "preserve_original_unless_explicit_mask_provided",
        "images": [product_result, model_result],
    }
    (out / "preprocessing_report.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8"
    )
    return {
        "product_reference": str(product_out),
        "model_reference": str(model_out),
        "report": report,
    }
