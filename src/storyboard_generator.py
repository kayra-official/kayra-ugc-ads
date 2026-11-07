"""Human-led Brazilian UGC storyboard for Kayra."""
from pathlib import Path
import json

UGC_SCENES = [
    ("HOOK_SELFIE", 3.708,
     "The same Brazilian female faces the smartphone camera with a gentle closed-mouth smile, "
     "then lightly touches the necklace she is already wearing. Silent visual performance; "
     "natural selfie framing and subtle handheld movement."),
    ("PENDANT_REVEAL", 3.708,
     "The same Brazilian female looks down briefly at the exact pendant already resting on her chest, "
     "then looks back toward the camera and gently adjusts the chain without removing it. "
     "Keep the jewellery clearly visible."),
    ("JEWELLERY_DETAIL", 3.708,
     "The same Brazilian female makes a small, graceful head turn so the earrings catch the natural window "
     "light, then lightly touches the necklace. Preserve the exact jewellery already being worn."),
    ("MIRROR_REVEAL", 3.708,
     "The same Brazilian female turns slightly in front of a mirror to show how the exact necklace and earrings "
     "look when worn. She admires the look with a subtle closed-mouth smile."),
    ("LIFESTYLE", 3.708,
     "The same Brazilian female makes a natural, relaxed movement in her home, gently turns her head and "
     "shoulders, and briefly touches the pendant to showcase the jewellery. Silent, natural "
     "expression with lips at rest."),
    ("DETAIL_AND_CLOSE", 3.708,
     "A slightly closer smartphone framing shows the exact necklace and earrings. The same Brazilian female "
     "gently turns left and right so the jewellery catches natural light, then finishes with "
     "a relaxed closed-mouth smile."),
]
def create_storyboard(image_analysis, cfg):
    scenes = []
    for number, (name, duration, action) in enumerate(UGC_SCENES, start=1):
        prompt = (
            "Photorealistic continuous live-action UGC video, not a still photograph or slideshow. "
            "A real Brazilian female lifestyle creator at home, filmed on a smartphone. "
            "Use the supplied MODEL-WEARING-THE-JEWELLERY image as the authoritative first-frame "
            "and identity reference. Maintain the same woman's face, age, skin tone, hair, makeup, "
            "outfit and home environment in every scene. She is already wearing the exact jewellery "
            "shown in the reference. Preserve its precise design, pendant outline, chain, stones, "
            "metal colour, scale and proportions. "
            "SILENT VISUAL PERFORMANCE ONLY: no speech, no dialogue, no voice, no narration, "
            "no singing, no whispering, no lip-sync and no speech-like mouth movement. Keep her "
            "lips naturally closed and at rest throughout; subtle closed-mouth smiles are allowed. "
            "No jewellery box, no gift box, no unboxing, no additional or alternative jewellery, "
            "no changing product, no removing jewellery and no putting jewellery on. "
            "Show the jewellery she is already wearing through gentle natural movement, small "
            "head and shoulder turns, and subtle hand gestures that do not cover the product. "
            "Natural blinking and breathing, realistic skin texture, natural window light, "
            "subtle handheld smartphone movement. No CGI, no cartoon look, no frozen pose, "
            "no extra fingers, no face morphing, no captions and no watermark. "
            + action
        )
        scenes.append({
            "scene_number": number, "duration_seconds": duration,
            "scene_name": name, "visual_description": action,
            "video_prompt": prompt, "reference_role": "model",
            "ugc_style": True, "human_action_required": True,
        })
    return {
        "title": "KAYRA | Brazilian Creator UGC",
        "duration_seconds": 25, "scene_count": len(scenes),
        "pipeline": "ltx23_silent_music_only_ugc_v3",
        "audio_policy": {"generated_scene_audio": False, "voiceover": False, "dialogue": False, "lip_sync": False, "final_audio": "background_music_only"},
        "creative_direction": cfg.get("storyboard", {}).get("style", "Authentic Brazilian UGC"),
        "product_analysis": image_analysis,
        "model_consistency": True, "product_reference_required": True,
        "product_scene_count": 0, "model_scene_count": len(scenes),
        "scenes": scenes,
    }

def save_storyboard(board, out_dir):
    p = Path(out_dir); p.mkdir(parents=True, exist_ok=True)
    target = p / "storyboard.json"
    target.write_text(json.dumps(board, indent=2, ensure_ascii=False), encoding="utf-8")
    prompts = p / "scene_prompts"; prompts.mkdir(exist_ok=True)
    for scene in board["scenes"]:
        (prompts / f"scene_{scene['scene_number']:02d}.txt").write_text(scene["video_prompt"], encoding="utf-8")
    return target
