# exYze frontend

React 19 + TypeScript + Vite. The 2D plan view uses react-konva.

## Run it

```
cd frontend
npm install
npm run dev        # http://localhost:5173, /api is proxied to http://localhost:8000
```

## Check it

```
npm run lint
npm test           # Vitest: the drawing maths in src/editor2d/draw.ts
npm run build
```

## Where things are

- `src/model/` — the geometry types (from 01 Architecture) and a sample plan.
- `src/editor2d/` — the read-only 2D view. `draw.ts` holds the geometry maths in metres with y up; `Plan2D.tsx` draws it.
- `src/app/` — pages, layout and the placeholder API in `api.ts`. Each function there names the real endpoint it will call.

The sample plan and the furniture sizes in `placeholderCatalog.ts` stand in for the API and `GET /api/catalog` until those exist.

## Sprint 2 viewer demo

Open `/projects/1/floors/1` and select **3D** to inspect the sample floor with
door and window openings. Drag to orbit, scroll or pinch to zoom, and use
**Reset view** to fit the plan again. The **2D** and **3D** views share the same
geometry v1 document.

Use **Open the parsed DXF demo** to open `/demo/dxf`. This route uses
`plan01.dxf`, the Package A parser's checked-in source drawing. Its geometry
contains provisional walls and labels. The demo retains model-space linework
on layers `0`, `MURO-PROY`, and `MURO-NO SEC` and applies an estimated 1:50
drawing scale based on a door symbol. The page flags the scale for review.
These steps apply only to this preview. Opening detection, room polygons, and
stored revisions use separate workstreams.

To regenerate or check the fixture, run these commands from `backend/` with
the locked backend dependencies installed.

```sh
uv run --locked python -m geometry.export_sprint2_demo
uv run --locked python -m geometry.export_sprint2_demo --check
```
