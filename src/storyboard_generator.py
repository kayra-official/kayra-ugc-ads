"""Kayra silent music-only storyboard with close-up jewellery opening scenes."""
from pathlib import Path
import json

MODEL_SCENES = [
    ("PENDANT_HERO_CLOSEUP", 3.0,
     "STATIC NECKLACE HERO SHOT. Frame only the lower neck, collarbones and upper chest "
     "from just below the chin to mid-chest. The pendant is centered and fully visible. "
     "The face, arms, wrists, hands and fingers must remain completely outside the image "
     "boundaries for the entire clip. Never generate hands entering from the bottom or sides. "
     "No touching or adjusting jewellery. Tripod-locked camera, fixed framing, no zoom, pan, "
     "tilt or reframing. Creator almost completely still; only barely perceptible breathing. "
     "No additional people or objects."),
    ("EARRING_PROFILE_CLOSEUP", 3.0,
     "STATIC EARRING HERO SHOT. Tight crop from temple to shoulder, with the visible ear "
     "and exact earring in the supplied model reference clearly visible. Keep hair away from "
     "the earring without moving it. Do not invent, redraw, replace or alter the earring. "
     "Head and camera remain still; no head turn, hands, fingers or camera movement. If the "
     "exact earring is not clearly visible in the reference, use a product-only macro scene "
     "instead of generating a substitute earring."),
    ("NECKLACE_THREE_QUARTER_CLOSEUP", 3.0,
     "Close-up from collarbone to lower face, three-quarter angle from the opposite side. "
     "Show the complete pendant, chain and upper neckline clearly. The creator holds this "
     "different pose almost still, with only subtle breathing. No touching or adjusting jewellery."),
    ("MIRROR_REVEAL", 3.0,
     "Medium close-up in a mirror, creator slowly turns her shoulders only a few degrees "
     "to reveal the jewellery from a three-quarter angle, then pauses. Keep movement minimal."),
    ("LIFESTYLE", 3.0,
     "Medium shot with the creator standing naturally in a softly lit home. She makes one "
     "small, slow head turn and a subtle closed-mouth smile. Hands remain away from jewellery."),
    ("DETAIL_AND_CLOSE", 3.0,
     "Slow, subtle camera push-in from medium close-up to close-up of the creator wearing "
     "the exact jewellery. She remains still with natural blinking and a closed-mouth smile."),
]

PRODUCT_SCENES = [
    ("PRODUCT_MACRO_PAN", 3.0,
     "Extreme macro close-up shot, 85mm macro lens look, very shallow depth of field. The camera "
     "performs an extremely slow horizontal pan across the exact jewellery item shown in the "
     "product reference. Preserve 100% of original visible design, geometric proportions, "
     "edge alignment, stone placement, chain links, metal colour and material texture. Do not "
     "redesign, invent, add, remove, bend or warp any feature. Natural studio light creates a "
     "subtle clean shimmer. Softly blurred neutral background, ultra-high detail, premium "
     "professional jewellery commercial, smooth controlled motion."),
    ("PRODUCT_DETAIL_GLINT", 3.0,
     "Extreme macro commercial detail of the exact product in the reference. Very slow horizontal "
     "camera slide across existing stones, metal surface and fine details. 85mm macro lens look, "
     "shallow depth of field, soft neutral studio background. Preserve exact geometry, stone count "
     "and positions, edge alignment, chain structure and material texture. Only natural light "
     "reflections may change; the product itself must not morph or gain new details."),
    ("PRODUCT_FULL_SET", 3.0,
     "Premium close product shot of the complete jewellery item exactly as shown in the reference. "
     "Very slow steady camera push-in with tiny horizontal drift. Keep the complete product and "
     "all visible components in frame. Preserve exact original design, shape, proportions, material, "
     "stones and colour. Soft studio lighting, restrained shimmer, neutral blurred background."),
]

SILENT = (
    "SILENT VIDEO ONLY: no voice, speech, dialogue, narration, singing, whispering, lip-sync "
    "or speech-like mouth movement. No audio generation. "
)
MODEL_BASE = (
    "Photorealistic live-action premium jewellery UGC. Use the supplied scene-specific photo "
    "as the authoritative first frame and identity reference. Preserve the same Brazilian female "
    "creator, face, skin tone, hair, makeup, outfit and exact jewellery. She is already wearing "
    "the jewellery. Never add, remove, replace, put on or alter any jewellery. Preserve pendant "
    "outline, chain, stones, metal colour, scale and proportions. "
    "VERY SLOW MOTION: nearly still product-model performance, one micro-movement at most, "
    "approximately 20 percent of normal gesture speed. No fast gestures, no sudden turns, no "
    "hand movement near jewellery, no camera shake. Hold the requested pose for most of the clip. "
    "Keep lips naturally closed. Natural soft studio/window light, realistic skin, no CGI, no "
    "cartoon, no face morphing, no extra fingers, no captions, no watermark. "
)
PRODUCT_BASE = (
    "Photorealistic premium jewellery product commercial using the supplied PRODUCT-ONLY "
    "reference as the exact source. Show only the jewellery in that image. Preserve exact design, "
    "geometry, proportions, stone count and placement, edge alignment, chain links, metal colour "
    "and texture. No morphing, warping, melting, redesign or invented features. Only camera and "
    "natural light reflections may change. Extremely slow smooth camera motion. "
)

def create_storyboard(image_analysis, cfg):
    scenes = []
    number = 1
    for name, duration, action in MODEL_SCENES:
        scenes.append({
            "scene_number": number,
            "duration_seconds": duration,
            "scene_name": name,
            "visual_description": action,
            "video_prompt": MODEL_BASE + SILENT + action,
            "reference_role": "model",
            "ugc_style": True,
            "human_action_required": False,
            "motion_speed": "ultra_slow",
            "preferred_reference_index": number,
        })
        number += 1

    for name, duration, action in PRODUCT_SCENES:
        scenes.append({
            "scene_number": number,
            "duration_seconds": duration,
            "scene_name": name,
            "visual_description": action,
            "video_prompt": PRODUCT_BASE + SILENT + action,
            "reference_role": "product",
            "ugc_style": False,
            "human_action_required": False,
            "motion_speed": "very_slow",
        })
        number += 1

    return {
        "title": "KAYRA | Silent Jewellery Close-up UGC",
        "duration_seconds": sum(x["duration_seconds"] for x in scenes) + 2.5,
        "scene_count": len(scenes),
        "pipeline": "ltx23_silent_closeup_pose_v6_reference_crop",
        "audio_policy": {
            "generated_scene_audio": False,
            "voiceover": False,
            "dialogue": False,
            "lip_sync": False,
            "final_audio": "background_music_only",
        },
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
