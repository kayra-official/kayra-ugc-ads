"""Prompt helpers for LTX scene generation from prepared UGC snapshots."""


def scene_prompt(scene):
    prompt = str(scene.get("background_prompt") or scene.get("visual_description") or "").strip()
    if not prompt:
        raise ValueError(f"Scene {scene.get('scene_number', '?')} has no background prompt.")
    return "Generate a premium Brazilian jewellery UGC video scene from the supplied snapshot. " + prompt
