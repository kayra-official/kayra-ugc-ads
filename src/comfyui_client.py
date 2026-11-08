"""Small client for submitting a saved API-format workflow to local ComfyUI."""
from __future__ import annotations

import json
import time
import uuid
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


class ComfyUIError(RuntimeError):
    pass


def _request(url, *, data=None, headers=None, timeout=30):
    request = Request(url, data=data, headers=headers or {})
    try:
        with urlopen(request, timeout=timeout) as response:
            return response.read()
    except (HTTPError, URLError, TimeoutError) as exc:
        raise ComfyUIError(f"ComfyUI request failed for {url}: {exc}") from exc


def _upload_image(base_url: str, path: Path) -> dict:
    boundary = f"----Kayra{uuid.uuid4().hex}"
    image_bytes = path.read_bytes()
    body = b"".join([
        f"--{boundary}\r\nContent-Disposition: form-data; name=\"image\"; filename=\"{path.name}\"\r\n".encode(),
        b"Content-Type: image/png\r\n\r\n", image_bytes, b"\r\n",
        f"--{boundary}\r\nContent-Disposition: form-data; name=\"type\"\r\n\r\ninput\r\n".encode(),
        f"--{boundary}\r\nContent-Disposition: form-data; name=\"overwrite\"\r\n\r\ntrue\r\n".encode(),
        f"--{boundary}--\r\n".encode(),
    ])
    response = _request(
        f"{base_url.rstrip('/')}/upload/image", data=body,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"}, timeout=120,
    )
    return json.loads(response)


def _find_node(workflow: dict, node_id, purpose: str) -> dict:
    node_id = str(node_id)
    if node_id not in workflow:
        raise ComfyUIError(f"Configured {purpose} node {node_id!r} is not in the API workflow.")
    return workflow[node_id]


def validate_comfyui_product_setup(cfg) -> Path:
    generation = cfg.get("generation", {})
    base_url = generation.get("comfyui_url", "http://127.0.0.1:8188").rstrip("/")
    workflow_path = Path(generation.get("comfyui_product_workflow", "assets/workflows/product_snapshot_api.json"))
    if not workflow_path.is_absolute():
        workflow_path = Path.cwd() / workflow_path
    if not workflow_path.is_file():
        raise ComfyUIError(
            f"ComfyUI API workflow not found: {workflow_path}. Restore the project's product_snapshot_api.json workflow."
        )
    _request(f"{base_url}/system_stats", timeout=5)
    return workflow_path


def _wait_for_image(base_url: str, prompt_id: str, timeout_seconds: int, output_node_id=None, progress=None) -> dict:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        data = json.loads(_request(f"{base_url.rstrip('/')}/history/{prompt_id}", timeout=30))
        entry = data.get(prompt_id)
        if entry:
            status = entry.get("status", {})
            if status.get("status_str") == "error" or status.get("completed") is False and status.get("messages"):
                raise ComfyUIError(f"ComfyUI workflow failed: {status.get('messages', status)}")
            outputs = entry.get("outputs", {})
            for node_id, output in outputs.items():
                if output_node_id and str(node_id) != str(output_node_id):
                    continue
                images = output.get("images", [])
                if images:
                    return images[0]
        if progress:
            progress("Waiting for local ComfyUI image generation")
        time.sleep(2)
    raise ComfyUIError(f"ComfyUI did not finish within {timeout_seconds} seconds.")


def run_product_workflow(cutout_image, output_image, prompt, cfg, progress=None):
    generation = cfg.get("generation", {})
    base_url = generation.get("comfyui_url", "http://127.0.0.1:8188").rstrip("/")
    workflow_path = validate_comfyui_product_setup(cfg)
    workflow = json.loads(workflow_path.read_text(encoding="utf-8"))
    image_node_id = generation.get("comfyui_image_node_id", "")
    image_node = _find_node(workflow, image_node_id, "input image") if image_node_id else None
    prompt_node = _find_node(workflow, generation.get("comfyui_prompt_node_id", ""), "positive prompt")
    image_input = generation.get("comfyui_image_input", "image")
    prompt_input = generation.get("comfyui_prompt_input", "text")
    if image_node is not None:
        uploaded = _upload_image(base_url, Path(cutout_image))
        image_node.setdefault("inputs", {})[image_input] = uploaded["name"]
    prompt_node.setdefault("inputs", {})[prompt_input] = prompt
    output_node_id = generation.get("comfyui_output_node_id")
    if not output_node_id:
        output_node_id = next((
            node_id for node_id, node in workflow.items()
            if node.get("class_type") == "SaveImage"
        ), None)
    if not output_node_id:
        raise ComfyUIError("The configured API workflow must include a SaveImage node.")

    payload = json.dumps({"prompt": workflow, "client_id": str(uuid.uuid4())}).encode()
    queued = json.loads(_request(
        f"{base_url}/prompt", data=payload,
        headers={"Content-Type": "application/json"}, timeout=30,
    ))
    if queued.get("error"):
        raise ComfyUIError(f"ComfyUI rejected the workflow: {queued['error']}")
    image_meta = _wait_for_image(
        base_url, queued["prompt_id"],
        int(generation.get("comfyui_timeout_seconds", 3600)), output_node_id, progress,
    )
    query = urlencode({
        "filename": image_meta["filename"],
        "subfolder": image_meta.get("subfolder", ""),
        "type": image_meta.get("type", "output"),
    })
    image_bytes = _request(f"{base_url}/view?{query}", timeout=120)
    target = Path(output_image)
    target.parent.mkdir(parents=True, exist_ok=True)
    temp = target.with_name(f".{target.stem}.generated{target.suffix}")
    temp.write_bytes(image_bytes)
    temp.replace(target)
    return target
