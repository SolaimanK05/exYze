# ml

Floor plan model for photo imports (package B), and the folder where the dimension reader (`ml/ocr/`, package E) will live.

This README covers `ml/model/`: running CubiCasa5K, its licence, the photo test set and the results so far.

## Python and package versions

Use **Python 3.13**. Checked on 21 November 2026:

| Package | Version | Python 3.13 wheels |
| --- | --- | --- |
| PyTorch | 2.15.0 | Linux, Windows, macOS |
| PaddlePaddle (for PaddleOCR) | 3.3.1 | Linux, Windows, macOS arm64. No 3.14 wheel yet |

PaddlePaddle is the limit: it has no Python 3.14 wheel on PyPI, so 3.13 is the newest version both libraries support. Recheck before changing the Python version.

## Setup

```
python3.13 -m venv .venv
.venv/bin/pip install -r ml/requirements.txt --extra-index-url https://download.pytorch.org/whl/cpu
```

On Windows use `.venv\Scripts\pip`. Run the tests from the repository root:

```
.venv/bin/python -m pytest ml
```

### Weights

The published weights are 209 MB and are not in the repository (`*.pkl` and `ml/weights/` are git-ignored). Download them once:

```
pip install gdown
gdown 1gRB7ez1e4H7a9Y09lLqRuna0luZO5VRK -O ml/weights/model_best_val_loss_var.pkl
```

That is the link from the CubiCasa5K README. Check the file:

```
sha256  dd20b4e1bf1d670f2125107b079df06958b1ccd36e49a464ab739aeb00b8e7a2
```

The file is a pickle, but it loads with PyTorch's default `weights_only=True`: it holds only tensors and an `OrderedDict`. Don't pass `--trust-checkpoint` for this file.

## Running the model

```
python -m ml.model.infer plan.jpg --weights ml/weights/model_best_val_loss_var.pkl
```

For each image it writes three PNGs to `ml/out/` (git-ignored, change with `--out`) and prints the time taken:

| File | Contents |
| --- | --- |
| `<name>_rooms.png` | Room classes (kitchen, bedroom, wall, ...) in colour |
| `<name>_icons.png` | Icon classes (door, window, toilet, ...) in colour |
| `<name>_wall.png` | Wall mask, white on black |

Options:

| Option | Default | Notes |
| --- | --- | --- |
| `--device` | `cpu` | `cuda` or `auto` when PyTorch has CUDA |
| `--max-side` | 1024 | Larger images are shrunk to this longest side. Not tuned yet |
| `--no-rotate` | off | By default the image is run at four rotations and the outputs averaged, as in the original evaluation. This is about four times slower |

On Colab or Kaggle, install the repository, upload the weights and run the same command with `--device cuda`.

### What was ported

The code in `ml/model/` is adapted from the CubiCasa5K repository, which targets Python 3.6 and PyTorch 1.0.

- `network.py`: the hourglass network. Layer names are unchanged so the published weights load as they are. The old pose-estimation init file is gone, and the sigmoid on the junction heatmaps no longer writes into the output in place.
- `predict.py`: loading, image preparation (RGB scaled to -1..1, like the training data) and the rotation averaging.
- `infer.py`: the command line above.

Not ported: the junction heatmaps and the polygon post-processing. We build walls from the wall mask, so they are not needed for now.

### Checks done

- With random weights, the new network gives the same output as the original code running on current PyTorch (largest difference 0.0, even and odd image sizes). The state-dict keys are identical.
- With the real weights, on one plan, the room and icon class maps from `ml.model.predict.segment` are identical to those from the original evaluation code (0 differing pixels).
- Unit tests in `ml/model/tests/`.

### Speed

Measured on a 2-thread Linux machine, with the real weights, on a 1024 x 678 image:

| Mode | Time |
| --- | --- |
| Single pass (`--no-rotate`) | 2.8 s |
| Four rotations (default) | 11.5 s |

The target is under 10 seconds per photo on CPU. A single pass meets it here. The four-rotation mode does not. Timings on a team laptop have not been taken yet.

### Not done yet

- Run on a free Colab or Kaggle GPU (`--device cuda` is untested).
- Timing on a laptop.
- Any phone photos. The only image tried is a scan from the CubiCasa5K sample notebook, where walls, doors and windows came out cleanly. That is a clean scan, not a phone photo, so it says little about our photos.

## Licence

| Item | Licence | Source |
| --- | --- | --- |
| CubiCasa5K code (including the weights link) | CC BY-NC 4.0 | `LICENSE` in the repository |
| CubiCasa5K dataset | CC BY-NC-SA 4.0 | Zenodo record 2613548 |
| Weights file | No separate licence is stated | CubiCasa5K README |

What this means for us:

- **Non-commercial only.** Coursework and a demo are fine. If exYze were ever sold or used for paid work, we could not ship CubiCasa5K or its weights in it.
- **Attribution and a note of changes** are required. `ml/model/network.py` carries both in its header, and the paper should be cited in the report: *CubiCasa5K: A Dataset and an Improved Multi-Task Model for Floorplan Image Analysis* (arXiv 1904.01920).
- **Dataset share-alike.** The dataset is CC BY-NC-SA, so material derived from it may have to be shared under the same terms. Whether fine-tuned weights count is unclear, so check before we publish any in Sprint 5.
- The weights have no licence of their own, so the code licence is the safest reading to follow.

This is our reading of the licence text, not legal advice. The fallback in the risk table (OpenCV-only walls, or another open model) is only needed if the team wants to keep the option of commercial use.

## Photo test set

About 20 phone photos of printed floor plans. The photos stay out of git (`ml/data/` is ignored) and are shared with the team another way. Only the notes file is tracked.

Layout:

```
ml/data/photos/       # the photos, named p01.jpg, p02.jpg, ...
ml/testset/notes.csv  # one row per photo
```

How to take them: plan lying flat, whole sheet in frame, phone held parallel to the paper, no shadow across the plan. Include some bad ones on purpose (angle, glare, curled page, dim light), because those are the cases we need to know about. Printed plans, brochures and screens are in scope. Hand sketches are not.

`notes.csv` columns:

| Column | Meaning |
| --- | --- |
| `file` | File name, for example `p01.jpg` |
| `taken_by` | Who took it |
| `medium` | `print`, `brochure` or `screen` |
| `paper` | `A4`, `A3`, `other` or `n/a` |
| `lighting` | `good`, `dim`, `glare` or `shadow` |
| `angle` | `flat`, `slight` or `strong` |
| `units_printed` | Units of the dimensions on the plan, for Shanto's OCR |
| `walls` | `ok`, `partial` or `bad`, judged by eye on `_wall.png` |
| `doors_found`, `doors_total` | Counted by hand |
| `windows_found`, `windows_total` | Counted by hand |
| `seconds` | Time reported by `infer` |
| `notes` | What worked, what failed |

Run the whole set:

```
python -m ml.model.infer ml/data/photos/*.jpg --weights ml/weights/model_best_val_loss_var.pkl --out ml/out
```

Shanto's flattening is not in yet, so for now photos go in as taken. Once flattening exists, run the set again on the flattened images and keep both results: the difference shows what flattening is worth.

## Results

First results on the photo set (to fill in once the photos are in):

| Measure | Result |
| --- | --- |
| Photos in the set | |
| Walls `ok` / `partial` / `bad` | |
| Doors found / total | |
| Windows found / total | |
| Median time per photo, CPU | |

What works:

-

What fails:

-

One good and one bad example for the software lab demo:

-
