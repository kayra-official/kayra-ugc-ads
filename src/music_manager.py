from pathlib import Path
import subprocess
import json

SUPPORTED={".mp3",".wav",".m4a",".aac",".flac",".ogg"}

def find_music(cfg):
    folder=Path(cfg["assets"]["music_dir"])
    chosen=cfg["assets"].get("music_file","").strip()
    if chosen:
        p=Path(chosen); p=p if p.is_absolute() else folder/p
        if p.exists(): return p
        raise FileNotFoundError(f"Configured music file not found: {p}")
    files=sorted(p for p in folder.iterdir() if p.suffix.lower() in SUPPORTED) if folder.exists() else []
    if not files: raise FileNotFoundError("No local music file found. Add a licensed instrumental track to assets/music.")
    return files[0]

def mix_music(video, music, output, cfg):
    probe = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "json", str(video)],
        check=True, capture_output=True, text=True,
    )
    dur = float(json.loads(probe.stdout)["format"]["duration"])
    vol=cfg["video"]["music_volume"]; fade=cfg["video"]["audio_fade_seconds"]
    af=f"volume={vol},afade=t=in:st=0:d={fade},afade=t=out:st={max(0,dur-fade)}:d={fade}"
    cmd=["ffmpeg","-y","-i",str(video),"-stream_loop","-1","-i",str(music),
         "-map","0:v:0","-map","1:a:0","-c:v","copy","-af",af,"-t",str(dur),
         "-movflags","+faststart",str(output)]
    subprocess.run(cmd,check=True,capture_output=True,text=True)
    return Path(output)
