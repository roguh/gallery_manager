#!/usr/bin/env python3
import glob
import os
import subprocess

try:
    from tqdm import tqdm
except ImportError:
    tqdm = lambda x: x

basedir = "./img/Portfolio_2024-12"
to_thumbnail_dir = lambda path: path.replace('img/', 'img/potato/')

os.makedirs(to_thumbnail_dir(basedir), exist_ok=True)

for img in tqdm(glob.glob(f"{basedir}/*")):
    fullsize = img
    thumbnail = to_thumbnail_dir(img)
    # Resize so that 256px is the largest dimension
    cmd = ["magick", fullsize, "-auto-orient", "-strip", "-quality", "78", "-resize", "256x256", thumbnail]
    subprocess.run(cmd)
