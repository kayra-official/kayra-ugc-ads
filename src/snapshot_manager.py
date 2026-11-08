"""Automatic discovery of the two original images in each product folder."""
from pathlib import Path

SNAPSHOTS = {
    "product_hero": ("product_hero.png", "Jewellery-only UGC snapshot"),
    "model_ugc": ("model_ugc.png", "Creator wearing jewellery UGC snapshot"),
}
PROMPTS = {
    "product_hero": "Create a photorealistic vertical 9:16 premium UGC product still from the supplied entire jewellery source. Keep the complete necklace and both matching earrings fully visible and in their original relative arrangement; do not crop, rearrange, rotate, redesign or alter any product detail. Blend the set naturally onto warm ivory beige textured fabric, with the necklace chain forming a relaxed V, pendant in the lower center, earrings above and to the side. Preserve exact pendant outline, stone count and positions, chain links, gold colour, scale and proportions. Soft natural window light, clean refined Brazilian jewellery campaign, no model, text or watermark.",
    "model_ugc": "Create a photorealistic vertical 9:16 Brazilian creator UGC portrait from the model wearing jewellery source. Preserve her face identity, skin tone, hair, makeup, outfit, and exact necklace and earrings. Bright natural home interior with window light and a few plants, relaxed authentic smartphone portrait, warm confident smile, hands lightly framing the neckline without covering the pendant. Show face and jewellery clearly. Preserve pendant shape, stones, chain and metal colour exactly. No text or watermark.",
}

ALIASES = {
    "product_hero": ("product_hero", "product_reference", "product", "hero"),
    "model_ugc": ("model_ugc", "model_reference", "model_with_jewellery", "model_wearing_jewellery", "model"),
}
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".bmp"}
VIDEO_EXTENSIONS = {".mp4", ".mov", ".m4v", ".webm"}

def discover_snapshots(product_dir):
    """Find product_reference and model_reference (or equivalent named sources)."""
    root = Path(product_dir)
    files = sorted((p for p in root.rglob("*") if p.is_file() and p.suffix.lower() in IMAGE_EXTENSIONS),
                   key=lambda p: (len(p.parts), p.name.lower())) if root.exists() else []
    found = {}
    for key, (canonical, _label) in SNAPSHOTS.items():
        stems = {canonical.rsplit(".", 1)[0], *ALIASES[key]}
        candidates = [p for p in files if p.stem.lower() in stems]
        if key == "product_hero" and not candidates:
            candidates = [p for p in files if p.name.lower().startswith("product_reference")]
        if candidates:
            found[key] = candidates[0].resolve()
    return found

def discover_product_video(product_dir):
    """Find a supplied product clip at the top level of the product folder."""
    root = Path(product_dir)
    clips = sorted(
        (p.resolve() for p in root.iterdir()
         if p.is_file() and p.suffix.lower() in VIDEO_EXTENSIONS),
        key=lambda p: (0 if root.name.lower() in p.stem.lower() else 1, p.name.lower()),
    ) if root.exists() else []
    if not clips:
        raise FileNotFoundError(
            f"No product video found in {root}. Add an .mp4, .mov, .m4v, or .webm clip to that product folder."
        )
    return clips[0]

def validate_snapshots(product_dir):
    found = discover_snapshots(product_dir)
    missing = [key for key in SNAPSHOTS if key not in found]
    if missing:
        raise ValueError("Each product needs two source images: jewellery-only product_reference and model_reference wearing the jewellery.")
    return {key: str(found[key]) for key in SNAPSHOTS}
