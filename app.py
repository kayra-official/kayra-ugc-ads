import hashlib
import json
from pathlib import Path
import gradio as gr

from src.common import load_settings
from src.product_analyzer import analyze_product
from src.storyboard_generator import create_storyboard, save_storyboard
from src.storyboard_renderer import render_contact_sheet
from src.batch_processor import process_all
from src.video_assembler import assemble_video
from src.music_manager import find_music, mix_music
from src.quality_checker import check_video
from src.product_compositor import prepare_master_reference
from src.watermark_preprocessor import preprocess_product_images

cfg = load_settings()
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}


def input_root():
    root = Path(cfg["app"].get("input_dir", "input")).expanduser()
    return (root if root.is_absolute() else Path.cwd() / root).resolve()


def output_root():
    root = Path(cfg["app"].get("output_dir", "output")).expanduser()
    return (root if root.is_absolute() else Path.cwd() / root).resolve()


def discover_products():
    """Discover input/<product-folder>/ and choose its product reference image."""
    root = input_root()
    root.mkdir(parents=True, exist_ok=True)
    preferred = (
        "product_reference.jpg", "product_reference.jpeg",
        "product_reference.png", "product_reference.webp",
        "product.jpg", "product.jpeg", "product.png", "product.webp",
        "reference.jpg", "reference.png", "main.jpg", "main.png",
    )
    products = []
    for folder in sorted((p for p in root.iterdir() if p.is_dir()), key=lambda p: p.name.lower()):
        images = [
            p for p in folder.iterdir()
            if p.is_file() and p.suffix.lower() in IMAGE_EXTENSIONS
            and not p.stem.lower().startswith(("model_reference", "model_", "model-"))
        ]
        if not images:
            continue
        by_name = {p.name.lower(): p for p in images}
        chosen = next((by_name[name] for name in preferred if name in by_name), None)
        if chosen is None:
            chosen = sorted(images, key=lambda p: p.name.lower())[0]
        products.append((f"{folder.name} · {chosen.name}", str(chosen.resolve())))
    return products


def product_project(image_path):
    image = Path(image_path).expanduser().resolve()
    try:
        relative = image.relative_to(input_root())
        name = relative.parts[0] if len(relative.parts) > 1 else image.stem
    except ValueError:
        name = image.parent.name or image.stem
    return output_root() / name


def load_selected_product(image_path):
    if image_path and Path(image_path).is_file():
        return str(Path(image_path).resolve())
    return None


def refresh_products(current_value=None):
    products = discover_products()
    values = [value for _, value in products]
    selected = current_value if current_value in values else (values[0] if values else None)
    return gr.update(choices=products, value=selected), selected

def resolve_original_product_image(gradio_image):
    """Map Gradio's temporary image copy to its original input file."""
    if not gradio_image:
        raise FileNotFoundError("No product image selected.")

    selected = Path(gradio_image).resolve()

    def file_hash(path):
        h = hashlib.sha256()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(1024 * 1024), b""):
                h.update(chunk)
        return h.hexdigest()

    if not selected.is_file():
        raise FileNotFoundError(f"Selected image not found: {selected}")

    selected_hash = file_hash(selected)
    input_root = Path("input").resolve()

    for candidate in input_root.rglob("*"):
        if (candidate.is_file()
                and candidate.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"}
                and candidate.name.lower() == selected.name.lower()
                and file_hash(candidate) == selected_hash):
            return candidate.resolve()

    raise FileNotFoundError(
        f"Could not locate the original product image in {input_root}: "
        f"{selected.name}"
    )

def storyboard(image):
    if not image:
        raise gr.Error("No product found. Add a product folder under input/ and click REFRESH PRODUCTS.")
    p = resolve_original_product_image(image)
    project = product_project(p)
    project.mkdir(parents=True, exist_ok=True)
    processed = preprocess_product_images(p, project)
    analysis = analyze_product(processed["product_reference"], cfg)
    master = prepare_master_reference(p, project, required=True)
    master["master_reference"] = processed["model_reference"]
    master["product_reference"] = processed["product_reference"]
    board = create_storyboard(analysis, cfg)
    board["master_reference"] = master["master_reference"]
    board["product_reference"] = master["product_reference"]
    save_storyboard(board, project)
    sheet = render_contact_sheet(board, master["product_reference"], project / "storyboard_contact_sheet.jpg", model_image_path=master["master_reference"])
    return str(project / "storyboard.json"), str(sheet), str(project)


