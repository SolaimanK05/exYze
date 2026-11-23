# Photo capture

The page where a phone photo of a printed plan is taken or chosen, uploaded, and followed until the server has finished with it. Package E.

## Files

| File | What it does |
| --- | --- |
| `CapturePage.tsx` | The page. Takes a `floorId`. |
| `uploadFlow.ts` | The page's state (`reduceFlow`) and `followUpload`, which polls until the upload settles. |
| `uploadApi.ts` | The two backend calls, and the `CaptureApi` type the page depends on. |
| `photoFile.ts` | Checks a chosen file before it is uploaded. |
| `statusText.ts` | The wording for each upload status. |
| `demoApi.ts` | A fake backend for showing the page before the upload endpoint exists. |

## Adding it to the app

The page does not know about the router. In `src/app/App.tsx`, register a route and pass the floor from the URL:

```tsx
const CapturePage = lazy(() => import('../capture/CapturePage').then((m) => ({ default: m.CapturePage })))

function CaptureRoute() {
  return <CapturePage floorId={Number(useParams().floorId)} />
}

// inside <Routes>
<Route path="projects/:projectId/floors/:floorId/capture" element={<Suspense fallback={null}><CaptureRoute /></Suspense>} />
```

## Trying it without a backend

In development, add `?demo` to the page's address. Uploads are then faked and the status moves from queued to processing to done. `?demo=corners` ends with the "corners need adjusting" state and `?demo=fail` ends with a failed import.

To open it on a phone, run `npm run dev -- --host` and use the address Vite prints for your network. Taking a photo with the camera button works over plain http.

## What the page expects from the API

These follow 01 Architecture and Contracts, which does not spell out the field names, so they are written down here.

- `POST /api/floors/{id}/uploads` with multipart fields `file` (the image, untouched) and `source` (`photo`). It answers `{"upload_id": 12, "status": "queued"}`.
- `GET /api/uploads/{id}` answers at least `{"upload_id": 12, "status": "...", "error": null}`, with `status` one of `queued`, `processing`, `waiting_user`, `done`, `failed`.
- Errors are `{"error": "NAME", "message": "..."}`, as in the contract.
