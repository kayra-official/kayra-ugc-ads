from pathlib import Path
import subprocess, json

def probe(path):
    p=subprocess.run(["ffprobe","-v","error","-show_streams","-show_format","-of","json",str(path)],
                     check=True,capture_output=True,text=True)
    return json.loads(p.stdout)

def check_video(path, expected_seconds=25, width=1080, height=1920):
    data=probe(path); streams=data.get("streams",[])
    v=next((s for s in streams if s.get("codec_type")=="video"),None)
    if not v: raise ValueError("Export has no video stream.")
    duration=float(data["format"]["duration"])
    if abs(duration-expected_seconds)>1.0: raise ValueError(f"Unexpected duration: {duration:.2f}s")
    if v.get("width")!=width or v.get("height")!=height:
        raise ValueError(f"Unexpected resolution: {v.get('width')}x{v.get('height')}")
    return {"duration":duration,"width":v["width"],"height":v["height"],
            "fps":v.get("r_frame_rate"),"has_audio":any(s.get("codec_type")=="audio" for s in streams)}
