from pathlib import Path

import gradio as gr

from src.common import load_settings
from src.video_assembler import assemble_video, prepare_product_clip, fit_model_scene_durations
from src.music_manager import find_music, mix_music
from src.quality_checker import check_video
from src.snapshot_manager import discover_product_video, discover_snapshots
from src.snapshot_generator import ensure_ugc_snapshots
from src.storyboard_generator import create_storyboard, save_storyboard
from src.storyboard_renderer import render_contact_sheet
from src.batch_processor import process_all

cfg = load_settings()
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}
ALL_PRODUCTS = "__all_products__"


def input_root():
    root = Path(cfg["app"].get("input_dir", "input")).expanduser()
    return (root if root.is_absolute() else Path.cwd() / root).resolve()


def output_root():
    root = Path(cfg["app"].get("output_dir", "output")).expanduser()
    return (root if root.is_absolute() else Path.cwd() / root).resolve()


def discover_products():
    """Return one named product entry for every usable product input folder."""
    root = input_root()
    root.mkdir(parents=True, exist_ok=True)
    preferred = (
        "product_reference.jpg", "product_reference.jpeg", "product_reference.png",
        "product_reference.webp", "product.jpg", "product.jpeg", "product.png",
        "product.webp", "reference.jpg", "reference.png", "main.jpg", "main.png",
    )
    products = []
    for folder in sorted((p for p in root.iterdir() if p.is_dir()), key=lambda p: p.name.lower()):
        scan_dir = folder / "product_images"
        scan_dir = scan_dir if scan_dir.is_dir() else folder
        images = [
            p for p in scan_dir.iterdir()
            if p.is_file() and p.suffix.lower() in IMAGE_EXTENSIONS
            and not p.stem.lower().startswith(("model_reference", "model_", "model-"))
        ]
        if not images:
            continue
        by_name = {p.name.lower(): p for p in images}
        chosen = next((by_name[name] for name in preferred if name in by_name), None)
        if chosen is None:
            chosen = sorted(images, key=lambda p: p.name.lower())[0]
        products.append((folder.name, str(chosen.resolve())))
    return products


def product_project(image_path):
    image = Path(image_path).expanduser().resolve()
    try:
        relative = image.relative_to(input_root())
        name = relative.parts[0] if len(relative.parts) > 1 else image.stem
    except ValueError:
        name = image.parent.name or image.stem
    return output_root() / name


def product_folder(image_path):
    image = Path(image_path).expanduser().resolve()
    try:
        return input_root() / image.relative_to(input_root()).parts[0]
    except (ValueError, IndexError):
        return image.parent


def dropdown_choices(products=None):
    products = discover_products() if products is None else products
    return [("All products", ALL_PRODUCTS), *products]


def refresh_products(current_value=None):
    choices = dropdown_choices()
    values = [value for _, value in choices]
    selected = current_value if current_value in values else (values[1] if len(values) > 1 else ALL_PRODUCTS)
    return gr.update(choices=choices, value=selected)


