# KAYRA AI VIDEO

Local-first Brazilian jewellery video workflow. Scene 1 uses the supplied product video after a four-second trim, slowed to half speed and capped at 12 seconds. Existing LTX-2.3 MLX model-with-jewelry clips are center-trimmed for seconds 12–25, followed by the three-second Kayra logo outro at 25–28. Background music is added to the final edit.

## Install and run

On Apple Silicon, install Python 3.10+, FFmpeg/ffprobe, then run:

```bash
./install.sh
./run.sh
```

Each product folder contains the product clip and two original images:

- `product_reference.jpg`: jewellery only.
- `model_reference.jpg`: creator wearing that jewellery.

The app scans each product folder automatically. It dynamically trims each supplied product video to preserve six seconds of source footage, removes its original audio, and slows that footage to half speed for a 12-second opening. Shorter source clips are slowed further rather than trimmed below 12 seconds. The model scenes use the original model-with-jewellery input. Scene 5 moves from the pendant to a close-up of the earrings; Scene 6 keeps the previous necklace-close-up prompt. Each is slowed to and trimmed at seven seconds. The 28-second final video uses 12 seconds for the product clip, 14 seconds for Scenes 5–6, and the final 2 seconds for the Kayra logo.

The product clip's original soundtrack is removed before assembly. The Kayra logo video is appended after scene 8, then the local music track is laid over the full export.

The Gradio screen has one product dropdown, including an **All products** option, and one **Generate UGC video** button. Storyboard creation runs automatically as part of video generation. The results area displays only the finished video or videos. The CLI does the same:

```bash
python main.py /absolute/path/to/input/PRODUCT_NAME/product_reference.jpg
```

Outputs are written to `output/PRODUCT_NAME/`, including the model UGC snapshot, storyboard, scene clips, and final video.

## Local model and hardware

The model scene generator uses the local LTX-2.3 MLX checkout with Metal access on Apple Silicon. Product scenes use FFmpeg motion interpolation and no image-generation backend.

Processing is sequential. LTX generation uses low-RAM settings for Apple Silicon.

## Branding and audio

The existing `assets/branding/kayra_logo.mp4` and local music remain in the project. Use images and music you have permission to use. The project does not remove watermarks.
