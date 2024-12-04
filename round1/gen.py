#!/usr/bin/env python3
"""This script generates HTML to display the given images in an aesthetically pleasing, network-error resilient HTML page suitable for a static website.

Good luck!
"""
import argparse
import base64
import datetime
import glob
import logging
import os.path
import random
import re
import sys
from collections import defaultdict
from enum import StrEnum

try:
    import gzip
except ImportError:
    gzip = None

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
        return list(cls.__members__)


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
    "--local-root-url",
    default="./",
)
parser.add_argument(
    "--image-list",
    "--include-images",
    "--filter-images",
    "-i",
    help="OPTIONAL. Include only images whose base filename matches any substring in this comma-separated list (filter images). Example: DSC101,DSC102 will select _DSC1010.jpg",
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
    default="potato/",
)
parser.add_argument(
    "--order-from-filter",
    help="If using --include-images or --filter-images, respect that order for the final output.",
    action="store_true",
)
parser.add_argument(
    "--order-from-exif",
    help="Get the file order from the EXIF datetime.",
    action="store_true",
)
parser.add_argument(
    "--order-from-prefix",
    help="Get the file order from a prefix like __1_ or __142_.",
    action="store_true",
)
parser.add_argument(
    "--shuffled-order",
    help="Randomized image order",
    action="store_true",
)
parser.add_argument(
    "--random-seed",
    help="Random number generator seed",
    default=None,
)
parser.add_argument(
    "--reverse-order",
    help="Reverse the file order.",
    action="store_true",
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
    "--custom-css",
    help="Custom CSS to insert into template.",
    default="",
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


def parse_csv(thelist: str) -> list[str]:
    return [item.strip() for item in thelist.split(",")]


parse_tags_list = parse_csv
parse_filters = parse_csv


def filter_match(haystack, filter_) -> bool:
    return filter_ in haystack


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


def get_exif_datetime(path: str) -> datetime.datetime | int:
    return get_tags(path).get("Image DateTime", 0)


PREFIX_ORDER_REGEX = re.compile(r"^__(\d+)_(.*)")


def remove_file_order(path: str) -> str:
    """Remove the user-specified order from a filename."""
    return (
        os.path.dirname(path)
        + "/"
        + PREFIX_ORDER_REGEX.sub(r"\2", os.path.basename(path))
    )


def get_file_order(path: str) -> int | float:
    """Get the user-specified order for a file."""
    match = PREFIX_ORDER_REGEX.match(os.path.basename(path))
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
        desired_root = args.local_root_url
    else:
        raise ValueError(f"Unknown image location! {img_location}")
    assert isinstance(desired_root, str), "What should the root URL be?"

    to_thumbnail_dir = lambda path: path.replace(
        max_resolution_dir, thumbnail_resolution_dir
    )
    to_smaller_dir = lambda path: path.replace(
        max_resolution_dir, smaller_resolution_dir
    )
    def all_filepaths(fullsize_img: str) -> dict[str, str]:
        return {
        "fullsize": fullsize_img,
        "thumbnail_tiny_optimized_filepath": to_thumbnail_dir(fullsize_img)
        + "_tiny.webp",
        "smaller": to_smaller_dir(fullsize_img) + "_1500.jpg",
        "evensmaller": to_smaller_dir(fullsize_img) + "_900.webp",
        "thumbnail": to_thumbnail_dir(fullsize_img),
        "thumbnail_optimized": to_thumbnail_dir(fullsize_img) + ".webp",
    }

    displayed_exif_tags = parse_tags_list(args.important_exif_tags)
    misc_exif_tags = parse_tags_list(args.other_exif_tags)
    overwrite_artist = args.overwrite_artist
    default_artist = args.default_artist
    html_output_location = args.html_output or "-"
    custom_css = args.custom_css

    filters: list[str] = []
    if args.image_list:
        filters = parse_filters(args.image_list)
    logger.debug("Filter list: %s", filters)

    all_images = glob.glob(f"{basedir}/*")
    if args.shuffled_order:
        # Copy list
        sorted_images = all_images[:]
        random.shuffle(sorted_images)
    elif args.order_from_filter:
        logger.debug("Order from filter")
        assert filters, "Must pass a list of --filter-images!"
        sorted_images = []
        for filtr in filters:
            for image in all_images:
                if filter_match(image, filtr) and image not in sorted_images:
                    sorted_images.append(image)
    elif args.order_from_exif:
        sorted_images = list(sorted(all_images, key=get_exif_datetime))
    elif args.order_from_prefix:
        sorted_images = list(sorted(all_images, key=get_file_order))
    else:
        sorted_images = list(sorted(all_images))

    if args.reverse_order:
        # Reverse list
        sorted_images = sorted_images[::-1]
    logger.debug("Image order: %s", sorted_images)
        
    # TODO assert that S3 url exists...?
    # check that all expected filenames exist locally
    verified_paths = defaultdict(list)
    for image_path in all_images:
        for name, file in all_filepaths(image_path).items():
            fpath = os.path.realpath(file)
            assert os.path.exists(fpath), f"{name} is missing!"
            verified_paths[name].append(os.path.basename(fpath))
    if verified_paths:
        for type_ in verified_paths:
            logger.debug("Verified %s paths exist: %s", type_, " ".join(verified_paths[type_]))


    str_output = []

    def output(line):
        if html_output_location == "-":
            print(line)
        str_output.append(line)

    total_size = 0
    total_images = 0
    for index, original_img_filepath in enumerate(sorted_images):
        # ./Portfolio/img/
        # https://s3.us-east-1.amazonaws.com/media.felina.art/img/s/Portfolio_2024-12/_FEL0970.jpg_1500.jpg
        tags = get_tags(original_img_filepath)
        logger.debug("EXIF Tags: %s", dict(tags))
        # Convert filepath into the right name for URLs and thumbnails
        root_img_filepath = remove_file_order(original_img_filepath)
        logger.debug("Removed file order %s", root_img_filepath)
        readable_basename = os.path.basename(root_img_filepath)
        if filters and not any(
            filter_match(readable_basename, filtr) for filtr in filters
        ):
            found_filter = [
                filtr for filtr in filters if filter_match(readable_basename, filtr)
            ]
            logger.debug(
                "Skipping %s due to filter %s", readable_basename, found_filter
            )
            continue
        logger.debug("Processing image #%s: %s", total_images, readable_basename)

        filepaths = all_filepaths(root_img_filepath)
        urls = {name: path.replace(" ", "%20").replace(filepath_root, desired_root) for name, path in filepaths.items()}

        fullsize = urls["fullsize"]
        # TODO ensure these filenames are the same used by resize.py
        # TODO use shared functions or something....... all scripts in one file?
        smaller = urls["smaller"]
        evensmaller = urls["evensmaller"]
        thumbnail = urls["thumbnail"]
        thumbnail_optimized = urls["thumbnail_optimized"]

        if overwrite_artist:
            artist = overwrite_artist
        else:
            artist = tags["Image Artist"] or default_artist
        title = " ".join([readable_basename] + (["by", artist] if artist else []))

        important_info = ""
        if displayed_exif_tags:
            important_info = " ".join(
                [tags.get(tag, "") for tag in displayed_exif_tags]
            )
            logger.debug("Important tags: %s", displayed_exif_tags)
        details = " ".join([tags.get(tag, "") for tag in misc_exif_tags])

        alt_text = f"{title} (Exposure: {important_info})"
        # Avoid double quote in this string
        caption_html = f"""
        <h4>{title}</h4>
        <p>Exposure: {important_info} <i>({details})</i></p>
        """.strip().replace(
            "\n", ""
        )

        tiny_base64 = None
        embedded_thumbnail = f"{thumbnail}"
        if total_base64 and index < total_base64:
            with open(filepaths["thumbnail_tiny_optimized_filepath"], "rb") as tinythumb:
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
        logger.debug("Generated %s bytes for %s", len(html), readable_basename)
        total_size += len(html) + 1  # plus newline
        total_images += 1
        output(html)

    if total_images > 0:
        logger.info(
            "Generated %s images, %s total bytes, average of %.2f bytes per image",
            total_images,
            total_size,
            total_size / total_images,
        )
    else:
        logger.warning("Empty image set? Filters too strict or wrong paths given.")

    template_out = ""
    if html_output_location != "-":
        with open(html_output_location, "r", encoding="utf-8") as htmltemplate:
            template_out = (
                htmltemplate.read()
                .replace("/* Flexbox gallery custom CSS from gen.py */", custom_css)
                .replace("<!-- gen.py output -->", "\n".join(str_output))
            )
            print(template_out)

    if gzip and total_images > 0:
        if template_out:
            gzip_size = len(gzip.compress(template_out.encode()))
        else:
            gzip_size = len(gzip.compress("\n".join(str_output).encode()))
        logger.info(
            "Approximate GZIP size of all output: %s, savings of %.2f%%",
            gzip_size,
            100 * (1 - gzip_size / total_size),
        )


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
    if args.random_seed:
        random.seed(args.random_seed)
    try:
        doit(args)
    except KeyboardInterrupt:
        logger.info("bye!")
    except Exception:
        logger.error("Critical error!", exc_info=True)


if __name__ == "__main__":
    main()