def generate_one(image_path, progress, start, span):
    product_name = Path(image_path).resolve().relative_to(input_root()).parts[0]
    project = product_project(image_path)
    project.mkdir(parents=True, exist_ok=True)

    def stage(fraction, message):
        progress(start + span * fraction, desc=f"{product_name} · {message}")

    product_clip = discover_product_video(product_folder(image_path))
    source_refs = discover_snapshots(product_folder(image_path))
    if "model_ugc" not in source_refs:
        raise FileNotFoundError(f"Model-with-jewellery image not found under {product_folder(image_path)}.")
    model_refs = ensure_ugc_snapshots(
        product_folder(image_path), project, cfg,
        lambda n, total, message: stage(0.08 + 0.10 * n / max(total, 1), message),
        roles=("model_ugc",),
    )
    refs = {"product_hero": str(Path(image_path).resolve()), "model_ugc": model_refs["model_ugc"]}
    clips = project / "clips"
    stage(0.04, "Slowing the supplied product video and removing its audio")
    prepare_product_clip(product_clip, clips / "scene_01.mp4", cfg)
    stage(0.20, "Preparing model-with-jewelry scenes 2–3")
    board = create_storyboard({"source": str(Path(image_path).resolve())}, cfg, refs)
    board["scenes"] = [scene for scene in board["scenes"] if scene["scene_number"] in (2, 3)]
    board["scene_count"] = 2
    board["pipeline"] = "product_clip_scene_1_model_ugc_scenes_2_3_v4"
    board["duration_seconds"] = cfg["video"]["target_seconds"]
    save_storyboard(board, project)
    render_contact_sheet(board, refs["product_hero"], project / "storyboard_contact_sheet.jpg")
    process_all(
        board, refs["product_hero"], project, cfg,
        lambda n, total, message: stage(0.20 + 0.55 * n / max(total, 1), message),
    )
    missing = [i for i in (1, 2, 3) if not (clips / f"scene_{i:02d}.mp4").is_file()]
    if missing:
        raise RuntimeError(f"{product_name}: scenes still missing: {', '.join(map(str, missing))}.")

    outro = Path(cfg["branding"]["outro_video"])
    if not outro.is_absolute():
        outro = Path(__file__).resolve().parent / outro
    if not outro.is_file():
        raise FileNotFoundError(f"Kayra outro not found: {outro}")
    stage(0.84, "Appending the Kayra logo video")
    clip_durations = fit_model_scene_durations(
        clips / "scene_01.mp4", outro, cfg["video"]["target_seconds"], cfg["video"]["fps"],
        scene_numbers=(2, 3), outro_seconds=cfg["video"]["outro_seconds"],
    )
    assembled = assemble_video(clips, outro, project / "picture_only.mp4", cfg,
        scene_count=3, scene_numbers=(1, 2, 3),
                               clip_durations=clip_durations)
    stage(0.90, "Adding background music")
    final_video = mix_music(assembled, find_music(cfg), project / "KAYRA_FINAL.mp4", cfg)
    check_video(final_video, None, cfg["video"]["width"], cfg["video"]["height"])
    return str(final_video), product_name


def generate(selection, progress=gr.Progress()):
    products = discover_products()
    if not products:
        raise gr.Error("No products found. Add a product reference image and product video to a folder under input/.")

    selected = products if selection == ALL_PRODUCTS else [item for item in products if item[1] == selection]
    if not selected:
        raise gr.Error("That product is no longer in the input folder. Refresh the page and choose again.")

    results = []
    total = len(selected)
    for index, (product_name, image_path) in enumerate(selected):
        start, span = index / total, 1 / total
        try:
            results.append(generate_one(image_path, progress, start, span))
        except Exception as exc:
            raise gr.Error(f"{product_name}: {exc}")
    progress(1, desc="All selected videos are ready")
    return results


CSS = """
:root { --kayra-ink: #1b2823; --kayra-muted: #6d7771; --kayra-accent: #168b68; }
body { background: #f6f7f5; }
.gradio-container { max-width: 1050px !important; margin: 0 auto !important; }
#kayra-shell { padding: 34px 28px 26px; }
#kayra-title { color: var(--kayra-ink); font-size: 34px; font-weight: 650; letter-spacing: -.04em; }
#kayra-subtitle { color: var(--kayra-muted); font-size: 15px; margin-top: 7px; }
#kayra-controls { margin-top: 30px; padding: 22px; border: 1px solid #e7ebe7; border-radius: 18px; background: white; }
#kayra-generate { min-height: 52px; border-radius: 12px; font-weight: 650; }
#kayra-results { margin-top: 26px; }
@media (max-width: 640px) { #kayra-shell { padding: 24px 14px; } #kayra-title { font-size: 28px; } }
"""


initial_choices = dropdown_choices()
initial_value = initial_choices[1][1] if len(initial_choices) > 1 else ALL_PRODUCTS

with gr.Blocks(title="KAYRA · UGC Studio") as demo:
    with gr.Column(elem_id="kayra-shell"):
        gr.Markdown("# KAYRA UGC Studio", elem_id="kayra-title")
        gr.Markdown("Choose one product or create videos for every product in your library.", elem_id="kayra-subtitle")
        with gr.Column(elem_id="kayra-controls"):
            product_choice = gr.Dropdown(
                choices=initial_choices,
                value=initial_value,
                label="Product",
                interactive=True,
                filterable=True,
            )
            generate_btn = gr.Button("Generate UGC video", variant="primary", elem_id="kayra-generate")
        results = gr.Gallery(
            label="Your videos",
            columns=2,
            rows=1,
            height=520,
            object_fit="contain",
            allow_preview=True,
            buttons=["download", "fullscreen"],
            elem_id="kayra-results",
        )

    demo.load(refresh_products, inputs=product_choice, outputs=product_choice)
    generate_btn.click(generate, inputs=product_choice, outputs=results)


if __name__ == "__main__":
    demo.launch(
        server_name="127.0.0.1", server_port=7860,
        theme=gr.themes.Soft(primary_hue="emerald"), css=CSS,
    )
