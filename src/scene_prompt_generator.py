"""Prompt helpers for LTX background-only generation."""


def scene_prompt(scene):
    prompt = str(scene.get("background_prompt") or scene.get("visual_description") or "").strip()
    if not prompt:
        raise ValueError(f"Scene {scene.get('scene_number', '?')} has no background prompt.")
    return (
        "Generate a moving cinematic background plate for a premium Brazilian jewellery "
        "advertisement. The jewellery product will be composited later from the real source "
        "photograph, so do not generate or depict any jewellery. "
        + prompt
    )
