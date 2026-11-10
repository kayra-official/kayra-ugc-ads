"""Three-clip silent jewellery storyboard: product Scene 1 and model Scenes 2–3."""
from pathlib import Path
import json

SCENES = [
    (2, "MODEL_PENDANT_TO_EARRINGS", 7.0, "Begin already tightly framed on the neckline and exact pendant; never show a full portrait or zoom in from a wide model shot. Slowly glide upward to a tight detail of the matching earring. Keep the creator's face, eyes, nose and mouth outside the frame throughout. Only the jewellery and the minimum neck or ear area needed to show it may appear. Preserve the exact pendant, chain, earrings, stones, materials and proportions from the reference. No face reveal, transitions, cuts, duplicate jewellery or redesign."),
    (3, "MODEL_PENDANT_ZOOM_OUT", 7.0, "Start with a close-up of the exact pendant, then slowly zoom out to reveal the creator wearing the jewellery. Elegant ultra-slow motion, nearly still pose; only barely visible breathing, a tiny smooth natural head movement and one natural blink. Keep shoulders and hands still. Preserve the exact pendant, chain and earrings from the reference in every frame; no redesign or morphing."),
]
SILENT = "Silent video only: no speech, narration, dialogue, singing, lip-sync, speech-like mouth movement, or generated audio. Photorealistic live action, vertical 9:16, cinematic natural light, no CGI/cartoon, no captions or watermark. Preserve source identity and jewellery exactly; no redesign, morphing, adding or removing details. "

def create_storyboard(image_analysis, cfg, references=None):
    references = references or {}
    scenes = []
    for number, name, duration, action in SCENES:
        scenes.append({"scene_number": number, "duration_seconds": duration, "scene_name": name,
                       "visual_description": action, "video_prompt": SILENT + action,
                       "camera_movement": action.split(";")[0], "reference_role": "model_ugc",
                       "reference_image": references.get("model_ugc", ""),
                       "reference_note": "Original model-with-jewellery image",
                       "ugc_style": True})
    return {"title": "KAYRA | Brazilian Jewellery UGC", "duration_seconds": cfg["video"]["target_seconds"],
            "scene_count": len(SCENES), "pipeline": "ltx23_product_clip_two_model_scenes_v5", "audio_policy": {"generated_scene_audio": False, "final_audio": "background_music_only"},
            "product_analysis": image_analysis, "references": references, "scenes": scenes}

def save_storyboard(board, out_dir):
    p = Path(out_dir); p.mkdir(parents=True, exist_ok=True)
    target = p / "storyboard.json"
    target.write_text(json.dumps(board, indent=2, ensure_ascii=False), encoding="utf-8")
    prompts = p / "scene_prompts"; prompts.mkdir(exist_ok=True)
    for scene in board["scenes"]:
        (prompts / f"scene_{scene['scene_number']:02d}.txt").write_text(scene["video_prompt"], encoding="utf-8")
    return target
