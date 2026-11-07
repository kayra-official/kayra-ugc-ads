import argparse
import yaml
from pathlib import Path
from src.common import load_settings
from src.product_analyzer import analyze_product
from src.storyboard_generator import create_storyboard, save_storyboard
from src.storyboard_renderer import render_contact_sheet
from src.watermark_preprocessor import preprocess_product_images
from src.product_compositor import prepare_master_reference
from src.batch_processor import process_all
from src.video_assembler import assemble_video
from src.music_manager import find_music, mix_music
from src.quality_checker import check_video

CONFIG_PATH = Path("config/settings.yaml")

with open(CONFIG_PATH, "r", encoding="utf-8") as f:
    cfg = yaml.safe_load(f)

def run(image):
    cfg = load_settings()
    image = Path(image).expanduser().resolve()
    project = Path(cfg["app"]["output_dir"]) / image.parent.name
    project.mkdir(parents=True, exist_ok=True)
    print("[1/7] Preprocessing authorized images...")
    processed = preprocess_product_images(image, project)
    print("[2/7] Product analysis...")
    analysis = analyze_product(processed["product_reference"], cfg)
    master = prepare_master_reference(image, project, required=True)
    master["master_reference"] = processed["model_reference"]
    master["product_reference"] = processed["product_reference"]
    board = create_storyboard(analysis, cfg)
    board.update({"master_reference": master["master_reference"], "product_reference": master["product_reference"]})
    save_storyboard(board, project)
    render_contact_sheet(board, master["product_reference"], project/"storyboard_contact_sheet.jpg", model_image_path=master["master_reference"])
    print("[3/7] Generating six continuous creator-led UGC clips...")
    clips = process_all(board, master["master_reference"], project, cfg, lambda n,total,msg: print(msg))
    if any(not (Path(clips)/f"scene_{i:02d}.mp4").exists() for i in range(1, len(board["scenes"])+1)):
        print("Some scenes remain. Run again to resume.")
        return None
    print("[4/7] Loading Kayra logo outro...")
    outro = Path(cfg["branding"]["outro_video"])
    if not outro.is_absolute():
        outro = Path(__file__).resolve().parent / outro
    if not outro.exists():
        raise FileNotFoundError(f"Kayra outro not found: {outro}")
    print("[5/7] Assembling silent video...")
    assembled = assemble_video(
        clips,
        outro,
        project / "picture_only.mp4",
        cfg
    )
    print("[6/7] Adding music and quality checks...")
    final = mix_music(
        assembled,
        find_music(cfg),
        project / "KAYRA_FINAL.mp4",
        cfg
    )
    report = check_video(final, cfg["video"]["target_seconds"], cfg["video"]["width"], cfg["video"]["height"])
    print(f"SUCCESS: {final}\\n{report}")
    return final

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("image", help="Product reference image; matching model_reference image must be beside it")
    run(ap.parse_args().image)
