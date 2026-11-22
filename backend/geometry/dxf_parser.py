"""DXF parser (Package A, Sprint 2).

Reads the model space of a DXF file and returns a ``ParseResult``:

* ``result.geometry``  exactly the geometry format from 01 Architecture and
                       Contracts (version, units, source, walls, openings,
                       rooms, labels, items, flags, scale). Nothing extra.
                       This is what gets stored in upload.result.
* ``result.raw``       Python-side data for the rest of Package A and for
                       Solaiman, not part of the shared format:
    - ``lines``    every straight segment: LINE, LWPOLYLINE/POLYLINE segments,
                   and the lines inside exploded blocks (input to wall pairing)
    - ``arcs``     arcs with centre, radius and angles (usually door swings;
                   never treated as walls)
    - ``inserts``  every INSERT with block name, position, rotation and scale
    - ``skipped``  entities the parser could not read, with the reason

TEXT and MTEXT become ``geometry["labels"]``, used later to name rooms.

All lengths are metres, rounded to 3 decimals (the database stores wall
coordinates as numeric(9,3)). Angles are degrees, 0 <= a < 360,
counter-clockwise from +x.

Nested blocks are exploded too (the inner INSERTs are listed with
``nested: true``).

Wall pairing, snapping and junctions come in Sprint 3. Until then,
``provisional_walls=True`` turns each raw line into a low-confidence wall so
the 2D and 3D views have something to draw.

Command line (prints the geometry format as JSON):
    uv run python -m geometry.dxf_parser plan.dxf --walls --out plan.json
    uv run python -m geometry.dxf_parser plan.dxf --raw-out plan_raw.json
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import ezdxf
from ezdxf.document import Drawing
from ezdxf.entities import DXFEntity
from ezdxf.lldxf.const import DXFError

from geometry.units import resolve_units

DECIMALS = 3
LAYER_HINT_WORD = "WALL"  # layer names containing this raise confidence (hint only)
DEFAULT_WALL_THICKNESS = 0.125
DEFAULT_WALL_HEIGHT = 3.0
LOW_CONFIDENCE = 0.5
MAX_BLOCK_DEPTH = 10  # protects against blocks that contain themselves


# --------------------------------------------------------------------------
# Reading the file
# --------------------------------------------------------------------------
@dataclass
class ParseResult:
    geometry: dict[str, Any]  # the geometry format from 01, nothing more
    raw: dict[str, Any]  # lines, arcs, inserts, skipped (Python-side only)


def read_dxf(path: str | Path) -> Drawing:
    """Open a DXF file. If it is damaged, fall back to ezdxf's recovery mode."""
    try:
        return ezdxf.readfile(str(path))
    except (DXFError, OSError):
        from ezdxf import recover

        doc, _auditor = recover.readfile(str(path))
        return doc


def parse_dxf(path: str | Path, provisional_walls: bool = False) -> ParseResult:
    """Parse a DXF file into the geometry format."""
    return parse_document(read_dxf(path), provisional_walls=provisional_walls)


