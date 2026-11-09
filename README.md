# KAYRA AI VIDEO

Local-first Brazilian jewellery video workflow. The final edit contains three clips: Scene 1 is the supplied product video prepared to 12 seconds; Scene 2 is a 7-second pendant-to-earrings move; Scene 3 is a 7-second pendant close-up that zooms out. The 2-second Kayra logo closes the 28-second video, with background music over the final edit.

## Install and run

On Apple Silicon, install Python 3.10+, FFmpeg/ffprobe, then run:

```bash
./install.sh
./run.sh
```

Each product folder contains the product clip and two original images:

- `product_reference.jpg`: jewellery only.
- `model_reference.jpg`: creator wearing that jewellery.

The app scans each product folder automatically. It dynamically trims each supplied product video to preserve six seconds of source footage, removes its original audio, and slows that footage to half speed for a 12-second opening. Shorter source clips are slowed further rather than trimmed below 12 seconds. Scenes 2–3 use smooth, deterministic camera moves over the original model-with-jewellery photo to preserve her identity and the exact jewelry. Scene 2 moves from the pendant to a close-up of the earrings; Scene 3 starts with a pendant close-up and slowly zooms out. Each is seven seconds. The 28-second final video uses 12 seconds for Scene 1, 14 seconds for Scenes 2–3, and the final 2 seconds for the Kayra logo.

The product clip's original soundtrack is removed before assembly. The Kayra logo video is appended after Scene 3, then the local music track is laid over the full export.

The Gradio screen has one product dropdown, including an **All products** option, and one **Generate UGC video** button. Storyboard creation runs automatically as part of video generation. The results area displays only the finished video or videos. The CLI does the same:

```bash
python main.py /absolute/path/to/input/PRODUCT_NAME/product_reference.jpg
```

Outputs are written to `output/PRODUCT_NAME/`, including the storyboard, scene clips, and final video.

## Local model and hardware

The model scene generator uses the local LTX-2.3 MLX checkout with Metal access on Apple Silicon. Product scenes use FFmpeg motion interpolation and no image-generation backend.

Processing is sequential. LTX generation uses low-RAM settings for Apple Silicon.

## Branding and audio

The existing `assets/branding/kayra_logo.mp4` and local music remain in the project. The model photo is cleaned into a processed copy when a watermark mask or local automatic remover is available; the original input is preserved. Product jewellery images are left untouched by default to protect fine details.
