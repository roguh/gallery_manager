#!/usr/bin/env python3
import glob
import multiprocessing
import os
import time
import re

try:
    from tqdm import tqdm
except ImportError:
    tqdm = lambda x: x

basedir = "./img/max_resolution/Portfolio_2024-12"

remove_file_order = True



ORDER_REGEX = re.compile(r"^__(\d+)_(.*)")

def remove_file_order(path: str) -> str:
    """Remove the user-specified order from a filename."""
    if not remove_file_order:
        return path
    return os.path.dirname(path) + "/" + ORDER_REGEX.sub(r"\2", os.path.basename(path))

to_thumbnail_dir = lambda path: remove_file_order(path.replace("img/max_resolution/", "img/potato/"))
to_smaller_dir = lambda path: remove_file_order(path.replace("img/max_resolution/", "img/potato/"))
os.makedirs(to_thumbnail_dir(basedir), exist_ok=True)
os.makedirs(to_smaller_dir(basedir), exist_ok=True)

def get_commands(img):
    fullsize = img
    thumbnail = to_thumbnail_dir(img)
    smaller = to_smaller_dir(img)

    # 256x - Resize so that 256px is the width, the height shall be proportional
    # x256 - Resize so that 256px is the height, the width shall be proportional
    thumbnail_cmd = [
        "magick",
        fullsize,
        "-auto-orient",
        "-strip",
        "-quality",
        "78",
        "-resize",
        "x256",
        thumbnail,
    ]
    webp_cmd = [
        "magick",
        fullsize,
        "-auto-orient",
        "-strip",
        "-quality",
        "78",
        "-resize",
        "x256",
        "-define",
        "webp:lossless=false",
        thumbnail + ".webp",
    ]
    smaller_cmds = [
        [
            "magick",
            fullsize,
            "-auto-orient",
            "-quality",
            "85",
            "-resize",
            "900x900^",
            "-define",
            "webp:lossless=false",
            smaller + "_900.webp",
        ],
        [
            "magick",
            fullsize,
            "-auto-orient",
            "-quality",
            "92",
            "-resize",
            "1500x1500^",
            "-format",
            "jpg",
            smaller + "_1500.jpg",
        ],
    ]
    webp_tiny_cmd = [
        "magick",
        fullsize,
        "-auto-orient",
        "-strip",
        "-quality",
        "75",
        "-resize",
        "x96",
        "-define",
        "webp:lossless=false",
        thumbnail + "_tiny.webp",
    ]
    return [
        webp_cmd,
        webp_tiny_cmd,
        thumbnail_cmd,
        *smaller_cmds,
    ]


def run_subprocess(command):
    import subprocess

    subprocess.run(command)


def main():
    commands = []
    for img in glob.glob(f"{basedir}/*"):
        commands += get_commands(img)

    processes = max(2, 2 * os.cpu_count())
    print("Parallelizing with #processes =", processes)

    pbar = tqdm(total=len(commands))
    with multiprocessing.Pool(processes=processes) as pool:
        for _ in pool.imap_unordered(run_subprocess, commands):
            pbar.update(1)


if __name__ == "__main__":
    main()