# --------------------------------------------------------------------------
# Collecting entities (all in drawing units, converted at the end)
# --------------------------------------------------------------------------
class _Collector:
    def __init__(self) -> None:
        self.lines: list[dict[str, Any]] = []
        self.arcs: list[dict[str, Any]] = []
        self.inserts: list[dict[str, Any]] = []
        self.labels: list[dict[str, Any]] = []
        self.skipped: list[dict[str, str]] = []

    def skip(self, entity: DXFEntity | None, why: str) -> None:
        self.skipped.append(
            {
                "type": entity.dxftype() if entity is not None else "?",
                "handle": entity.dxf.handle if entity is not None else "",
                "reason": why,
            }
        )

    # -- geometry ---------------------------------------------------------
    def add_geometry(
        self, e: DXFEntity, origin: str, fallback_layer: str, depth: int = 0
    ) -> None:
        """Collect a LINE, ARC, LWPOLYLINE or POLYLINE (and, inside blocks,
        nested INSERTs). Anything else is ignored."""
        kind = e.dxftype()
        layer = e.dxf.get("layer", "0")
        if layer == "0":  # layer 0 inside a block means "use the INSERT's layer"
            layer = fallback_layer

        if kind == "LINE":
            s, t = e.dxf.start, e.dxf.end
            self.lines.append(
                {
                    "x1": s.x,
                    "y1": s.y,
                    "x2": t.x,
                    "y2": t.y,
                    "layer": layer,
                    "origin": origin,
                }
            )
        elif kind == "ARC":
            self.arcs.append(_arc_to_wcs(e, layer, origin))
        elif kind in ("LWPOLYLINE", "POLYLINE"):
            if kind == "POLYLINE" and not e.is_2d_polyline:
                self.skip(e, "3D polyline ignored")
                return
            # virtual_entities() yields LINE and ARC (for bulges) in WCS
            for part in e.virtual_entities():
                self.add_geometry(part, origin, layer, depth)
        elif kind == "INSERT":  # only reached for blocks nested inside blocks
            self.add_insert(e, depth=depth + 1, origin=origin)

    # -- inserts ----------------------------------------------------------
    def add_insert(self, ins: DXFEntity, depth: int = 0, origin: str = "") -> None:
        if depth > MAX_BLOCK_DEPTH:
            self.skip(ins, f"blocks nested deeper than {MAX_BLOCK_DEPTH}; not exploded")
            return
        name = ins.dxf.name
        layer = ins.dxf.get("layer", "0")
        p = ins.dxf.insert
        self.inserts.append(
            {
                "block": name,
                "x": p.x,
                "y": p.y,
                "rotation": ins.dxf.get("rotation", 0.0) % 360.0,
                "xscale": ins.dxf.get("xscale", 1.0),
                "yscale": ins.dxf.get("yscale", 1.0),
                "layer": layer,
                "nested": depth > 0,
            }
        )
        try:
            for part in ins.virtual_entities():
                self.add_geometry(part, f"block:{name}", layer, depth)
        except Exception as exc:  # noqa: BLE001
            # Real files contain broken blocks. Record it, never hide it.
            self.skip(ins, f"could not explode block {name!r}: {exc}")

    # -- text -------------------------------------------------------------
    def add_text(self, e: DXFEntity) -> None:
        if e.dxftype() == "TEXT":
            text = e.dxf.get("text", "")
            if e.dxf.get("halign", 0) or e.dxf.get("valign", 0):
                p = e.dxf.get("align_point", e.dxf.insert)
            else:
                p = e.dxf.insert
        else:  # MTEXT
            text = e.plain_text()
            p = e.dxf.insert
        text = " ".join(text.split())  # collapse newlines and runs of spaces
        if text:
            self.labels.append({"text": text, "x": p.x, "y": p.y})


def _arc_to_wcs(arc: DXFEntity, layer: str, origin: str) -> dict[str, Any]:
    """Arc centre and angles in world coordinates (handles mirrored arcs whose
    extrusion direction is (0, 0, -1))."""
    c = arc.ocs().to_wcs(arc.dxf.center)
    start, end = arc.dxf.start_angle, arc.dxf.end_angle
    if arc.dxf.extrusion.z < 0:  # OCS x axis is mirrored: 180 - angle, swapped
        start, end = 180.0 - end, 180.0 - start
    return {
        "cx": c.x,
        "cy": c.y,
        "radius": arc.dxf.radius,
        "start_angle": start % 360.0,
        "end_angle": end % 360.0,
        "layer": layer,
        "origin": origin,
    }


# --------------------------------------------------------------------------
# Building the output
# --------------------------------------------------------------------------
def _r(value: float) -> float:
    return round(value, DECIMALS) + 0.0  # + 0.0 turns -0.0 into 0.0


def _extent(c: _Collector) -> float:
    xs: list[float] = []
    ys: list[float] = []
    for ln in c.lines:
        xs += [ln["x1"], ln["x2"]]
        ys += [ln["y1"], ln["y2"]]
    for a in c.arcs:
        xs += [a["cx"] - a["radius"], a["cx"] + a["radius"]]
        ys += [a["cy"] - a["radius"], a["cy"] + a["radius"]]
    for i in c.inserts:
        xs.append(i["x"])
        ys.append(i["y"])
    if not xs:
        return 0.0
    return max(max(xs) - min(xs), max(ys) - min(ys))


def _layer_hint(layer: str) -> bool:
    return LAYER_HINT_WORD in layer.upper()


