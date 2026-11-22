# Package C material rate draft

The seven starter materials cover walls, finishes, doors and windows. Rates
are coursework estimates in Bangladeshi taka (BDT) based on the
Dhaka/Mymensingh column of the Bangladesh Public Works Department's
[Schedule of Rates 2022, 2nd revised, Part A: Civil Works][pwd], effective
22 January 2026. Item numbers below refer to that edition.

| Code | Material | Category | Unit | Measured by | Draft BDT per unit | PWD basis |
| --- | --- | --- | --- | --- | ---: | --- |
| `brickwork` | Brickwork with mortar | `masonry` | `m3` | `wall_volume` | 10,377.00 | 04.3, first-class brickwork with mortar |
| `plaster` | Cement plaster, both faces | `plaster` | `m2` | `wall_area` | 324.00 | 15.1.1, 12 mm cement plaster |
| `paint` | Plastic emulsion paint | `paint` | `m2` | `wall_area` | 265.00 | 16.2.1, standard acrylic emulsion |
| `floor_tile` | Floor tiles | `flooring` | `m2` | `floor_area` | 1,769.00 | 06.3.1, matt or rustic floor tiles |
| `skirting` | Tile skirting | `skirting` | `m` | `perimeter` | 139.40 | 06.6.1, wall tile rate used as a proxy for a 100 mm strip |
| `door_flush` | Flush door with frame | `door` | `piece` | `door_count` | 14,566.93 | 12.9.2.1 shutter and 11.1.1.1 timber frame |
| `window_alu` | Aluminium sliding window | `window` | `piece` | `window_count` | 7,463.52 | 14.7.1.1 frame and 14.16.1.2.1 clear glass |

## Conversion assumptions

- Skirting uses one metre of run at 0.10 m high. BDT 1,394/m² × 0.10 m² gives BDT 139.40/m.
- A representative door uses a 0.90 × 2.10 m shutter, BDT 4,325/m², and a three-sided frame of 0.06 × 0.15 m section, BDT 139,274/m³. The 5.10 m frame length and shutter area give BDT 14,566.93 per piece.
- A representative window is 1.20 × 1.20 m. The frame rate of BDT 3,920/m² and 5 mm clear glass rate of BDT 1,263/m² give BDT 7,463.52 per piece. The gross window area approximates the glass area.
- The takeoff measures the two wall faces in `wall_area`. Apply each finish rate once per square metre of that total.

These are baseline estimates for future seed data. Preserve the source item
numbers and assumptions when adding the seed. Label any generated monthly
prices as simulated.

[pwd]: https://ss.pwd.gov.bd/document/sor/Final_SoR_2022%20_2nd_Revised.pdf
