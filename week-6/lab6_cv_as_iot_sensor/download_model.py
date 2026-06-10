"""
Tải model YOLOv8n ONNX cho object detection trong Lab 6 Enhanced.
Chạy:
    python download_model.py
"""
import urllib.request
import sys
from pathlib import Path

MODEL_DIR = Path(__file__).resolve().parent / "models"
MODEL_PATH = MODEL_DIR / "yolov8n.onnx"
# Fallback URLs
URLS = [
    "https://huggingface.co/Kalray/yolov8/resolve/main/yolov8n.onnx",
    "https://huggingface.co/Kalray/yolov8/raw/main/yolov8n.onnx",
]

def download(url: str, dest: Path):
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Downloading YOLOv8n ONNX model...")
    print(f"  URL: {url}")
    print(f"  Dest: {dest}")
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=120) as resp:
            with open(str(dest), "wb") as f:
                f.write(resp.read())
        size_mb = dest.stat().st_size / (1024 * 1024)
        print(f"Done! Model saved ({size_mb:.1f} MB).")
        print("Enable detection in config.yaml: detection.enabled = true")
        return True
    except Exception as e:
        print(f"  Failed: {e}")
        return False

if __name__ == "__main__":
    if MODEL_PATH.exists():
        overwrite = input(f"Model already exists at {MODEL_PATH}. Overwrite? (y/N): ").strip().lower()
        if overwrite != "y":
            print("Skipping download.")
            sys.exit(0)
    for url in URLS:
        if download(url, MODEL_PATH):
            sys.exit(0)
    print("\nAll URLs failed. You can manually download yolov8n.onnx and save to:")
    print(f"  {MODEL_PATH}")
    print("Then enable detection in config.yaml: detection.enabled = true")
    sys.exit(1)
