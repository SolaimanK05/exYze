# Geometry JSON v1 review for 22 Nov 2026

Turjo (A) and Abdullah Ibn Yousuf (D) to confirm in team chat. Shanto (E) to confirm photo scaling. Acknowledgment is pending.

Review the [DXF revision fixture](../../backend/app/fixtures/dev_revision_v1.json) against the 19 Nov “01 Architecture and Contracts” specification.

- [ ] Version is 1. Coordinates and lengths are in metres, with the origin at bottom left, x right and y up. DXF converts from drawing units. Photos are scaled before persistence.
- [ ] Walls are directed centrelines with thickness, height, exterior and optional finish/confidence. Opening offsets run from the wall start to the near edge. Opening numbers start at 1 per wall.
- [ ] Document keys are unique. New import elements omit database IDs. Stored elements carry IDs. Opening and room-boundary wall references and item room references can use keys or IDs.
- [ ] Import may send empty rooms. Labels supply room names. Furniture uses catalogue codes and can omit its room on import. Confidence below 0.6 raises a review flag during import.
- [ ] The fixture follows the written rule, with `scale: null` for DXF. The printed example instead gives DXF an OCR scale. Confirm the written rule with A and E. Photo scale uses OCR or manual input.

Record Turjo’s acknowledgment and date here once received.
