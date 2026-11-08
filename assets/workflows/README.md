# Product snapshot workflow

`product_snapshot_api.json` is a ready-to-queue ComfyUI API workflow built from standard nodes. It expects the local `sdxl_lightning_4step.safetensors` checkpoint, generates an empty linen background from the positive prompt at node `3`, and saves the background through node `7`.

The app segments the supplier photo locally with `rembg`, generates only the empty background with local ComfyUI, then composites the original jewelry pixels over it. This prevents diffusion from redrawing or redesigning the product. It does not send product images to Google or another hosted image API.

Keep ComfyUI running at the URL in `config/settings.yaml`, and make sure the checkpoint filename matches one in ComfyUI's `models/checkpoints` directory. This workflow uses standard ComfyUI nodes and does not require IC-Light custom nodes.
