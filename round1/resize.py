#!/usr/bin/env python3
import glob
import subprocess

try:
    from tqdm import tqdm
except ImportError:
    tqdm = lambda x: x

for img in tqdm(glob.glob("./img/Portfolio_2024-12/*")):
    fullsize = img
    thumbnail = img.replace('img/', 'img/resized/')
    # Resize so that 256px is the largest dimension
    cmd = ["magick", fullsize, "-auto-orient", "-strip", "-quality", "78", "-resize", "256x256", thumbnail]
    subprocess.run(cmd)
