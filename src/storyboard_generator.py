"""Human-led Brazilian UGC storyboard for Kayra."""
from pathlib import Path
import json

UGC_SCENES = [
    ("HOOK_SELFIE", 3.708, "The same Brazilian female jewellery creator from the reference starts a casual selfie video at home, smiles warmly and says in Brazilian Portuguese: 'Gente, olha o que chegou!'. She holds the closed jewellery gift box at chest level and brings it naturally into frame. Medium selfie framing, handheld smartphone camera, natural window light."),
    ("UNBOXING", 3.708, "The same creator sits at a dressing table, looks down with genuine excitement and opens the jewellery box with both hands, then looks back at the phone camera. Keep her face, hair, outfit and room consistent. Natural unboxing action, believable fingers, handheld phone video."),
    ("PUTTING_ON", 3.708, "The same creator gently puts on the exact necklace from the model reference, fastening it naturally and adjusting the chain at her neckline. Show a believable continuous action, realistic hands and shoulder movement, same face and outfit, mirror-side smartphone UGC framing."),
    ("MIRROR_REVEAL", 3.708, "The same creator stands in front of a mirror wearing the exact jewellery, turns slightly to admire it, adjusts the pendant once and smiles naturally at her reflection. Casual authentic creator video, natural body movement, consistent room and outfit."),
    ("TALKING_REVIEW", 3.708, "The same creator faces the smartphone camera wearing the exact jewellery and speaks naturally in Brazilian Portuguese: 'Ficou lindo, delicado e combina com tudo.' She gestures lightly near the necklace without covering it. Authentic social-media review, realistic lip and facial movement."),
    ("DETAIL_AND_CLOSE", 3.708, "The same creator moves slightly closer to the phone camera, tilts her head and gently turns left and right so the exact necklace and earrings catch natural light, then gives a relaxed smile. Keep her identity and jewellery consistent. End on a natural confident creator pose."),
]

def create_storyboard(image_analysis, cfg):
    scenes = []
    for number, (name, duration, action) in enumerate(UGC_SCENES, start=1):
        prompt = (
            "Photorealistic continuous live-action UGC video, not a still photograph and not a slideshow. "
            "A real Brazilian female lifestyle creator filming herself on a smartphone at home. "
            "Use the supplied MODEL-WEARING-THE-JEWELLERY image as the primary first-frame and identity reference. "
            "Maintain the same woman's face, age, skin tone, hair, makeup, outfit and home environment in every scene. "
            "She is wearing the exact jewellery visible in the reference. Preserve its visible design, pendant outline, "
            "chain, stones, metal colour and proportions. Human action must be clear and continuous throughout the clip; "
            "natural blinking, breathing, facial expressions, hand movement and body movement. Natural Brazilian Portuguese "
            "creator delivery where dialogue is specified. Real smartphone exposure, subtle handheld camera movement, "
            "natural window light, realistic skin texture. No product-only shots, no floating jewellery, no CGI, no "
            "cartoon look, no frozen pose, no extra fingers, no face morphing, no captions, no watermark. "
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
        "pipeline": "ltx23_single_creator_human_led_v2",
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
