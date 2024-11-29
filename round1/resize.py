#!/usr/bin/env python3
import glob
import subprocess

try:
    from tqdm import tqdm
except ImportError:
    tqdm = lambda x: x

for img in tqdm(glob.glob("./Portfolio_2024-12/*")):
    fullsize = img
    thumbnail = f"resized/{img}"
    # Resize so that 256px is the largest dimension
    cmd = ["magick", fullsize, "-auto-orient", "-resize", "256x256", thumbnail]
    subprocess.run(cmd)
