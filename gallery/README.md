# /public/gallery

JPEG portraits loaded by the web front-end (`apps/web/lib/gallery.ts`) and the FastAPI `/api/swap` endpoint. Metadata (title, artist, year, palette) lives in `data/gallery.json`; this directory holds the image files only.

## Contents

14 photos, in four groups:

- **Tier 2 — People** (9): industrial operations — armoring, CHX manufacturing/production, offshore drilling, land operations, lead extrusion.
- **Tier 2 — Project** (3): Electris Completions at the CHPC, Ardmore (Houston).
- **Tier 1 — Operating base** (1): `tier-1-operating-base-coca-amr-4904.jpg`.
- **Tier 2 — Lab** (1): `tier-2-people-lab-NEPEC-sugar-land-NAL-7R55891.jpg`.

Per-file `title` and `palette` are defined in `data/gallery.json`.

## Naming convention

All filenames are **kebab-case slugs**: lowercase, with spaces and underscores replaced by `-`. The `id` field in `data/gallery.json` is the filename **without** the extension. `gallery.ts` resolves `id + ".jpg" / ".jpeg" / ".png" / ".webp"` against this directory, so the id and the basename must match exactly.

Example:
- `data/gallery.json` → `"id": "tier-2-people-drilling-offshore-operations-el-nido-asa-3917-4inch"`
- file on disk → `tier-2-people-drilling-offshore-operations-el-nido-asa-3917-4inch.jpg`

## Adding new art

1. Drop a `.jpg` / `.jpeg` / `.png` / `.webp` into this directory using a kebab-case slug as the basename.
2. Add an entry to `data/gallery.json` with `id` equal to that slug (no extension).
3. The swap pipeline picks it up automatically — no code changes needed.