# Furniture catalogue

The fixed set of 25 furniture items. Decoration only, no prices, no user uploads. This list becomes the `catalog_item` table (seed file in Sprint 3) and is what `GET /api/catalog` returns.

Sizes are the overall bounding box in metres: width along the item's left-right axis, depth front to back, height from the floor. The columns match `catalog_item` (`code`, `name`, `category`, `width_m`, `depth_m`, `height_m`, `model_path`).

| Code | Name | Category | Width | Depth | Height |
| --- | --- | --- | --- | --- | --- |
| `bed_single` | Single bed | bedroom | 0.90 | 2.00 | 0.90 |
| `bed_double` | Double bed | bedroom | 1.50 | 2.00 | 0.90 |
| `wardrobe` | Wardrobe | bedroom | 1.20 | 0.60 | 2.10 |
| `bedside_table` | Bedside table | bedroom | 0.45 | 0.40 | 0.55 |
| `sofa_3` | Sofa (3-seat) | living | 2.10 | 0.90 | 0.85 |
| `armchair` | Armchair | living | 0.85 | 0.85 | 0.85 |
| `tv` | TV on stand | living | 1.10 | 0.25 | 0.70 |
| `tv_unit` | TV unit | living | 1.50 | 0.40 | 0.50 |
| `coffee_table` | Coffee table | living | 1.00 | 0.55 | 0.40 |
| `kitchen_counter` | Kitchen counter | kitchen | 1.20 | 0.60 | 0.90 |
| `stove` | Stove | kitchen | 0.60 | 0.60 | 0.90 |
| `fridge` | Fridge | kitchen | 0.70 | 0.70 | 1.80 |
| `kitchen_sink` | Kitchen sink | kitchen | 0.80 | 0.60 | 0.90 |
| `toilet` | Toilet | bathroom | 0.40 | 0.70 | 0.80 |
| `basin` | Basin | bathroom | 0.55 | 0.45 | 0.85 |
| `shower` | Shower | bathroom | 0.90 | 0.90 | 2.00 |
| `bathtub` | Bathtub | bathroom | 1.70 | 0.75 | 0.60 |
| `dining_table` | Dining table | dining | 1.60 | 0.90 | 0.75 |
| `dining_chair` | Dining chair | dining | 0.45 | 0.50 | 0.90 |
| `desk` | Desk | other | 1.20 | 0.60 | 0.75 |
| `office_chair` | Office chair | other | 0.60 | 0.60 | 1.00 |
| `bookshelf` | Bookshelf | other | 0.80 | 0.30 | 1.80 |
| `plant` | Plant | other | 0.40 | 0.40 | 1.00 |
| `rug` | Rug | other | 2.00 | 1.40 | 0.02 |
| `shoe_rack` | Shoe rack | other | 0.80 | 0.30 | 0.60 |

Counts per category: bedroom 4, living 5, kitchen 4, bathroom 4, dining 2, other 6.

The sizes are typical real-world values, not measured from the models. They are a proposal until Rakin and Jahidul have looked at them.

## Notes for Rakin and Jahidul

- **No height above the floor.** `placed_item` stores only x, y and rotation, so every item stands on the floor. That is why `tv` is a TV with its own stand, and why the `tv` and `tv_unit` can be placed separately but not stacked.
- **The rug** is 2 cm high so it can sit under other furniture without a separate layer.
- **Model files** go in `frontend/public/models/`, one `.glb` per code, named `<code>.glb`, each under 1 MB. `model_path` would then be `models/<code>.glb`.
- **Scale.** Each model is scaled to the size in the table when it is added, so the viewer can use `width_m`, `depth_m` and `height_m` as the real size.

## Open points to agree

- Which way a model faces at rotation 0, and where its origin is (the centre of its footprint, on the floor, is the obvious choice). This is a contract between the viewer (Rakin), the 2D editor (Jahidul) and the models, so it needs an answer before Sprint 4.
- Whether the sizes above are right for the plans we are importing, which are largely Bangladeshi. Bed and wardrobe sizes in particular may differ.

## Models

All candidates are CC0, so there is no licence issue and no credit is required. Checked from each pack's public page on 21 November 2026.

| Pack | Licence | Formats | Notes |
| --- | --- | --- | --- |
| [Kenney Furniture Kit](https://kenney.nl/assets/furniture-kit) | CC0 | Not stated on the page | 140 files, version 1.0 from 2018 |
| [KayKit Furniture Bits](https://kaylousberg.itch.io/furniture-bits) | CC0 | OBJ, FBX, glTF | Free tier has 50+ low-poly models. Paid tiers add more assets and the source files, not needed here |
| [3D Furniture Pack by mehrasaur](https://opengameart.org/content/3d-furniture-pack-new) | CC0 | blend, OBJ, FBX | 2 beds, 6 chairs, 5 cupboards, 1 desk, 3 sofas, 6 tables, no materials. Would need conversion to glTF |

**Not yet done:** the packs have not been downloaded, so which pack covers which of the 25 items is not confirmed, and the `model file` for each item is not chosen. The pack pages do not list their model names, and Kenney's site refused access from the machine this was written on. The next step is to download the Kenney and KayKit packs, tick off the 25 codes against what they contain, fill the gaps from the third pack or the first-party sources, then check each file size.
