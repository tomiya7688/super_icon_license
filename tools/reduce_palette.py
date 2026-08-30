"""Convert project raster assets to a strict grayscale or grayscale-plus-red palette."""
from __future__ import annotations

import argparse
import subprocess
from io import BytesIO
from pathlib import Path
from typing import Iterable

from PIL import Image

BLACK = (0, 0, 0)
GRAY = (128, 128, 128)
WHITE = (255, 255, 255)
RED = (255, 0, 0)


def is_red(r: int, g: int, b: int) -> bool:
    """Keep clearly red pixels; map anti-aliased red shades to pure red."""
    strongest_other = max(g, b)
    return r >= 96 and r - strongest_other >= 40 and r >= strongest_other * 1.35


def gray_level(r: int, g: int, b: int) -> tuple[int, int, int]:
    """Keep mid and light-gray areas visibly gray instead of collapsing to white."""
    luma = 0.2126 * r + 0.7152 * g + 0.0722 * b
    if luma < 64:
        return BLACK
    if luma < 224:
        return GRAY
    return WHITE


def output_kwargs(path: Path) -> dict[str, object]:
    if path.suffix.lower() == ".webp":
        return {"format": "WEBP", "lossless": True, "method": 6}
    return {"format": "PNG", "compress_level": 9}


def source_image(path: Path, source_ref: str | None) -> Image.Image:
    if source_ref is None:
        return Image.open(path)
    repository = path.parents[1]
    relative_path = path.relative_to(repository).as_posix()
    result = subprocess.run(
        ["git", "show", f"{source_ref}:{relative_path}"],
        cwd=repository,
        check=True,
        stdout=subprocess.PIPE,
    )
    return Image.open(BytesIO(result.stdout))


def convert(path: Path, preserve_red: bool, source_ref: str | None) -> set[tuple[int, int, int]]:
    with source_image(path, source_ref) as source:
        image = source.convert("RGBA")
        converted: list[tuple[int, int, int, int]] = []
        colors: set[tuple[int, int, int]] = set()
        for r, g, b, a in image.getdata():
            if a == 0:
                converted.append((0, 0, 0, 0))
                continue
            color = RED if preserve_red and is_red(r, g, b) else gray_level(r, g, b)
            converted.append((*color, a))
            colors.add(color)
        image.putdata(converted)
        temporary = path.with_name(path.stem + ".palette-tmp" + path.suffix)
        image.save(temporary, **output_kwargs(path))
    temporary.replace(path)
    return colors


def raster_files(directory: Path) -> Iterable[Path]:
    yield from sorted(path for path in directory.iterdir() if path.suffix.lower() in {".png", ".webp"})


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("assets", type=Path)
    parser.add_argument("--keep-red", action="store_true")
    parser.add_argument("--source-ref", help="Read unprocessed source images from this Git ref.")
    args = parser.parse_args()

    allowed = {BLACK, GRAY, WHITE}
    if args.keep_red:
        allowed.add(RED)

    files = list(raster_files(args.assets))
    if not files:
        raise SystemExit(f"No PNG or WebP files in {args.assets}")

    for path in files:
        colors = convert(path, args.keep_red, args.source_ref)
        if not colors <= allowed:
            raise RuntimeError(f"Unexpected colors in {path}: {colors - allowed}")
        print(f"{path.name}: {', '.join('#%02X%02X%02X' % color for color in sorted(colors))}")


if __name__ == "__main__":
    main()