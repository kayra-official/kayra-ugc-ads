"""Authorized watermark cleanup using user-supplied masks; originals are never modified.

Place a same-size PNG mask next to an input image:
  product_reference_watermark_mask.png
  model_reference_watermark_mask.png
White pixels mark watermark areas to inpaint; black pixels are preserved.
"""
from pathlib import Path
import shutil
from PIL import Image
import numpy as np
import cv2
from .product_compositor import find_model_reference

def _prepare_one(source: Path, mask_path: Path, destination: Path):
    destination.parent.mkdir(parents=True, exist_ok=True)
    if mask_path.exists():
        image = cv2.imread(str(source), cv2.IMREAD_COLOR)
        mask = cv2.imread(str(mask_path), cv2.IMREAD_GRAYSCALE)
        if image is None or mask is None:
            raise ValueError(f"Cannot read image or watermark mask for {source.name}")
        if mask.shape != image.shape[:2]:
            raise ValueError(f"Watermark mask must match {source.name} dimensions exactly.")
        cleaned = cv2.inpaint(image, mask, 5, cv2.INPAINT_TELEA)
        if not np.any(mask):
            raise ValueError(f"Watermark mask for {source.name} is empty.")
        cv2.imwrite(str(destination), cleaned)
        return {"source": str(source), "processed": str(destination), "watermark_mask": str(mask_path), "cleaned": True}
    shutil.copy2(source, destination)
    return {"source": str(source), "processed": str(destination), "watermark_mask": None, "cleaned": False}

def preprocess_product_images(product_image, project_dir):
    product = Path(product_image).expanduser().resolve()
    model = find_model_reference(product)
    if model is None:
        raise FileNotFoundError("Add model_reference.jpg beside the product image; human-led UGC requires a consistent creator reference.")
    out = Path(project_dir) / "processed"
    product_out = out / f"product_reference{product.suffix.lower()}"
    model_out = out / f"model_reference{model.suffix.lower()}"
    product_mask = product.with_name("product_reference_watermark_mask.png")
    model_mask = model.with_name("model_reference_watermark_mask.png")
    results = [
        _prepare_one(product, product_mask, product_out),
        _prepare_one(model, model_mask, model_out),
    ]
    report = {"authorization_required": True, "originals_modified": False, "images": results}
    (out / "preprocessing_report.json").write_text(__import__("json").dumps(report, indent=2), encoding="utf-8")
    return {"product_reference": str(product_out), "model_reference": str(model_out), "report": report}
