#!/usr/bin/env python3
"""This script generates HTML to display the given images in an aesthetically pleasing, network-error resilient HTML page suitable for a static website.

Good luck!
"""
import argparse
import base64
import glob
import logging
import os.path
import re
import sys
from collections import defaultdict
from enum import StrEnum

# PYTHONPATH add external/exifpy/
current_path = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(current_path, "external/exifpy"))
# TODO write your own exif library for jpg + png
import exifread

logger = logging.getLogger(__name__)

handler = logging.StreamHandler(sys.stderr)
handler.setLevel(logging.DEBUG)
formatter = logging.Formatter("[%(levelname)s] %(message)s")
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(logging.DEBUG)


class ImageLocation(StrEnum):
    """The internet URLs where images will be located."""

    AWS_S3 = "AWS_S3"
    LOCAL = "LOCAL"

    @classmethod
    def members(cls):
        """Return list of all enum member names."""
        return [name for name in cls.__members__]


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
POSSIBLE_EXIF_TAGS = list(EXIF_TAG_CONVERTERS.keys())

parser = argparse.ArgumentParser(
    description=__doc__, formatter_class=argparse.ArgumentDefaultsHelpFormatter
)
parser.add_argument(
    "--default-artist",
    help="This will be used for any image missing an artist.",
    default="Felina R.C.",
)
parser.add_argument(
    "--overwrite-artist", help="This will be used for all images.", default=None
)
parser.add_argument(
    "--image-location",
    "-l",
    help=f"Choose from: {', '.join(ImageLocation.members())}",
    required=True,
)
parser.add_argument(
    "--html-output",
    "-o",
    help="Output to stdout or use a template file. Will replace the string '<!-- gen.py output -->' in the template file with special HTML. LightGallery ($) or ViewerJS recommended, but suitable for non-JS browsers as well.",
    default="-",
)
parser.add_argument(
    "--basedir",
    "-b",
    help="Folder where all the full size images are located. "
    "Example: ./img/max_resolution/Portfolio_2024-12",
    required=True,
)
parser.add_argument(
    "--pathroot",
    "--root",
    "-r",
    help="Only needed if not using S3, images are locally hosted. This will be replaced by the URL root.",
    default="./",
)
parser.add_argument(
    "--aws-s3-bucket-url",
    "--bucket-url",
    help="REQUIRED if images are in S3. This is the AWS S3 bucket root URL. Example: https://s3.us-east-6.amazonaws.com/your.bucket.name/",
)
parser.add_argument(
    "--image-list",
    "--include-images",
    "-i",
    help="OPTIONAL. Include only images whose base filename matches any substring in this comma-separated list. Example: DSC101,DSC102 will select _DSC1010.jpg",
    default="",
)
parser.add_argument(
    "--hardcoded-count",
    type=int,
    default=20,
    help="How many images to encode in base64 for ultimate resilience against network errors. This can significantly increase the size of the HTML and ruins HTML caching.",
)
parser.add_argument(
    "--max-resolution-sub-dir",
    "--max-resolution-sub-folder",
    help="Sub-folder where all the full size images are located.",
    default="max_resolution/",
)
parser.add_argument(
    "--thumbnail-sub-dir",
    help="Sub-folder where all the thumbnail size images are located.",
    default="potato/",
)
parser.add_argument(
    "--smaller-sub-dir",
    help="Sub-folder where all the less-than-fullsize images are located.",
    default="s/",
)
parser.add_argument(
    "--important-exif-tags",
    help=f"Comma separated list of EXIF tag names to show in the image description, title, and alt text. Possible values: {POSSIBLE_EXIF_TAGS}",
    default="EXIF ExposureTime,EXIF FNumber,EXIF ISOSpeedRatings",
)
parser.add_argument(
    "--other-exif-tags",
    help=f"Comma separated list of EXIF tag names to show in the image description, title, and alt text. Possible values: {POSSIBLE_EXIF_TAGS}",
    default="Image Make,Image Model,EXIF FocalLength",
)
parser.add_argument(
    "--verbose",
    "-v",
    help="Log more information.",
    action="store_true",
)
parser.add_argument(
    "--quiet",
    "-q",
    help="Log only errors.",
    action="store_true",
)


def get_tags(img_filepath: str) -> dict[str, str]:
    """Extract EXIF image metadata from a given file."""
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


def remove_file_order(path: str) -> str:
    """Remove the user-specified order from a filename."""
    return os.path.dirname(path) + "/" + ORDER_REGEX.sub(r"\2", os.path.basename(path))


def get_file_order(path: str) -> int | float:
    """Get the user-specified order for a file."""
    match = ORDER_REGEX.match(os.path.basename(path))
    if not match:
        return float("inf")
    return int(match.groups()[0])


