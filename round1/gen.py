#!/usr/bin/env python3
import base64
import glob
import os.path
import re
import sys
from enum import StrEnum
from collections import defaultdict

current_path = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(current_path, "external/exifpy"))
# TODO write your own exif library for jpg + png
import exifread

# TODO artist parameter
default_artist = "Felina R.C."

class ImageLocation(StrEnum):
    AWS_S3 = "AWS_S3"
    LOCAL = "LOCAL"


# TODO img_location parameter
# img_location: ImageLocation = ImageLocation.AWS_S3
img_location: ImageLocation = ImageLocation.LOCAL

# PYTHONPATH=external/exifpy/

# TODO base64 count/enable parameter
BASE64 = 20  # the first 10 imgs will be data encoded

# TODO basedir parameter
basedir = "./img/max_resolution/Portfolio_2024-12"
filepath_root = "./"

if img_location == ImageLocation.AWS_S3:
# TODO bucket url parameter
    desired_root = "https://s3.us-east-1.amazonaws.com/media.felina.art/"
elif img_location == ImageLocation.LOCAL:
    desired_root = filepath_root
else:
    raise ValueError(f"Unknown image location! {img_location}")

# TODO thumbnail and smaller parameter
to_thumbnail_dir = lambda path: path.replace("img/max_resolution/", "img/potato/")
to_smaller_dir = lambda path: path.replace("img/max_resolution/", "img/s/")

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


def get_tags(img_filepath: str) -> dict[str, str]:
    with open(img_filepath, "rb") as fh:
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


ORDER_REGEX = re.compile(r"^__(\d+)_(.*)")
get_order = lambda path: int(ORDER_REGEX.match(os.path.basename(path)).groups()[0]) if ORDER_REGEX.match(os.path.basename(path)) else float('inf')
remove_order = lambda path: os.path.dirname(path) + "/" + ORDER_REGEX.sub(r"\2", os.path.basename(path))


def main():
    for index, original_img_filepath in enumerate(sorted(glob.glob(f"{basedir}/*"), key=get_order)):
        # ./Portfolio/img/
        # https://s3.us-east-1.amazonaws.com/media.felina.art/img/s/Portfolio_2024-12/_FEL0970.jpg_1500.jpg
        print(os.path.basename(original_img_filepath), get_order(original_img_filepath), file=sys.stderr)
        tags = get_tags(original_img_filepath)
        # Convert filepath into the right name for URLs and thumbnails
        root_img_filepath = remove_order(original_img_filepath)
        readable_basename = os.path.basename(root_img_filepath)
        thumbnail_tiny_optimized_filepath = to_thumbnail_dir(root_img_filepath) + "_tiny.webp"
        img_url = root_img_filepath.replace(" ", "%20").replace(filepath_root, desired_root)

        fullsize = img_url
        # TODO ensure these filenames are the same used by resize.py
        smaller = to_smaller_dir(img_url) + "_1500.jpg"
        evensmaller = to_smaller_dir(img_url) + "_900.webp"
        thumbnail = to_thumbnail_dir(img_url)
        thumbnail_optimized = thumbnail + ".webp"

        # Get from exif data
        title = " ".join(
            [readable_basename, "by", tags["Image Artist"] or default_artist]
        )
        # TODO exif tag parameter
        important_info = " ".join(
            [
                tags["EXIF ExposureTime"],
                tags["EXIF FNumber"],
                tags["EXIF ISOSpeedRatings"],
            ]
        )
        details = " ".join(
            [
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
        """.strip().replace(
            "\n", ""
        )

        tiny_base64 = None
        embedded_thumbnail = f"{thumbnail}"
        if BASE64 and index < BASE64:
            with open(thumbnail_tiny_optimized_filepath, "rb") as tinythumb:
                tiny_base64 = base64.b64encode(tinythumb.read()).decode()
            embedded_thumbnail = (
                f'data:image/webp;base64,{tiny_base64}'
            )

        # data-responsively-lazy - for lazy loading
        # data-fullsize - link to fullsize image, for viewerjs
        html = f"""
            <!-- {readable_basename} -->
            <a 
                class="__gallery_anchor"
                data-sub-html="{caption_html}"
                href="{fullsize}"
                data-src="{smaller}"
                data-srcset="{evensmaller} 1100w, {smaller} 1600w"
                data-download-url="{fullsize}"
            >
                <img
                    title="{alt_text}"
                    src="{embedded_thumbnail}"
                    srcset="{thumbnail_optimized} 256w webp, {thumbnail} 256w"
                    onerror="this.srcset=this.src"
                    data-fullsize="{fullsize}" >
            </a>"""
        html = "".join(line.strip() + " " for line in html.split("\n")).strip()
        print(html)


if __name__ == "__main__":
    main()
