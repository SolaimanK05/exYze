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

On Colab, pick a GPU runtime, then:

```
!git clone https://github.com/SolaimanK05/exyze
%cd exyze
!pip install -q -r ml/requirements.txt gdown
!gdown 1gRB7ez1e4H7a9Y09lLqRuna0luZO5VRK -O ml/weights/model_best_val_loss_var.pkl
!python -m ml.model.infer plan.jpg --weights ml/weights/model_best_val_loss_var.pkl --device cuda
```

Make the `ml/weights` folder first (`!mkdir -p ml/weights`) and upload the photo next to the notebook. Disconnect the runtime when you are done: free GPU time is capped.

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

Time per photo, with the real weights, images shrunk to 1024 on the long side:

| Machine | Four rotations (default) | Single pass (`--no-rotate`) |
| --- | --- | --- |
| Windows 10 PC, CPU only (4 photos) | 10.0 to 13.5 s, median 12.9 s | 2.8 to 4.3 s, median 3.7 s |
| 2-thread Linux machine, CPU | 8 to 16 s | about 3 s |
| Colab T4 GPU (3 photos) | 0.3 to 0.8 s after the first call (2.1 s while CUDA starts) | not timed |

The target is under 10 seconds per photo on CPU. A single pass meets it on the PC. The four-rotation mode does not, by a few seconds. On the one photo where both modes were compared by eye (p30), the wall masks were both usable, with the four-rotation one slightly better. The GPU gave the same outputs as the CPU, to within one pixel.

### Not done yet

- Kaggle GPU (Colab T4 is tested, Kaggle is not).
- Running the set again after Shanto's flattening is in.
- Cropping out page clutter before the model runs (see Results).

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

28 floor plan images: 25 photos (7 of a plan on a monitor, 18 of paper plans), 1 clean digital image and 2 archive scans. The photos stay out of git (`ml/data/` is ignored) and are shared with the team in a Google Drive folder. Only the notes file is tracked.

Layout:

```
ml/data/photos/       # the photos, named p01_<description>_<medium>.jpg and so on
ml/testset/notes.csv  # one row per photo, keyed by the p-number
```

The set includes bad cases on purpose (shadow, rotation, creased paper, a finger in frame), because those are the cases we need to know about. Printed plans and screens are in scope. Hand sketches are not, apart from p11.

`notes.csv` columns:

| Column | Meaning |
| --- | --- |
| `file` | The p-number, for example `p01` (the start of the file name) |
| `medium` | `monitor`, `paper`, `digital` or `archive` |
| `walls` | `ok`, `partial` or `bad`, judged by eye on `_wall.png` |
| `doors_found`, `doors_total` | Doors the model marked on a real door, and doors on the plan |
| `doors_extra` | Door marks that are not on a door |
| `windows_found`, `windows_total`, `windows_extra` | The same for windows |
| `confidence` | How sure the count is: `high`, `medium`, `low-medium`, `low`, or `n/a` when nothing was counted |
| `notes` | What worked, what failed |

How to count: an opening in a wall is one door, even a double door. Windows are counted by the gap in the wall, so two windows with wall between them are two. Marks that are only specks are ignored. Blank counts mean the plan does not show doors or windows in a way anyone can read (old prints), or draws none.

The counts were made by reading the side-by-side result images, not on site. Rows marked `low` come from dense drawings and are approximate, mainly the totals.

Run the whole set:

```
python -m ml.model.infer ml/data/photos/*.jpg --weights ml/weights/model_best_val_loss_var.pkl --out ml/out
```

Shanto's flattening is not in yet, so for now photos go in as taken. Once flattening exists, run the set again on the flattened images and keep both results: the difference shows what flattening is worth.

## Results

First results on the photo set. Default mode (four rotations), CubiCasa5K weights as published.

| Measure | Result |
| --- | --- |
| Photos in the set | 28 |
| Walls `ok` / `partial` / `bad` | 18 / 9 / 1 |
| Doors found / total, 9 photos with solid counts | 47 / 62, 5 wrong marks |
| Windows found / total, same 9 photos | 49 / 54, 8 wrong marks |
| Doors found / total, all 19 photos counted (approximate) | 126 / 201 |
| Windows found / total, all 20 photos counted (approximate) | 169 / 202 |
| Median time per photo, Windows 10 PC, CPU | 12.9 s (3.7 s single pass) |
| Time per photo, Colab T4 | 0.3 to 0.8 s |

The nine photos with solid counts are p11, p12, p13, p18, p19, p20, p21, p25 and p30. The other counts are rougher, so read the all-photos rows as a guide only.

What works:

- Walls, on clean plans and on phone photos with shadow, creases or rotation. The outline and the inner walls close on most photos.
- Plans that draw doors with a swing arc and windows as a line in the wall: p13, p20, p21 and p30 together have 21 of 22 doors and 24 of 24 windows found.
- Speed on a GPU, and on the PC in single-pass mode.

What fails:

- Old prints (p01, p02, p05 to p07, p26, p27). They draw doors as gaps and windows in an older style, so doors and windows cannot be scored, even by eye. The walls are fine on some (p03, p06, p07).
- Page clutter. On p05 the photo and the text on the magazine page are read as walls. Cropping to the plan should fix this.
- Dense drawings (p08, p09, p14, p15, p17). Many doors are missed, p15 most of all, and windows are split into pieces.
- Glass walls and rows of thin marks (p18, p22, p24) give several window marks for one opening.
- Speed in the default mode: about 13 s per photo on the PC, over the 10 s target.

One good and one bad example for the software lab demo:

- Good: p13 or p30 (our own print). Not chosen yet.
- Bad: p05 or p19. Not chosen yet.
