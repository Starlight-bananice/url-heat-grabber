#!/usr/bin/env python3
"""Build a macOS .icns file from the project's PNG iconset.

The macOS image tool available in some build environments rejects otherwise
valid iconsets, so this keeps the conversion deterministic and dependency-free.
The modern PNG-backed icon types below are understood by current macOS Finder.
"""

from __future__ import annotations

import struct
import sys
from pathlib import Path


ICON_ENTRIES = (
    ("ic11", "icon_16x16@2x.png"),
    ("ic12", "icon_32x32@2x.png"),
    ("ic07", "icon_128x128.png"),
    ("ic13", "icon_128x128@2x.png"),
    ("ic08", "icon_256x256.png"),
    ("ic14", "icon_256x256@2x.png"),
    ("ic09", "icon_512x512.png"),
    ("ic10", "icon_512x512@2x.png"),
)


def chunk(kind: str, payload: bytes) -> bytes:
    kind_bytes = kind.encode("ascii")
    if len(kind_bytes) != 4:
        raise ValueError(f"invalid icon type: {kind}")
    return kind_bytes + struct.pack(">I", len(payload) + 8) + payload


def build(iconset_dir: Path, output_path: Path) -> None:
    chunks: list[bytes] = []
    for kind, filename in ICON_ENTRIES:
        source = iconset_dir / filename
        if not source.is_file():
            raise FileNotFoundError(source)
        payload = source.read_bytes()
        if not payload.startswith(b"\x89PNG\r\n\x1a\n"):
            raise ValueError(f"not a PNG: {source}")
        chunks.append(chunk(kind, payload))

    body = b"".join(chunks)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(b"icns" + struct.pack(">I", len(body) + 8) + body)


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit("usage: build_icns.py ICONSET_DIR OUTPUT_ICNS")
    build(Path(sys.argv[1]), Path(sys.argv[2]))
