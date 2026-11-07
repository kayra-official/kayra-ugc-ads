from pathlib import Path
import subprocess

def create_logo_outro(logo_path, output_path, cfg):
    logo=Path(logo_path)
    if not logo.exists(): raise FileNotFoundError(f"Original KAYRA logo missing: {logo}")
    w,h=cfg["video"]["width"],cfg["video"]["height"]; dur=cfg["video"]["outro_seconds"]; fps=cfg["video"]["fps"]
    # Static original logo over animated light-gradient background; logo itself is never AI-generated.
    vf=(f"scale=iw*min((iw*0+{w}*0.72)/iw,(ih*0+{h}*0.28)/ih):-1,"
        f"format=rgba")
    cmd=["ffmpeg","-y","-f","lavfi","-i",f"color=c=0x102b22:s={w}x{h}:r={fps}:d={dur}",
         "-i",str(logo),"-filter_complex",
         f"[1:v]scale=iw*min({w}*0.72/iw,{h}*0.28/ih):-1,format=rgba[logo];"
         f"[0:v][logo]overlay=(W-w)/2:(H-h)/2:format=auto,fade=t=in:st=0:d=0.7,fade=t=out:st={dur-0.6}:d=0.6[v]",
         "-map","[v]","-an","-t",str(dur),"-pix_fmt","yuv420p",str(output_path)]
    subprocess.run(cmd,check=True,capture_output=True,text=True)
    return Path(output_path)
