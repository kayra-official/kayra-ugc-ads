
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

    ltx_dir = Path(generation.get("ltx_project_dir", "~/Documents/GitHub/ltx-2-mlx")).expanduser().resolve()
    model = generation["model"]
    width = int(generation["render_width"])
    height = int(generation["render_height"])
    frames = int(generation.get("frames", 25))

    ltx_executable = ltx_dir / ".venv" / "bin" / "ltx-2-mlx"
    command = [
        str(ltx_executable) if ltx_executable.is_file() else "uv",
    ]
    if not ltx_executable.is_file():
        command.extend(["run", "--package", "ltx-pipelines-mlx", "ltx-2-mlx"])
    command.extend([
        "generate",
        "--prompt", prompt,
        "--output", str(output),
        "--model", model,
        "--width", str(width),
        "--height", str(height),
        "--frames", str(frames),
        "--frame-rate", str(fps),
        "--seed", str(seed),
        "--distilled",
        "--low-ram",
        "--no-audio",
    ])
    # Use guided frame conditioning for both snapshot and video passes. The
    # scene pass previously relied on LTX's automatic image binding, which
    # gave it more freedom to reinterpret the pendant and earrings.
    command.extend([
        "--image", str(reference), "0",
        str(request.get("image_strength", 0.65)),
        request.get("image_binding", "guide"),
    ])

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
