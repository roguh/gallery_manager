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
to_smaller_dir = lambda path: path.replace('img/', 'img/s/')

os.makedirs(to_thumbnail_dir(basedir), exist_ok=True)
os.makedirs(to_smaller_dir(basedir), exist_ok=True)

for img in tqdm(glob.glob(f"{basedir}/*")):
    fullsize = img
    
    thumbnail = to_thumbnail_dir(img)
    shrink = to_smaller_dir(img)
    
    # 256x - Resize so that 256px is the width, the height shall be proportional
    # x256 - Resize so that 256px is the height, the width shall be proportional
    cmd = ["magick", fullsize, "-auto-orient", "-strip", "-quality", "78", "-resize", "x256", thumbnail]
    webp_cmd = ["magick", fullsize, "-auto-orient", "-strip", "-quality", "78", "-resize", "x256", "-define", "webp:lossless=false", thumbnail + ".webp"]
    shrink_cmd = ["magick", fullsize, "-auto-orient", "-quality", "85", "-resize", "900x", "-define", "webp:lossless=false", shrink + ".webp"]

    webp_tiny_cmd = ["magick", fullsize, "-auto-orient", "-strip", "-quality", "75", "-resize", "x96"] + ["-define", "webp:lossless=false", thumbnail + "_tiny.webp"]
    subprocess.run(webp_tiny_cmd)
    subprocess.run(cmd)
    subprocess.run(webp_cmd)
    subprocess.run(shrink_cmd)
