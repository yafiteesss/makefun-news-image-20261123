"""Entrypoint for the news-image-20261123 entry.

Renders the Monday 23 November 2026 world-news poster and writes it to
entry.png in the output directory. Standard library only, no network,
fully deterministic: two runs write byte-identical files.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from build_image import build_png_bytes


def output_dir():
    env_dir = os.environ.get("MAKEFUN_OUTPUT_DIR")
    if env_dir:
        return env_dir
    if os.path.isdir("/output"):
        return "/output"
    return "out"


def main():
    target_dir = output_dir()
    os.makedirs(target_dir, exist_ok=True)
    data = build_png_bytes()
    path = os.path.join(target_dir, "entry.png")
    with open(path, "wb") as fh:
        fh.write(data)
    print("wrote %s (%d bytes)" % (path, len(data)))


if __name__ == "__main__":
    main()
