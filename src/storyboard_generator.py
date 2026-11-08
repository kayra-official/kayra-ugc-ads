"""Six-scene silent jewellery storyboard using two model clips."""
from pathlib import Path
import json

SCENES = [
    ("COMPLETE_SET_HERO", 3.25, "product_hero", "Hero view of the complete jewellery set on a refined neutral surface. Slow controlled push-in; keep every piece visible."),
    ("NECKLACE_PENDANT_MACRO", 3.25, "product_hero", "Macro glide across the exact necklace and pendant, preserving pendant shape, stones, chain, metal colour and proportions."),
    ("EARRING_CLOSEUP", 3.25, "product_hero", "Macro detail of the exact earrings and their stones and metal finish. Subtle natural light glint, slow camera slide."),
    ("JEWELLERY_SPARKLE_DETAIL", 3.25, "product_hero", "Slow cinematic detail pass over the exact jewellery set; only realistic reflections shift, product design remains unchanged."),
    ("MODEL_PENDANT_TO_EARRINGS", 7.0, "model_ugc", "One continuous elegant shot of the same creator wearing the exact jewellery in the reference. Begin framed on the pendant, slowly push closer, then smoothly move the camera upward to a close-up of the visible matching earrings. Camera movement only; keep the woman still and do not turn her head. Preserve the exact pendant, chain, earrings, stones, face and outfit. No transitions, cuts, duplicate jewellery or redesign."),
    ("MODEL_PENDANT_ZOOM_OUT", 7.0, "model_ugc", "Start with a close-up of the exact pendant, then slowly zoom out to reveal the creator wearing the jewellery. Elegant ultra-slow motion, nearly still pose; only barely visible breathing and one natural blink. Keep shoulders and hands still; after the zoom out, keep the camera still. Preserve the exact pendant, chain and earrings from the reference."),
]
SILENT = "Silent video only: no speech, narration, dialogue, singing, lip-sync, speech-like mouth movement, or generated audio. Photorealistic live action, vertical 9:16, cinematic natural light, no CGI/cartoon, no captions or watermark. Preserve source identity and jewellery exactly; no redesign, morphing, adding or removing details. "

def create_storyboard(image_analysis, cfg, references=None):
    references = references or {}
    scenes = []
    for i, (name, duration, role, action) in enumerate(SCENES, 1):
        scenes.append({"scene_number": i, "duration_seconds": duration, "scene_name": name,
                       "visual_description": action, "video_prompt": SILENT + action,
                       "camera_movement": action.split(";")[0], "reference_role": role,
                       "reference_image": references.get(role, ""),
                       "reference_note": "Product UGC snapshot" if role == "product_hero" else "Creator UGC snapshot",
                       "ugc_style": role != "product_hero"})
    return {"title": "KAYRA | Brazilian Jewellery UGC", "duration_seconds": cfg["video"]["target_seconds"],
            "scene_count": len(SCENES), "pipeline": "ltx23_product_clip_two_model_scenes_v3", "audio_policy": {"generated_scene_audio": False, "final_audio": "background_music_only"},
            "product_analysis": image_analysis, "references": references, "scenes": scenes}

def save_storyboard(board, out_dir):
    p = Path(out_dir); p.mkdir(parents=True, exist_ok=True)
    target = p / "storyboard.json"
    target.write_text(json.dumps(board, indent=2, ensure_ascii=False), encoding="utf-8")
    prompts = p / "scene_prompts"; prompts.mkdir(exist_ok=True)
    for scene in board["scenes"]:
        (prompts / f"scene_{scene['scene_number']:02d}.txt").write_text(scene["video_prompt"], encoding="utf-8")
    return target
