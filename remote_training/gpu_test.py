import torch
from pathlib import Path

out = Path(r"D:\UNI\THESIS\remote_training\gpu_test.txt")

text = (
    f"Torch: {torch.__version__}\n"
    f"CUDA runtime: {torch.version.cuda}\n"
    f"CUDA available: {torch.cuda.is_available()}\n"
)

if torch.cuda.is_available():
    text += f"GPU: {torch.cuda.get_device_name(0)}\n"

out.write_text(text)
