# KAYRA AI VIDEO GENERATOR

A local-first application scaffold for producing a 25-scene jewellery UGC advertisement from one product image. It creates a storyboard, 25 scene prompt files, a 5×5 planning contact sheet, resumable clip jobs, an original-logo outro, FFmpeg assembly, local music mixing and export validation.

## Important hardware/model reality

This project does **not** pretend that a 16 GB MacBook Air can reliably generate 25 photorealistic one-second LTX videos with no model-specific setup. LTX-2.3 MLX command-line interfaces and memory requirements can vary by repository/version. To avoid inventing unsupported CLI flags or silently creating fake clips, the video backend is an explicit adapter contract. Until it is configured, generation stops with a clear error. The application, storyboard, contact sheet, job manifest, asset pipeline, outro and assembly code are implemented locally.

No paid API, cloud inference, or API key is used. Local Ollama vision analysis is optional; when it is unavailable, the app uses a conservative fallback and flags the lower confidence rather than claiming visual analysis occurred.

## Requirements

- macOS on Apple Silicon recommended
- Python 3.11+
- FFmpeg + ffprobe (`brew install ffmpeg`)
- Local storage for models and generated video
- Original KAYRA logo PNG and licensed local instrumental music

## Install

```bash
chmod +x install.sh run.sh
./install.sh
```

## Add assets

1. Copy the **original** transparent or high-resolution logo to `assets/logo/kayra_logo.png`.
2. Add one or more properly licensed instrumental tracks (MP3/WAV/M4A) to `assets/music/`.
3. Upload one jewellery image in the web UI.

The repository cannot supply KAYRA's private original logo. It is intentionally not fabricated. Music files are also not bundled because their licensing and redistribution permissions cannot be assumed.

## Optional local product analysis

Install Ollama locally and download a vision model compatible with your machine, e.g.:

```bash
ollama pull llava:7b
ollama serve
```

The app calls only `127.0.0.1`; no cloud endpoint is used. A 7B vision model may be slow or memory-heavy on 16 GB. Close memory-intensive apps. If Ollama is unavailable, a conservative fallback is used and recorded in the storyboard JSON.

## LTX-2.3 MLX integration (required for actual AI motion)

The project does not ship an unverified LTX CLI invocation. Configure `generation.command` in `config/settings.yaml` to point to a local executable wrapper compatible with the JSON contract below. The wrapper is called once per scene with the path to a JSON request file:

```json
{
  "scene_number": 1,
  "prompt": "scene prompt",
  "reference_image": "/absolute/path/product.png",
  "output_video": "/absolute/path/scene_01.mp4",
  "duration_seconds": 1,
  "width": 1080,
  "height": 1920,
  "fps": 24,
  "seed": 20261107,
  "model": "LTX-2.3 MLX",
  "mode": "image-to-video"
}
```

Wrapper requirements:
- Read the JSON request file passed as its sole argument.
- Use the locally installed, verified LTX-2.3 MLX implementation and its **documented** API.
- Use `reference_image` as the image-to-video conditioning image for every scene.
- Generate genuine video frames with temporal motion; do not output a still image or slideshow.
- Save a valid video to `output_video`; nonzero exit on failure.
- Respect available memory. Run sequentially; the app processes scenes in batches of five, one at a time.
- If the model requires a longer temporal window, generate the supported minimum and let FFmpeg extract the first second.

Do not point `generation.command` at a generic shell command that ignores the request JSON. A backend integration test should be run before a full 25-scene batch. Actual output quality depends on the chosen model, quantization, MLX implementation and memory footprint.

## Run

```bash
./run.sh
```

Open the local Gradio URL shown in the terminal (normally http://127.0.0.1:7860). Upload one image, generate the storyboard, then generate the video. CLI alternative:

```bash
source .venv/bin/activate
python main.py /absolute/path/to/jewellery.jpg
```

## Output

For each uploaded image, the application creates `output/<image-name>/` containing:
- `storyboard.json`
- `scene_prompts/scene_01.txt` … `scene_25.txt`
- `storyboard_contact_sheet.jpg` (planning preview, not generated video)
- `clips/scene_01.mp4` … `scene_25.mp4`
- `manifest.json` for resume/retry state
- `logo_outro.mp4`
- `picture_only.mp4`
- `KAYRA_FINAL.mp4`

The batch manifest records successful scene numbers. Re-running the CLI resumes completed clips and retries only missing/failed scenes. The UI has a one-scene regeneration control.

## Timing note

The final export is targeted at 25 seconds. The current assembler uses all 25 scene clips and reserves approximately 2.5 seconds for the logo outro by shortening the last three scene segments. For a strict 25 × 1.0s scene runtime **plus** a 2.5s outro, set `video.target_seconds` to 27.5 and update the corresponding assembly policy in `src/video_assembler.py`.

## Troubleshooting

- **No video backend configured:** configure `generation.command` as described above.
- **Missing logo:** add the original file at `assets/logo/kayra_logo.png`.
- **No music:** add a licensed local audio track to `assets/music/`.
- **Out of memory:** use a smaller supported quantization/resolution, close other applications, and process sequentially. Do not run parallel generations.
- **FFmpeg error:** run `ffmpeg -version` and `ffprobe -version`; check logs and verify input clip codecs.
- **Resume:** rerun the same image/project; completed valid clips are skipped.
- **Scene retry:** use the UI's Regenerate Scene control or remove that scene number from `manifest.json` before rerunning.

## What has and has not been validated

The package includes source-level tests and startup checks. A complete photorealistic 25-scene generation cannot be truthfully certified without the exact LTX-2.3 MLX model weights, its installed runtime/API and the user's original logo/music assets on the target Mac. The project fails clearly instead of fabricating clips when those prerequisites are absent.


## Human-led UGC update

The storyboard now creates six longer, human-action scenes featuring the same creator reference:
selfie hook, unboxing, putting on the jewellery, mirror reveal, talking review, and final detail.
All six clips use the model-wearing-jewellery image as the LTX image-to-video reference.
The flat-lay product image is retained for product analysis and visual checking, not animated as a scene.

### Authorized watermark cleanup

Original vendor images are never overwritten. If a vendor has authorized watermark removal,
create a same-dimension PNG mask beside each image. Use white pixels over the watermark and
black pixels everywhere else:

- `product_reference_watermark_mask.png`
- `model_reference_watermark_mask.png`

The app inpaints only the marked pixels and saves the result in each product's
`output/<product>/processed/` folder. If no mask exists, the source is copied unchanged.
Review every cleaned image before video generation; inpainting cannot reliably reconstruct
jewellery details hidden by a watermark.

LTX generates 89 frames per scene at 24 fps (about 3.7 seconds). The final editor combines
the six clips and the Kayra outro. One model reference image is required per product folder.
