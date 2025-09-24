#!/usr/bin/env python3
"""
CLI tool to add EXIF shooting date (YYYY-MM-DD) as a text watermark to images.

Features:
- Input can be a single image file or a directory of images.
- Reads EXIF DateTimeOriginal/DateTime/DateTimeDigitized.
- User can control font size, color, and placement.
- Saves watermarked images into a sibling subdirectory named <original_dir>/_watermark.
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable, Optional, Tuple

from PIL import Image, ImageDraw, ImageFont, ImageColor


# Common EXIF datetime tag IDs
EXIF_TAG_DATETIME = 306  # DateTime
EXIF_TAG_DATETIME_ORIGINAL = 36867  # DateTimeOriginal
EXIF_TAG_DATETIME_DIGITIZED = 36868  # DateTimeDigitized


SUPPORTED_EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".png",
    ".tif",
    ".tiff",
    ".webp",
}


@dataclass
class WatermarkOptions:
    font_size: int
    color: str
    position: str
    margin: int
    font_path: Optional[Path]


def parse_args(argv: Optional[Iterable[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Add EXIF date (YYYY-MM-DD) watermark to image(s).",
    )
    parser.add_argument(
        "input_path",
        type=Path,
        help="Path to an image file or a directory containing images.",
    )
    parser.add_argument(
        "--font-size",
        type=int,
        default=36,
        help="Font size in pixels (default: 36).",
    )
    parser.add_argument(
        "--color",
        type=str,
        default="#FFFFFF",
        help="Text color (CSS name or #RRGGBB, default: #FFFFFF).",
    )
    parser.add_argument(
        "--position",
        choices=["tl", "tr", "bl", "br", "center"],
        default="br",
        help="Watermark position: tl=top-left, tr=top-right, bl=bottom-left, br=bottom-right, center (default: br).",
    )
    parser.add_argument(
        "--margin",
        type=int,
        default=12,
        help="Margin from edges in pixels (default: 12).",
    )
    parser.add_argument(
        "--font",
        type=Path,
        default=None,
        help="Optional path to a .ttf/.otf font file. If not provided, a default font is used.",
    )
    return parser.parse_args(argv)


def iter_image_files(path: Path) -> Iterable[Path]:
    if path.is_file():
        if path.suffix.lower() in SUPPORTED_EXTENSIONS:
            yield path
        return
    if path.is_dir():
        for p in sorted(path.iterdir()):
            if p.is_file() and p.suffix.lower() in SUPPORTED_EXTENSIONS:
                yield p


def extract_exif_date(image: Image.Image) -> Optional[str]:
    try:
        exif = image.getexif()
    except Exception:
        return None
    if not exif:
        return None

    for tag in (EXIF_TAG_DATETIME_ORIGINAL, EXIF_TAG_DATETIME_DIGITIZED, EXIF_TAG_DATETIME):
        value = exif.get(tag)
        if not value:
            continue
        # EXIF datetime often like "YYYY:MM:DD HH:MM:SS"
        if isinstance(value, bytes):
            try:
                value = value.decode("utf-8", errors="ignore")
            except Exception:
                continue
        if isinstance(value, str):
            parts = value.strip().split(" ")
            if not parts:
                continue
            date_str = parts[0]
            # Replace EXIF colons in date with hyphens
            date_str = date_str.replace(":", "-")
            # Validate date
            try:
                # Some cameras might store like YYYY-MM-DD already
                if ":" in parts[0]:
                    datetime.strptime(parts[0], "%Y:%m:%d%H:%M:%S" if len(parts) == 1 else "%Y:%m:%d")
                else:
                    datetime.strptime(date_str, "%Y-%m-%d")
            except Exception:
                # Best-effort: still return transformed date part
                pass
            return date_str
    return None


def load_font(font_path: Optional[Path], font_size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    if font_path is not None:
        try:
            return ImageFont.truetype(str(font_path), font_size)
        except Exception as exc:
            print(f"[WARN] Failed to load font '{font_path}': {exc}. Falling back to default font.")
    # Fallback default font
    try:
        return ImageFont.load_default()
    except Exception:
        # As a last resort, try a common system font (may not exist)
        return ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", font_size)


def compute_position(
    img_size: Tuple[int, int],
    text_size: Tuple[int, int],
    position: str,
    margin: int,
) -> Tuple[int, int]:
    img_w, img_h = img_size
    text_w, text_h = text_size

    if position == "tl":
        return (margin, margin)
    if position == "tr":
        return (img_w - text_w - margin, margin)
    if position == "bl":
        return (margin, img_h - text_h - margin)
    if position == "br":
        return (img_w - text_w - margin, img_h - text_h - margin)
    # center
    return ((img_w - text_w) // 2, (img_h - text_h) // 2)


def draw_watermark(
    image: Image.Image,
    text: str,
    options: WatermarkOptions,
) -> Image.Image:
    img = image.convert("RGBA")
    draw = ImageDraw.Draw(img)

    # Resolve color
    try:
        text_color = ImageColor.getrgb(options.color)
    except ValueError:
        print(f"[WARN] Invalid color '{options.color}', defaulting to white.")
        text_color = (255, 255, 255)

    font = load_font(options.font_path, options.font_size)
    # Use textbbox for accurate metrics
    bbox = draw.textbbox((0, 0), text, font=font)
    text_w, text_h = bbox[2] - bbox[0], bbox[3] - bbox[1]
    x, y = compute_position(img.size, (text_w, text_h), options.position, options.margin)

    # Optional subtle shadow for visibility
    shadow_offset = max(1, options.font_size // 24)
    shadow_color = (0, 0, 0, 160)
    try:
        draw.text((x + shadow_offset, y + shadow_offset), text, font=font, fill=shadow_color)
    except Exception:
        pass
    draw.text((x, y), text, font=font, fill=text_color)
    return img.convert(image.mode)


def ensure_output_dir(base: Path) -> Path:
    # If base is a file, use its parent; if it's a dir, use it directly
    parent = base.parent if base.is_file() else base
    out_dir = parent / f"{parent.name}_watermark"
    out_dir.mkdir(parents=True, exist_ok=True)
    return out_dir


def process_image_file(image_path: Path, options: WatermarkOptions, out_dir: Path) -> None:
    try:
        with Image.open(image_path) as im:
            date_text = extract_exif_date(im)
            if not date_text:
                print(f"[SKIP] No EXIF date found: {image_path}")
                return
            watermarked = draw_watermark(im, date_text, options)
            # Save with same filename into out_dir
            out_path = out_dir / image_path.name
            save_params = {}
            if out_path.suffix.lower() in {".jpg", ".jpeg"}:
                save_params.update({"quality": 95, "subsampling": 2})
            watermarked.save(out_path, **save_params)
            print(f"[OK] {image_path} -> {out_path}")
    except Exception as exc:
        print(f"[ERROR] Failed to process {image_path}: {exc}")


def main(argv: Optional[Iterable[str]] = None) -> int:
    args = parse_args(argv)
    input_path: Path = args.input_path

    options = WatermarkOptions(
        font_size=args.font_size,
        color=args.color,
        position=args.position,
        margin=args.margin,
        font_path=args.font,
    )

    if not input_path.exists():
        print(f"Input path does not exist: {input_path}")
        return 1

    files = list(iter_image_files(input_path))
    if not files:
        print("No supported image files found.")
        return 1

    out_dir = ensure_output_dir(input_path if input_path.is_dir() else input_path.parent)
    for f in files:
        process_image_file(f, options, out_dir)
    return 0


if __name__ == "__main__":
    sys.exit(main())


