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
    # 256x - Resize so that 256px is the height, the height shall be proportional
    # x256 - Resize so that 256px is the width, the width shall be proportional
    cmd = ["magick", fullsize, "-auto-orient", "-strip", "-quality", "78", "-resize", "x256", thumbnail]
    subprocess.run(cmd)
