"""Generate the geometry v1 fixture for the Sprint 2 DXF browser demo."""

import argparse
import json
from pathlib import Path

from .dxf_parser import lines_to_provisional_walls, parse_dxf

SOURCE = Path(__file__).parent / "tests" / "data" / "plan01.dxf"
TARGET = (
    Path(__file__).resolve().parents[2]
    / "frontend"
    / "src"
    / "model"
    / "demo"
    / "plan01.json"
)
# The declared inch conversion gives a roughly 0.48 m-wide office.
# A ~0.78 drawing-inch door block gives a ~1 m door with this preview scale.
PAPER_SCALE = 50
PLAN_LAYERS = {"0", "MURO-PROY", "MURO-NO SEC"}
SCALE_NOTE = f"Preview scale estimated at 1:{PAPER_SCALE} from a door symbol. Confirm before measuring."


def render_fixture() -> str:
    parsed = parse_dxf(SOURCE)
    plan_lines = [
        line
        for line in parsed.raw["lines"]
        if line["layer"] in PLAN_LAYERS and not line["origin"].startswith("block:")
    ]
    geometry = parsed.geometry
    geometry["walls"] = lines_to_provisional_walls(plan_lines)
    for wall in geometry["walls"]:
        for field in ("x1", "y1", "x2", "y2"):
            wall[field] = round(wall[field] * PAPER_SCALE, 3)
    for label in geometry["labels"]:
        label["x"] = round(label["x"] * PAPER_SCALE, 3)
        label["y"] = round(label["y"] * PAPER_SCALE, 3)
    geometry["flags"].append(
        {"element_kind": "scale", "element_ref": "dxf", "reason": SCALE_NOTE}
    )
    return json.dumps(geometry, indent=2) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check", action="store_true", help="verify the checked-in fixture"
    )
    options = parser.parse_args()
    content = render_fixture()
    if options.check:
        if not TARGET.exists() or TARGET.read_text(encoding="utf-8") != content:
            parser.exit(
                1,
                "Fixture is out of date. Run python -m geometry.export_sprint2_demo.\n",
            )
        print(f"Verified {TARGET.name} against {SOURCE.name}")
    else:
        TARGET.parent.mkdir(parents=True, exist_ok=True)
        TARGET.write_text(content, encoding="utf-8")


if __name__ == "__main__":
    main()
