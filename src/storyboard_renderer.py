from PIL import Image, ImageDraw, ImageFont
from pathlib import Path
import textwrap

def render_contact_sheet(board, product_image_path, output_path, model_image_path=None):
    W, H = 1500, 1200
    canvas = Image.new("RGB", (W, H), (18, 38, 31))
    draw = ImageDraw.Draw(canvas)
    try:
        font = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial.ttf", 18)
    except Exception:
        font = ImageFont.load_default()
    for idx, scene in enumerate(board["scenes"]):
        x, y = (idx % 3) * 500, (idx // 3) * 400
        draw.rectangle((x+5, y+5, x+494, y+394), outline=(190, 155, 85), width=2)
        draw.text((x+18, y+14), f"SCENE {scene['scene_number']:02d} · {scene['scene_name']}", fill=(236, 207, 143), font=font)
        source = Path(scene.get("reference_image") or product_image_path)
        if source.is_file():
            thumb = Image.open(source).convert("RGB")
            thumb.thumbnail((250, 210))
            canvas.paste(thumb, (x + (500-thumb.width)//2, y+45))
            if scene.get("reference_note", "").startswith("Portrait reused"):
                draw.rectangle((x+135, y+218, x+365, y+244), fill=(38, 58, 49))
                draw.text((x+145, y+221), "Creator identity reference", fill=(236, 207, 143), font=font)
        else:
            draw.rectangle((x+125, y+55, x+375, y+245), fill=(38, 58, 49), outline=(190, 155, 85), width=1)
            missing_name = source.name or "reference image"
            label = f"Missing: {missing_name}"
            draw.text((x+145, y+130), label, fill="white", font=font)
        lines = textwrap.wrap(scene["visual_description"], width=55)[:5]
        for j, line in enumerate(lines):
            draw.text((x+18, y+270+j*22), line, fill="white", font=font)
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    canvas.save(output_path)
    return output_path
