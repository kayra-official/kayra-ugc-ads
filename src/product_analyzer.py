from pathlib import Path
import base64, json, urllib.request
from PIL import Image

def analyze_product(image_path, cfg):
    p = Path(image_path)
    if not p.exists(): raise FileNotFoundError(f"Product image not found: {p}")
    try:
        with Image.open(p) as im:
            im.verify()
        with Image.open(p) as im:
            if im.width < 128 or im.height < 128: raise ValueError("Image is too small; use at least 128x128 pixels.")
            im.convert("RGB")
    except Exception as e:
        raise ValueError(f"Invalid product image: {e}") from e

    # Local Ollama vision model; no cloud calls. If unavailable, produce conservative
    # image metadata and instruct prompts not to infer unseen details.
    model = cfg["analysis"]["ollama_model"]
    url = cfg["analysis"]["ollama_url"].rstrip("/") + "/api/generate"
    prompt = ("Inspect this jewellery product image. Return concise JSON only with "
              "category, visible_material_or_finish, stones, shape_and_design, "
              "distinctive_details, confidence, and visual_constraints. "
              "Do not guess hidden details. Preserve exact product identity.")
    try:
        raw = p.read_bytes()
        payload = {"model": model, "prompt": prompt, "images":[base64.b64encode(raw).decode()],
                   "stream":False, "format":"json"}
        req = urllib.request.Request(url, data=json.dumps(payload).encode(),
                                     headers={"Content-Type":"application/json"})
        with urllib.request.urlopen(req, timeout=cfg["analysis"]["timeout_seconds"]) as r:
            data = json.loads(r.read().decode())
        result = json.loads(data.get("response","{}"))
        result["analysis_backend"] = f"ollama:{model}"
        return result
    except Exception as e:
        return {
            "category":"jewellery item (not confidently classified)",
            "visible_material_or_finish":"describe only visible finish; do not assume metal",
            "stones":"preserve only visibly identifiable stones",
            "shape_and_design":"match the uploaded reference exactly",
            "distinctive_details":"use the reference image as the sole authority",
            "confidence":"low; local vision model unavailable",
            "visual_constraints":"Do not invent, redesign, recolour, add or remove product elements.",
            "analysis_backend":"conservative fallback",
            "analysis_note":f"Local Ollama vision analysis unavailable: {e}"
        }
