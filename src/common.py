from pathlib import Path
import yaml, logging

ROOT = Path(__file__).resolve().parents[1]

def load_settings():
    with (ROOT / "config/settings.yaml").open(encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    for key in ("output_dir","input_dir","temp_dir","logs_dir"):
        cfg["app"][key] = str(ROOT / cfg["app"][key])
    cfg["assets"]["logo"] = str(ROOT / cfg["assets"]["logo"])
    cfg["assets"]["music_dir"] = str(ROOT / cfg["assets"]["music_dir"])
    return cfg

def setup_logging(cfg):
    Path(cfg["app"]["logs_dir"]).mkdir(parents=True, exist_ok=True)
    logging.basicConfig(filename=Path(cfg["app"]["logs_dir"])/"kayra.log",
                        level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    return logging.getLogger("kayra")
