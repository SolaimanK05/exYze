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
