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
    source = model_image_path or product_image_path
    thumb = Image.open(source).convert("RGB")
    thumb.thumbnail((250, 210))
    for idx, scene in enumerate(board["scenes"]):
        x, y = (idx % 3) * 500, (idx // 3) * 400
        draw.rectangle((x+5, y+5, x+494, y+394), outline=(190, 155, 85), width=2)
        draw.text((x+18, y+14), f"SCENE {scene['scene_number']:02d} · {scene['scene_name']}", fill=(236, 207, 143), font=font)
        canvas.paste(thumb, (x + (500-thumb.width)//2, y+45))
        lines = textwrap.wrap(scene["visual_description"], width=55)[:5]
        for j, line in enumerate(lines):
            draw.text((x+18, y+270+j*22), line, fill="white", font=font)
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    canvas.save(output_path)
    return output_path
