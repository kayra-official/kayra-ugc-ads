import argparse
import yaml
from pathlib import Path
from src.common import load_settings
from src.snapshot_manager import discover_product_video, discover_snapshots
from src.snapshot_generator import ensure_ugc_snapshots
from src.video_assembler import assemble_video, prepare_product_clip, fit_model_scene_durations
from src.storyboard_generator import create_storyboard, save_storyboard
from src.storyboard_renderer import render_contact_sheet
from src.batch_processor import process_all
from src.music_manager import find_music, mix_music
from src.quality_checker import check_video

CONFIG_PATH = Path("config/settings.yaml")

with open(CONFIG_PATH, "r", encoding="utf-8") as f:
    cfg = yaml.safe_load(f)

def run(image):
    cfg = load_settings()
    image = Path(image).expanduser().resolve()
    product_folder = image.parent.parent if image.parent.name == "product_images" else image.parent
    project = Path(cfg["app"]["output_dir"]) / product_folder.name
    project.mkdir(parents=True, exist_ok=True)
    product_clip = discover_product_video(product_folder)
    source_refs = discover_snapshots(product_folder)
    if "model_ugc" not in source_refs:
        raise FileNotFoundError(f"Model-with-jewellery image not found under {product_folder}.")
    refs_model = ensure_ugc_snapshots(
        product_folder, project, cfg, lambda n, total, message: print(message), roles=("model_ugc",)
    )
    refs = {"product_hero": str(image), "model_ugc": refs_model["model_ugc"]}
    clips = project / "clips"
    print("[1/5] Slowing the supplied product video and removing its audio...")
    prepare_product_clip(product_clip, clips / "scene_01.mp4", cfg)
    print("[2/5] Generating model-with-jewellery scenes 5–6...")
    board = create_storyboard({"source": str(image)}, cfg, refs)
    board["scenes"] = [scene for scene in board["scenes"] if scene["scene_number"] in (5, 6)]
    board["scene_count"] = 6
    board["pipeline"] = "product_clip_scenes_1_4_model_ugc_scenes_5_8_v2"
    board["duration_seconds"] = cfg["video"]["target_seconds"]
    save_storyboard(board, project)
    render_contact_sheet(board, refs["product_hero"], project/"storyboard_contact_sheet.jpg")
    process_all(board, refs["product_hero"], project, cfg, lambda n,total,msg: print(msg))
    if any(not (clips/f"scene_{i:02d}.mp4").exists() for i in (1, 5, 6)):
        print("Some scenes remain. Run again to continue.")
        return None
    print("[3/5] Loading Kayra logo outro...")
    outro = Path(cfg["branding"]["outro_video"])
    if not outro.is_absolute():
        outro = Path(__file__).resolve().parent / outro
    if not outro.exists():
        raise FileNotFoundError(f"Kayra outro not found: {outro}")
    print("[4/5] Assembling the product clip, two model scenes and Kayra logo...")
    clip_durations = fit_model_scene_durations(
        clips / "scene_01.mp4", outro, cfg["video"]["target_seconds"], cfg["video"]["fps"],
        scene_numbers=(5, 6), outro_seconds=cfg["video"]["outro_seconds"],
    )
    assembled = assemble_video(
        clips,
        outro,
        project / "picture_only.mp4",
        cfg,
        scene_count=6,
        scene_numbers=(1, 5, 6),
        clip_durations=clip_durations,
    )
    print("[5/5] Adding background music and checking the export...")
    final = mix_music(
        assembled,
        find_music(cfg),
        project / "KAYRA_FINAL.mp4",
        cfg
    )
    report = check_video(final, None, cfg["video"]["width"], cfg["video"]["height"])
    print(f"SUCCESS: {final}\\n{report}")
    return final

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("image", help="Product reference image; matching model_reference image must be beside it")
    run(ap.parse_args().image)
