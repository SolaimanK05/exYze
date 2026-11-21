"""Run the floor plan model on one or more images.

    python -m ml.model.infer plan.jpg --weights ml/weights/model_best_val_loss_var.pkl

Writes <name>_rooms.png, <name>_icons.png and <name>_wall.png to --out for each
image and prints how long the model took.
"""

import argparse
import sys
import time
from pathlib import Path

import numpy as np
import torch
from PIL import Image

from .predict import (
    DOOR,
    WALL,
    WINDOW,
    load_image,
    load_model,
    pick_device,
    segment,
)

# one colour per class, background and "empty" are white
ROOM_COLOURS = [
    (255, 255, 255),
    (180, 180, 180),
    (0, 0, 0),
    (222, 184, 135),
    (255, 215, 0),
    (135, 206, 250),
    (64, 224, 208),
    (221, 160, 221),
    (139, 69, 19),
    (160, 160, 100),
    (100, 100, 160),
    (240, 128, 128),
]
ICON_COLOURS = [
    (255, 255, 255),
    (30, 144, 255),
    (220, 20, 60),
    (210, 105, 30),
    (255, 140, 0),
    (46, 139, 87),
    (72, 209, 204),
    (188, 143, 143),
    (178, 34, 34),
    (123, 104, 238),
    (105, 105, 105),
]


def paint(class_map, colours):
    return Image.fromarray(np.asarray(colours, dtype=np.uint8)[class_map])


def parse_args(argv):
    p = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    p.add_argument("images", nargs="+", type=Path)
    p.add_argument("--weights", required=True, type=Path)
    p.add_argument("--out", type=Path, default=Path("ml/out"))
    p.add_argument("--device", default="cpu", help="cpu, cuda or auto (default cpu)")
    p.add_argument(
        "--max-side",
        type=int,
        default=1024,
        help="shrink images whose longest side is larger (default 1024)",
    )
    p.add_argument(
        "--no-rotate",
        action="store_true",
        help="skip the four-rotation averaging, about 4x faster",
    )
    p.add_argument(
        "--trust-checkpoint",
        action="store_true",
        help="allow a full pickle load of the weights file",
    )
    return p.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    if not args.weights.is_file():
        sys.exit(
            f"weights not found: {args.weights}\n"
            "Download model_best_val_loss_var.pkl from the CubiCasa5K README link."
        )

    device = pick_device(args.device)
    model = load_model(args.weights, device, args.trust_checkpoint)
    args.out.mkdir(parents=True, exist_ok=True)
    print(f"device: {device}, torch {torch.__version__}")

    for path in args.images:
        image = load_image(path, args.max_side)
        start = time.perf_counter()
        seg = segment(model, image, rotate=not args.no_rotate)
        if device.startswith("cuda"):
            torch.cuda.synchronize()
        seconds = time.perf_counter() - start

        paint(seg.rooms, ROOM_COLOURS).save(args.out / f"{path.stem}_rooms.png")
        paint(seg.icons, ICON_COLOURS).save(args.out / f"{path.stem}_icons.png")
        Image.fromarray(seg.wall_mask.astype(np.uint8) * 255).save(
            args.out / f"{path.stem}_wall.png"
        )

        h, w = seg.rooms.shape
        total = h * w
        print(
            f"{path.name}: {w}x{h}, {seconds:.1f}s, "
            f"wall {np.count_nonzero(seg.rooms == WALL) / total:.1%}, "
            f"door px {np.count_nonzero(seg.icons == DOOR)}, "
            f"window px {np.count_nonzero(seg.icons == WINDOW)}"
        )


if __name__ == "__main__":
    main()
