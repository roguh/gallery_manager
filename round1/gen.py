#!/usr/bin/env python3
import glob
for img in glob.glob("./Portfolio_2024-12/*"):
    fullsize = img
    thumbnail = f"resized/{img}"
    print(f"""<a href="{fullsize}" class="__gallery_anchor"><img src="{thumbnail}" data-fullsize="{fullsize}"></a>""")
