#!/usr/bin/env python3
import glob
import os.path
import sys
from collections import defaultdict

current_path = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(current_path, "external/exifpy"))
import exifread

# PYTHONPATH=external/exifpy/

as_is = "{}".format

EXIF_TAG_CONVERTERS = {
    "EXIF FNumber": "f/{}".format,
    "EXIF FocalLength": "{}mm".format,
    "EXIF ExposureTime": "{}sec".format,
    "EXIF ISOSpeedRatings": "ISO{}".format,
    "Image Artist": as_is,
    "Image DateTime": as_is,
    "Image Make": as_is,
    "Image Model": as_is,
    "EXIF UserComment": as_is,
}


def get_tags(img_path: str) -> dict[str, str]:
    with open(img_path, "rb") as fh:
        all_tags = exifread.process_file(fh)
    tags = defaultdict(lambda: "")
    for tag, value in all_tags.items():
        if tag not in EXIF_TAG_CONVERTERS:
            continue
        converter = EXIF_TAG_CONVERTERS.get(tag) or as_is
        as_string = value.printable
        if tag == "EXIF FNumber" and len(value.values) == 1:
            try:
                # Convert f-number to a decimal
                # Do not use float() as that can be inaccurate
                as_string = format(value.values[0], ".5g")
            except Exception:
                as_string = value.printable
        tags[tag] = converter(as_string)
    return tags


for img in glob.glob("./img/Portfolio_2024-12/*"):
    fullsize = img
    basename = os.path.basename(img)
    thumbnail = img.replace("img/", "img/potato/")

    # Get from exif data
    tags = get_tags(img)
    title = " ".join(
        [basename, "by", tags["Image Artist"], tags["EXIF UserComment"]]
    )
    important_info = " ".join(
        [tags["EXIF ExposureTime"], tags["EXIF FNumber"], tags["EXIF ISOSpeedRatings"]]
    )
    details = " ".join(
        [
            tags["Image DateTime"],
            tags["Image Make"],
            tags["Image Model"],
            tags["EXIF FocalLength"],
        ]
    )

    alt_text = f"Photograph {title} ({important_info})"
    # Avoid double quote in this string
    caption_html = f"""
    <h4>{title}</h4>
    <p>{important_info} <i>({details})</i></p>
    """.strip().replace("\n", "")

    print(
        f"""<a href="{fullsize}" class="__gallery_anchor" data-sub-html="{caption_html}" ><img title="{alt_text}" alt="{alt_text}" src="{thumbnail}" data-fullsize="{fullsize}" ></a>"""
    )
