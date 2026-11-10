# KAYRA AI VIDEO

Local-first Brazilian jewellery video workflow. The final edit contains three clips: Scene 1 is the supplied product video prepared to 10 seconds; Scene 2 is a 7-second jewellery-only move from a pendant close-up to an earring close-up, keeping the model's face out of frame; Scene 3 is a 7-second pendant close-up that zooms out to reveal the model. The 2-second Kayra logo closes the 28-second video, with background music over the final edit.

## Install and run

On Apple Silicon, install Python 3.10+, FFmpeg/ffprobe, then run:

```bash
./install.sh
./run.sh
```

Each product folder contains the product clip and two original images:

- `product_reference.jpg`: jewellery only.
- `model_reference.jpg`: creator wearing that jewellery.

The app scans each product folder automatically. It dynamically selects the source segment for a 10-second opening, removes the product clip's original audio, and slows the footage to 45% speed. Shorter source clips are slowed further rather than output below 10 seconds. Scenes 2–3 use the original model-with-jewellery photo as their reference. Scene 2 uses a deterministic close crop that begins at the neckline and glides to the earring, keeping the face out of frame; Scene 3 is unchanged and zooms out from a pendant close-up to reveal the model. The 28-second final video allocates the remaining time across Scenes 2–3 and the Kayra logo.

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