def generate(image, progress=gr.Progress()):
    if not image:
        raise gr.Error("No product selected. Add a product folder under input/ and click REFRESH PRODUCTS.")
    p = resolve_original_product_image(image)
    project = product_project(p)
    project.mkdir(parents=True, exist_ok=True)
    try:
        progress(0.03, desc="Image preprocessing")
        processed = preprocess_product_images(p, project)
        progress(0.08, desc="Product analysis")
        analysis = analyze_product(processed["product_reference"], cfg)
        master = prepare_master_reference(p, project, required=True)
        master["master_reference"] = processed["model_reference"]
        master["product_reference"] = processed["product_reference"]
        board = create_storyboard(analysis, cfg)
        board["master_reference"] = master["master_reference"]
        board["product_reference"] = master["product_reference"]
        save_storyboard(board, project)
        render_contact_sheet(board, master["product_reference"], project / "storyboard_contact_sheet.jpg", model_image_path=master["master_reference"])
        progress(0.12, desc="Storyboard generated; master model reference prepared")
        # The scene references/order changed. Never reuse old all-model clips for product scenes.
        manifest_path = project / "manifest.json"
        old_state = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else {}
        if old_state.get("pipeline") != board["pipeline"]:
            old_state = {"pipeline": board["pipeline"], "completed": [], "failed": {}}
            manifest_path.write_text(json.dumps(old_state, indent=2), encoding="utf-8")
        clips = process_all(
            board, master["master_reference"], project, cfg,
            lambda n, t, m: progress(0.12 + 0.65 * n / max(t, 1), desc=m)
        )
        if len(list(clips.glob("scene_*.mp4"))) < len(board["scenes"]):
            return (
                str(project / "storyboard.json"),
                str(project / "storyboard_contact_sheet.jpg"),
                None,
                "First batch completed. Generate the remaining scenes before final assembly."
            )
        progress(0.80, desc="Logo integration")
        outro = Path(cfg["branding"]["outro_video"])
        if not outro.is_absolute():
            outro = Path(__file__).resolve().parent / outro

        if not outro.exists():
            raise FileNotFoundError(f"Kayra outro not found: {outro}")
        progress(0.87, desc="Video assembly")
        assembled = assemble_video(clips, outro, project / "picture_only.mp4", cfg)
        progress(0.94, desc="Music integration")
        final_video = mix_music(assembled, find_music(cfg), project / "KAYRA_FINAL.mp4", cfg)
        report = check_video(final_video, 25, 1080, 1920)
        progress(1, desc="Complete")
        return str(project / "storyboard.json"), str(project / "storyboard_contact_sheet.jpg"), str(final_video), report
    except Exception as exc:
        raise gr.Error(str(exc))


def regen(image, scene_no):
    if not image:
        raise gr.Error("Select a product folder first.")
    p = resolve_original_product_image(image)
    project = product_project(p)
    board_file = project / "storyboard.json"
    if not board_file.exists():
        raise gr.Error("Generate the storyboard first.")
    board = json.loads(board_file.read_text(encoding="utf-8"))
    number = int(scene_no)
    if number < 1 or number > len(board["scenes"]):
        raise gr.Error(f"Scene number must be between 1 and {len(board['scenes'])}.")
    from src.video_generator import generate_scene
    master = board.get("master_reference")
    if not master or not Path(master).is_file():
        raise gr.Error("Master model reference is missing. Generate the storyboard again.")
    out = project / "clips" / f"scene_{number:02d}.mp4"
    out.parent.mkdir(parents=True, exist_ok=True)
    generate_scene(
        board["scenes"][number - 1], master, out, cfg,
        product_reference=board.get("product_reference", str(p))
    )
    return str(out)


initial_products = discover_products()
initial_value = initial_products[0][1] if initial_products else None

with gr.Blocks(title="KAYRA AI VIDEO GENERATOR", theme=gr.themes.Soft(primary_hue="emerald")) as demo:
    gr.Markdown(
        "# KAYRA AI VIDEO GENERATOR\n"
        "Automatically discovers product folders in `input/`. Select a product, "
        "generate six human-led Brazilian creator scenes with LTX-2.3 MLX.\\n\\n"
        "Authorized watermark cleanup: add same-size `product_reference_watermark_mask.png` "
        "and/or `model_reference_watermark_mask.png` beside the source image. White marks "
        "the watermark area; black protects the rest. Originals are never overwritten."
    )
    with gr.Row():
        product_choice = gr.Dropdown(
            choices=initial_products, value=initial_value,
            label="Discovered products", interactive=True, scale=5
        )
        refresh_btn = gr.Button("REFRESH PRODUCTS", variant="secondary", scale=1)

    image = gr.Image(
        value=initial_value, type="filepath",
        label="Selected product reference", sources=[], interactive=False
    )
    with gr.Row():
        sb = gr.Button("GENERATE STORYBOARD", variant="secondary")
        go = gr.Button("GENERATE UGC VIDEO", variant="primary")

    project = gr.Textbox(label="Project folder", interactive=False)
    storyboard_file = gr.File(label="Storyboard JSON")
    sheet = gr.Image(label="5 × 5 storyboard contact sheet")
    final = gr.Video(label="Final KAYRA advertisement")
    report = gr.JSON(label="Quality report")

    product_choice.change(load_selected_product, product_choice, image)
    refresh_btn.click(refresh_products, product_choice, [product_choice, image])
    sb.click(storyboard, image, [storyboard_file, sheet, project])
    go.click(generate, image, [storyboard_file, sheet, final, report])

    gr.Markdown("### Regenerate one scene")
    scene = gr.Number(value=1, minimum=1, maximum=6, precision=0, label="Scene number")
    clip = gr.Video(label="Regenerated clip")
    regen_btn = gr.Button("REGENERATE SCENE")
    regen_btn.click(regen, [image, scene], clip)

    if not initial_products:
        gr.Markdown(
            "**No products discovered yet.** Create folders such as "
            "`input/product_001/product_reference.jpg`, then click **REFRESH PRODUCTS**."
        )

if __name__ == "__main__":
    demo.launch(server_name="127.0.0.1", server_port=7860)
