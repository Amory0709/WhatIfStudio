# /public/gallery

Portrait JPEGs used by both the web front-end and the FastAPI swap endpoint.

## Files

| File             | Role                                                                                       |
| ---------------- | ------------------------------------------------------------------------------------------ |
| `ag-1.jpg` … `ag-12.jpg` | 12 portrait photos cycled across the 50-card 3D gallery track (1:1 from the AG App demo). All under 250 KB. |
| `amber-1.jpg`   | Curated gallery portrait used as a face-swap **target** (the artwork the user's face is composited onto). Real photo, 2.3 MB. |
| `salt-2.jpg`    | Real demo **face source** — a portrait of a person whose face is supplied to the swap engine. 1.0 MB. |

## Naming convention

`<slug>-<n>.jpg` where `<slug>` is the palette label (`amber`, `salt`, etc.) and `<n>` is the variant number. The FastAPI `/api/swap` endpoint looks up the target by the artwork's `id` field, e.g. `source_id=amber-1` → `/public/gallery/amber-1.jpg`.

## Adding new art

Drop a JPEG (or PNG/WebP) into this directory and ensure its filename matches an artwork id from `apps/web/lib/gallery.ts`. The swap pipeline supports `.jpg`, `.jpeg`, `.png`, and `.webp` extensions.