def parse_document(doc: Drawing, provisional_walls: bool = False) -> ParseResult:
    """Parse an open ezdxf document (model space only) into the geometry format."""
    c = _Collector()
    msp = doc.modelspace()

    for e in msp:
        kind = e.dxftype()
        try:
            if kind in ("LINE", "ARC", "LWPOLYLINE", "POLYLINE"):
                c.add_geometry(e, origin=kind.lower(), fallback_layer="0")
            elif kind == "INSERT":
                c.add_insert(e)
            elif kind in ("TEXT", "MTEXT"):
                c.add_text(e)
        except Exception as exc:  # noqa: BLE001  (recorded, not hidden)
            c.skip(e, str(exc))

    code = doc.header.get("$INSUNITS")
    units = resolve_units(code, _extent(c))
    k = units.factor

    lines = []
    for ln in c.lines:
        x1, y1, x2, y2 = (_r(ln[key] * k) for key in ("x1", "y1", "x2", "y2"))
        if x1 == x2 and y1 == y2:  # zero length after rounding: useless
            continue
        lines.append(
            {
                "x1": x1,
                "y1": y1,
                "x2": x2,
                "y2": y2,
                "layer": ln["layer"],
                "origin": ln["origin"],
                "layer_hint": _layer_hint(ln["layer"]),
            }
        )

    arcs = [
        {
            "cx": _r(a["cx"] * k),
            "cy": _r(a["cy"] * k),
            "radius": _r(a["radius"] * k),
            "start_angle": round(a["start_angle"], 3),
            "end_angle": round(a["end_angle"], 3),
            "layer": a["layer"],
            "origin": a["origin"],
        }
        for a in c.arcs
    ]

    inserts = [
        {
            "block": i["block"],
            "x": _r(i["x"] * k),
            "y": _r(i["y"] * k),
            "rotation": round(i["rotation"], 3),
            "xscale": i["xscale"],
            "yscale": i["yscale"],
            "layer": i["layer"],
            "nested": i["nested"],
        }
        for i in c.inserts
    ]

    labels = [
        {"text": t["text"], "x": _r(t["x"] * k), "y": _r(t["y"] * k)} for t in c.labels
    ]

    flags = []
    if units.assumed:
        # review_flag.element_kind only allows wall/opening/room/item/scale
        flags.append(
            {"element_kind": "scale", "element_ref": "dxf", "reason": units.reason}
        )

    geometry: dict[str, Any] = {
        "version": 1,
        "units": "m",
        "source": "dxf",
        "walls": lines_to_provisional_walls(lines) if provisional_walls else [],
        "openings": [],
        "rooms": [],
        "labels": labels,
        "items": [],
        "flags": flags,
        "scale": None,
    }
    raw: dict[str, Any] = {
        "source_units_code": code,
        "metres_per_unit": k,
        "units_assumed": units.assumed,
        "lines": lines,
        "arcs": arcs,
        "inserts": inserts,
        "skipped": c.skipped,
    }
    return ParseResult(geometry=geometry, raw=raw)


# --------------------------------------------------------------------------
# Provisional walls (until real wall pairing exists in Sprint 3)
# --------------------------------------------------------------------------
def lines_to_provisional_walls(lines: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Turn raw lines into low-confidence walls so 2D/3D can draw something.

    Uses lines drawn directly in model space (not inside blocks, which are
    mostly furniture). If any of those are on a layer that looks like a wall
    layer, only those are used. Each wall gets confidence 0.5 and the default
    thickness, as the spec says for unpaired lines.
    """
    candidates = [ln for ln in lines if not ln["origin"].startswith("block:")]
    hinted = [ln for ln in candidates if ln["layer_hint"]]
    chosen = hinted or candidates
    return [
        {
            "key": f"w{n}",
            "x1": ln["x1"],
            "y1": ln["y1"],
            "x2": ln["x2"],
            "y2": ln["y2"],
            "thickness": DEFAULT_WALL_THICKNESS,
            "height": DEFAULT_WALL_HEIGHT,
            "exterior": False,
            "confidence": LOW_CONFIDENCE,
        }
        for n, ln in enumerate(chosen, start=1)
    ]


# --------------------------------------------------------------------------
# Command line
# --------------------------------------------------------------------------
def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="Parse a DXF file into exYze geometry JSON"
    )
    ap.add_argument("dxf", help="path to the .dxf file")
    ap.add_argument(
        "--walls", action="store_true", help="add provisional walls from raw lines"
    )
    ap.add_argument(
        "--out", help="write the geometry JSON to this file instead of stdout"
    )
    ap.add_argument(
        "--raw-out", help="also write the raw lines/arcs/inserts JSON to this file"
    )
    args = ap.parse_args(argv)

    result = parse_dxf(args.dxf, provisional_walls=args.walls)
    if args.raw_out:
        Path(args.raw_out).write_text(
            json.dumps(result.raw, indent=2), encoding="utf-8"
        )
    text = json.dumps(result.geometry, indent=2)
    if args.out:
        Path(args.out).write_text(text, encoding="utf-8")
    else:
        sys.stdout.write(text + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())