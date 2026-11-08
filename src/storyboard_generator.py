"""Silent music-only Kayra UGC storyboard: creator scenes + product macro scenes."""
from pathlib import Path
import json

MODEL_SCENES = [
    ("HOOK_SELFIE", 3.0,
     "The creator holds a calm medium close-up pose, then makes one very slow, subtle head turn "
     "and a gentle closed-mouth smile. Her hands remain below the necklace."),
    ("PENDANT_REVEAL", 3.0,
     "The creator slowly lowers her gaze toward the pendant and returns her gaze to camera. "
     "Her hands stay away from the chain; the necklace remains fully visible and unchanged."),
    ("JEWELLERY_DETAIL", 3.0,
     "A slow, small head turn lets the earrings catch the window light. Keep shoulders relaxed "
     "and hands still, away from all jewellery."),
    ("MIRROR_REVEAL", 3.0,
     "The creator slowly rotates her upper body only a few degrees toward a three-quarter angle, "
     "then pauses. Keep the necklace and earrings unchanged and visible."),
    ("LIFESTYLE", 3.0,
     "The creator makes one gentle, slow shoulder movement and a subtle closed-mouth smile. "
     "No touching the necklace or earrings."),
    ("DETAIL_AND_CLOSE", 3.0,
     "A gradual, very slow camera push-in toward the creator's face and jewellery. She remains "
     "almost still, with only natural blinking and a soft closed-mouth smile."),
]

PRODUCT_SCENES = [
    ("PRODUCT_MACRO_PAN", 3.0,
     "Extreme macro close-up shot, 85mm macro lens look, very shallow depth of field. The camera "
     "performs an extremely slow horizontal pan across the exact jewellery item shown in the "
     "product reference. Preserve 100% of the original visible design, geometric proportions, "
     "edge alignment, stone placement, chain links, metal colour and material texture. Do not "
     "redesign, invent, add, remove, bend or warp any feature. Natural studio light creates a "
     "subtle clean shimmer on the existing facets. Softly blurred neutral background, ultra-high "
     "detail, premium professional jewellery commercial, smooth controlled motion."),
    ("PRODUCT_DETAIL_GLINT", 3.0,
     "Extreme macro commercial detail of the exact product in the reference image. Very slow "
     "horizontal camera slide across the existing stones, metal surface and fine details. 85mm "
     "macro lens look, shallow depth of field, soft neutral studio background. Preserve exact "
     "original geometry, proportions, stone count and positions, edge alignment, chain structure "
     "and material texture. Only natural light reflections may change; the product itself must "
     "not morph, rotate unnaturally, melt or gain new details."),
    ("PRODUCT_FULL_SET", 3.0,
     "Premium macro-to-close product shot of the complete jewellery item exactly as shown in the "
     "reference. Very slow, steady camera push-in with a tiny horizontal drift. Keep the full "
     "product composition and every visible component in frame. Preserve exact original design, "
     "shape, proportions, material, stones and colour. Soft studio lighting, restrained shimmer, "
     "neutral softly blurred background, luxury catalogue commercial quality."),
]

SILENT_RULES = (
    "SILENT VIDEO ONLY: absolutely no voice, speech, dialogue, narration, singing, whispering, "
    "lip-sync or speech-like mouth movement. For model scenes, keep lips naturally closed; "
    "subtle closed-mouth smiles only. No audio generation. "
)

MODEL_BASE = (
    "Photorealistic continuous live-action UGC video, not a still image or slideshow. "
    "Use the supplied model-wearing-the-exact-jewellery image as the identity and first-frame "
    "reference. Preserve the same Brazilian female creator, face, age, skin tone, hair, makeup, "
    "outfit and environment. She is already wearing the exact jewellery. Never add, remove, "
    "replace, put on, or alter any jewellery. Preserve pendant outline, chain, stones, metal "
    "colour, scale and proportions. MOTION MUST BE SLOW, CALM AND NATURAL: one small deliberate "
    "action across the entire clip, approximately half the speed of an ordinary social video; "
    "no fast gestures, sudden turns, quick hand movements, exaggerated expressions or rapid "
    "camera motion. Mostly steady camera, gentle natural blinking and breathing. "
    "No jewellery box, gift box or unboxing. No CGI, cartoon look, face morphing, extra fingers, "
    "captions or watermark. "
)

PRODUCT_BASE = (
    "Photorealistic premium jewellery product commercial, image-to-video. Use the supplied "
    "PRODUCT-ONLY reference image as the authoritative source. Show only the exact jewellery "
    "visible in that image; no model, hands, packaging, extra pieces or invented components. "
    "Preserve original product design, exact geometry, proportions, edge alignment, stone count "
    "and placement, chain links, metal colour and material texture. No morphing, warping, melting, "
    "redesign or feature substitution. Only camera movement and natural light reflections may "
    "change. Motion is extremely slow, smooth and controlled. "
)

def create_storyboard(image_analysis, cfg):
    scenes = []
    number = 1

    for name, duration, action in MODEL_SCENES:
        prompt = MODEL_BASE + SILENT_RULES + action
        scenes.append({
            "scene_number": number,
            "duration_seconds": duration,
            "scene_name": name,
            "visual_description": action,
            "video_prompt": prompt,
            "reference_role": "model",
            "ugc_style": True,
            "human_action_required": True,
            "motion_speed": "slow",
        })
        number += 1

    for name, duration, action in PRODUCT_SCENES:
        prompt = PRODUCT_BASE + SILENT_RULES + action
        scenes.append({
            "scene_number": number,
            "duration_seconds": duration,
            "scene_name": name,
            "visual_description": action,
            "video_prompt": prompt,
            "reference_role": "product",
            "ugc_style": False,
            "human_action_required": False,
            "motion_speed": "very_slow",
        })
        number += 1

    return {
        "title": "KAYRA | Silent Brazilian UGC + Product Macro",
        "duration_seconds": sum(s["duration_seconds"] for s in scenes) + 2.5,
        "scene_count": len(scenes),
        "pipeline": "ltx23_silent_music_only_macro_v4",
        "audio_policy": {
            "generated_scene_audio": False,
            "voiceover": False,
            "dialogue": False,
            "lip_sync": False,
            "final_audio": "background_music_only",
        },
        "creative_direction": cfg.get("storyboard", {}).get(
            "style", "Silent creator showcase with premium macro product shots"
        ),
        "product_analysis": image_analysis,
        "model_consistency": True,
        "product_reference_required": True,
        "product_scene_count": len(PRODUCT_SCENES),
        "model_scene_count": len(MODEL_SCENES),
        "scenes": scenes,
    }

def save_storyboard(board, out_dir):
    p = Path(out_dir)
    p.mkdir(parents=True, exist_ok=True)
    target = p / "storyboard.json"
    target.write_text(json.dumps(board, indent=2, ensure_ascii=False), encoding="utf-8")
    prompts = p / "scene_prompts"
    prompts.mkdir(exist_ok=True)
    for scene in board["scenes"]:
        (prompts / f"scene_{scene['scene_number']:02d}.txt").write_text(
            scene["video_prompt"], encoding="utf-8"
        )
    return target
