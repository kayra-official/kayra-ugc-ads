
#!/usr/bin/env python3
"""JSON adapter between Kayra and LTX-2.3 MLX."""

import yaml
import json
import sys
import subprocess
from pathlib import Path


def main():
    if len(sys.argv) < 2:
        raise SystemExit("Usage: ltx_mlx_wrapper.py request.json")

    request_path = Path(sys.argv[1]).expanduser().resolve()
    request = json.loads(request_path.read_text(encoding="utf-8"))

    ltx_dir = Path.home() / "Documents/GitHub/ltx-2-mlx"

    reference = Path(request["reference_image"]).expanduser().resolve()
    output = Path(request["output_video"]).expanduser().resolve()

    output.parent.mkdir(parents=True, exist_ok=True)

    prompt = request["prompt"]
    fps = int(request.get("fps", 24))
    seed = int(request.get("seed", 20261107))

    project_dir = Path(__file__).resolve().parent.parent
    settings = yaml.safe_load(
        (project_dir / "config/settings.yaml").read_text()
    )
    generation = settings["generation"]

    model = generation["model"]
    width = int(generation["render_width"])
    height = int(generation["render_height"])
    frames = int(generation.get("frames", 25))

    command = [
        "uv", "run",
        "--package", "ltx-pipelines-mlx",
        "ltx-2-mlx", "generate",
        "--prompt", prompt,
        "--output", str(output),
        "--model", model,
        "--image", str(reference),
        "--width", str(width),
        "--height", str(height),
        "--frames", str(frames),
        "--frame-rate", str(fps),
        "--seed", str(seed),
        "--distilled",
        "--low-ram",
        "--no-audio",
    ]

    print("Starting LTX-2.3 MLX...")
    print("Reference:", reference)
    print("Output:", output)
    print("Resolution:", width, "x", height)

    subprocess.run(
        command,
        cwd=str(ltx_dir),
        check=True,
    )

    if not output.is_file() or output.stat().st_size < 1024:
        raise RuntimeError("LTX did not produce a valid video file.")

    print("SUCCESS:", output)


if __name__ == "__main__":
    main()