def doit(args: argparse.Namespace):
    """Generate HTML given these arguments."""
    img_location: ImageLocation = ImageLocation(args.image_location.strip().upper())

    # the first X imgs will be base64 data encoded
    # hardcoded into the HTML itself
    total_base64: int | float = args.hardcoded_count

    basedir = "./" + os.path.relpath(args.basedir)
    max_resolution_dir = args.max_resolution_sub_dir
    smaller_resolution_dir = args.smaller_sub_dir
    thumbnail_resolution_dir = args.thumbnail_sub_dir
    assert (
        max_resolution_dir in basedir
    ), "Images must be contained in a subfolder named max_resolution/"
    filepath_root = args.pathroot

    if img_location == ImageLocation.AWS_S3:
        desired_root = args.aws_s3_bucket_url
    elif img_location == ImageLocation.LOCAL:
        desired_root = filepath_root
    else:
        raise ValueError(f"Unknown image location! {img_location}")
    assert isinstance(desired_root, str)

    to_thumbnail_dir = lambda path: path.replace(
        max_resolution_dir, thumbnail_resolution_dir
    )
    to_smaller_dir = lambda path: path.replace(
        max_resolution_dir, smaller_resolution_dir
    )

    displayed_exif_tags = args.important_exif_tags
    misc_exif_tags = args.other_exif_tags
    overwrite_artist = args.overwrite_artist
    default_artist = args.default_artist
    html_output_location = args.html_output or "-"

    filter_image_list: list[str] = []
    if args.image_list:
        filter_image_list = [param.strip() for param in args.image_list.split(",")]

    str_output = []

    def output(line, to):
        if to == "-":
            print(line)
        else:
            str_output.append(line)

    for index, original_img_filepath in enumerate(
        sorted(glob.glob(f"{basedir}/*"), key=get_file_order)
    ):
        # ./Portfolio/img/
        # https://s3.us-east-1.amazonaws.com/media.felina.art/img/s/Portfolio_2024-12/_FEL0970.jpg_1500.jpg
        logger.info("Processing image %s", original_img_filepath)
        logger.debug(
            "Converting basename %s to %s",
            os.path.basename(original_img_filepath),
            get_file_order(original_img_filepath),
        )
        tags = get_tags(original_img_filepath)
        # Convert filepath into the right name for URLs and thumbnails
        root_img_filepath = remove_file_order(original_img_filepath)
        readable_basename = os.path.basename(root_img_filepath)
        if filter_image_list and not any(
            readable_basename in param for param in filter_image_list
        ):
            logger.debug("Skipping due to filter: %s", readable_basename)
            continue

        thumbnail_tiny_optimized_filepath = (
            to_thumbnail_dir(root_img_filepath) + "_tiny.webp"
        )
        img_url = root_img_filepath.replace(" ", "%20").replace(
            filepath_root, desired_root
        )

        fullsize = img_url
        # TODO ensure these filenames are the same used by resize.py
        smaller = to_smaller_dir(img_url) + "_1500.jpg"
        evensmaller = to_smaller_dir(img_url) + "_900.webp"
        thumbnail = to_thumbnail_dir(img_url)
        thumbnail_optimized = thumbnail + ".webp"

        if overwrite_artist:
            artist = overwrite_artist
        else:
            artist = tags["Image Artist"] or default_artist
        title = " ".join([readable_basename, "by", artist])

        important_info = ""
        if displayed_exif_tags:
            important_info = " ".join(
                [tags.get(tag, "") for tag in displayed_exif_tags]
            )
        details = " ".join([tags.get(tag, "") for tag in misc_exif_tags])

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
        if total_base64 and index < total_base64:
            with open(thumbnail_tiny_optimized_filepath, "rb") as tinythumb:
                tiny_base64 = base64.b64encode(tinythumb.read()).decode()
            embedded_thumbnail = f"data:image/webp;base64,{tiny_base64}"

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
        logger.info("Generated %s bytes for this %s", len(html), readable_basename)
        output(html, html_output_location)

    if str_output:
        with open(html_output_location, "r", encoding="utf-8") as htmltemplate:
            print(htmltemplate.read().replace("<!-- gen.py output -->", "\n".join(str_output)))


def main(sys_args=sys.argv[1:]):
    """Parse arguments and run the code, with error logging."""
    args = parser.parse_args(sys_args)
    if args.quiet:
        logger.setLevel(logging.ERROR)
    elif args.verbose:
        logger.setLevel(logging.DEBUG)
    else:
        logger.setLevel(logging.INFO)
    logger.debug(args)
    try:
        doit(args)
    except KeyboardInterrupt:
        logger.info("bye!")
    except Exception:
        logger.error("Critical error!", exc_info=True)


if __name__ == "__main__":
    main()
