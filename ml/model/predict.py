"""Loading the CubiCasa5K weights and running segmentation on one image."""

from dataclasses import dataclass

import numpy as np
import torch
import torch.nn.functional as F
from PIL import Image

from .network import N_CLASSES, N_HEATMAPS, N_ROOM_CLASSES, HourglassFloorPlan

ROOM_CLASSES = [
    "Background",
    "Outdoor",
    "Wall",
    "Kitchen",
    "Living Room",
    "Bedroom",
    "Bath",
    "Hallway",
    "Railing",
    "Storage",
    "Garage",
    "Other rooms",
]
ICON_CLASSES = [
    "Empty",
    "Window",
    "Door",
    "Closet",
    "Electr. Appl.",
    "Toilet",
    "Sink",
    "Sauna bench",
    "Fire Place",
    "Bathtub",
    "Chimney",
]

WALL = ROOM_CLASSES.index("Wall")
WINDOW = ICON_CLASSES.index("Window")
DOOR = ICON_CLASSES.index("Door")

# quarter turns used for test-time averaging, as in the original eval code
TURNS = (0, 1, 2, -1)


@dataclass
class Segmentation:
    rooms: np.ndarray  # (H, W) uint8, index into ROOM_CLASSES
    icons: np.ndarray  # (H, W) uint8, index into ICON_CLASSES

    @property
    def wall_mask(self):
        return self.rooms == WALL


def load_model(weights, device="cpu", trust_checkpoint=False):
    """Build the network and load the published checkpoint into it.

    The checkpoint is a pickle. By default only plain tensors are accepted
    (torch.load with weights_only=True). If that fails on the official file,
    rerun with trust_checkpoint=True, but only for a file you downloaded from
    the CubiCasa5K authors.
    """
    model = HourglassFloorPlan(N_CLASSES)
    checkpoint = torch.load(
        weights, map_location="cpu", weights_only=not trust_checkpoint
    )
    model.load_state_dict(checkpoint["model_state"])
    return model.to(device).eval()


def load_image(path, max_side=None):
    """Read an image as a (1, 3, H, W) tensor in [-1, 1], like the training data."""
    img = Image.open(path).convert("RGB")
    if max_side and max(img.size) > max_side:
        scale = max_side / max(img.size)
        img = img.resize(
            (round(img.width * scale), round(img.height * scale)), Image.LANCZOS
        )
    arr = np.asarray(img, dtype=np.float32)
    tensor = torch.from_numpy(arr).permute(2, 0, 1).unsqueeze(0)
    return 2 * (tensor / 255.0) - 1


def _turn(t, n):
    # n quarter turns clockwise on a (N, C, H, W) tensor
    return torch.rot90(t, k=-n, dims=(2, 3))


@torch.inference_mode()
def segment(model, image, rotate=True):
    """Return the room and icon class maps for an image tensor.

    With rotate=True the image is run at four orientations and the logits are
    averaged, which is what the original evaluation does. It is about four
    times slower. The junction heatmaps are not used here.
    """
    device = next(model.parameters()).device
    image = image.to(device)
    height, width = image.shape[2:]

    turns = TURNS if rotate else (0,)
    logits = 0
    for n in turns:
        out = _turn(model(_turn(image, n)), -n)
        out = out[:, N_HEATMAPS:]
        logits = logits + F.interpolate(
            out, size=(height, width), mode="bilinear", align_corners=True
        )
    logits = logits / len(turns)

    rooms = logits[:, :N_ROOM_CLASSES].argmax(dim=1)[0]
    icons = logits[:, N_ROOM_CLASSES:].argmax(dim=1)[0]
    return Segmentation(
        rooms.to(torch.uint8).cpu().numpy(), icons.to(torch.uint8).cpu().numpy()
    )


def pick_device(name):
    if name == "auto":
        return "cuda" if torch.cuda.is_available() else "cpu"
    return name
