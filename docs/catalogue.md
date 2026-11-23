# Furniture catalogue

The fixed set of 25 furniture items. Decoration only, no prices, no user uploads. This list becomes the `catalog_item` table (seed file in Sprint 3) and is what `GET /api/catalog` returns.

Sizes are the overall bounding box in metres: width along the item's left-right axis, depth front to back, height from the floor. The columns match `catalog_item` (`code`, `name`, `category`, `width_m`, `depth_m`, `height_m`, `model_path`).

| Code | Name | Category | Width | Depth | Height |
| --- | --- | --- | --- | --- | --- |
| `bed_single` | Single bed | bedroom | 1.00 | 1.97 | 0.66 |
| `bed_double` | Double bed | bedroom | 1.67 | 1.97 | 0.66 |
| `wardrobe` | Wardrobe | bedroom | 0.70 | 0.44 | 1.49 |
| `bedside_table` | Bedside table | bedroom | 0.47 | 0.38 | 0.46 |
| `sofa_3` | Sofa (3-seat) | living | 1.71 | 1.43 | 0.80 |
| `armchair` | Armchair | living | 0.86 | 0.72 | 0.80 |
| `tv` | TV on stand | living | 1.20 | 0.22 | 0.80 |
| `tv_unit` | TV unit | living | 1.40 | 0.44 | 0.54 |
| `coffee_table` | Coffee table | living | 1.16 | 0.70 | 0.40 |
| `kitchen_counter` | Kitchen counter | kitchen | 0.75 | 0.79 | 0.79 |
| `stove` | Stove | kitchen | 0.75 | 0.79 | 0.79 |
| `fridge` | Fridge | kitchen | 0.75 | 0.51 | 1.61 |
| `kitchen_sink` | Kitchen sink | kitchen | 0.75 | 0.79 | 0.86 |
| `toilet` | Toilet | bathroom | 0.55 | 0.84 | 0.79 |
| `basin` | Basin | bathroom | 0.59 | 0.51 | 0.98 |
| `shower` | Shower | bathroom | 0.98 | 1.02 | 1.91 |
| `bathtub` | Bathtub | bathroom | 2.08 | 0.98 | 0.74 |
| `dining_table` | Dining table | dining | 1.47 | 0.78 | 0.57 |
| `dining_chair` | Dining chair | dining | 0.35 | 0.35 | 0.82 |
| `desk` | Desk | other | 1.29 | 0.69 | 0.67 |
| `office_chair` | Office chair | other | 0.59 | 0.55 | 1.06 |
| `bookshelf` | Bookshelf | other | 0.70 | 0.44 | 1.54 |
| `plant` | Plant | other | 0.37 | 0.42 | 1.14 |
| `rug` | Rug | other | 2.75 | 1.61 | 0.02 |
| `shoe_rack` | Shoe rack | other | 0.70 | 0.44 | 0.70 |

Counts per category: bedroom 4, living 5, kitchen 4, bathroom 4, dining 2, other 6.

The sizes are the models' own bounding boxes after one uniform scale (see Models below), so they are what the viewer will draw. Several differ from typical real sizes: the Kenney set is stylised, so tables and counters sit a little low and the sofa is deep.

## Notes for Rakin and Jahidul

- **No height above the floor.** `placed_item` stores only x, y and rotation, so every item stands on the floor. That is why `tv` is a TV with its own stand, and why the `tv` and `tv_unit` can be placed separately but not stacked.
- **The rug** is 2 cm high so it can sit under other furniture without a separate layer.
- **Model files** go in `frontend/public/models/`, one `.glb` per code, named `<code>.glb`, each under 1 MB. `model_path` would then be `models/<code>.glb`.
- **Scale.** The whole set uses one scale factor (1 Kenney unit = 0.175 m), so no model is stretched. The viewer can use `width_m`, `depth_m` and `height_m` as the real size.
- **Origin.** Every model stands on the floor with the centre of its footprint at the origin.

## Open points to agree

- Which way a model faces at rotation 0. The origin is settled (see above). The facing direction is not checked yet: it is a contract between the viewer (Rakin), the 2D editor (Jahidul) and the models, so it needs an answer before Sprint 4.
- Whether the sizes above are good enough for the plans we are importing, which are largely Bangladeshi. The wardrobe (0.70 m wide) is small, and the double bed (1.67 m) is wider than the 1.50 m we first assumed.

## Models

All 25 come from one pack, so the style is consistent. The files are in `frontend/public/models/`, one `<code>.glb` each, 347 KB in total and 39 KB at most.

**Pack:** [Kenney Furniture Kit 1.0](https://kenney.nl/assets/furniture-kit), CC0 (the pack's own `License.txt` says so). No credit is required. KayKit Furniture Bits, also CC0, was checked and is not used: it has no kitchen or bathroom items.

| Code | Kenney model |
| --- | --- |
| `bed_single` | `bedSingle` |
| `bed_double` | `bedDouble` |
| `wardrobe` | `bookcaseClosedDoors` |
| `bedside_table` | `cabinetBedDrawerTable` |
| `sofa_3` | `loungeSofaLong` |
| `armchair` | `loungeChair` |
| `tv` | `televisionModern` |
| `tv_unit` | `cabinetTelevision` |
| `coffee_table` | `tableCoffee` |
| `kitchen_counter` | `kitchenCabinet` |
| `stove` | `kitchenStove` |
| `fridge` | `kitchenFridge` |
| `kitchen_sink` | `kitchenSink` |
| `toilet` | `toilet` |
| `basin` | `bathroomSink` |
| `shower` | `shower` |
| `bathtub` | `bathtub` |
| `dining_table` | `table` |
| `dining_chair` | `chair` |
| `desk` | `desk` |
| `office_chair` | `chairDesk` |
| `bookshelf` | `bookcaseOpen` |
| `plant` | `pottedPlant` |
| `rug` | `rugRectangle` |
| `shoe_rack` | `bookcaseOpenLow` |

Weak matches:
- `wardrobe` is a closed bookcase with doors (Kenney has no wardrobe).
- `shoe_rack` is a low open bookcase.
- `kitchen_counter` and `stove` have the same footprint.
- The dining table is low at 0.57 m.

Rakin and Jahidul can ask for a swap if one looks wrong in the viewer.
