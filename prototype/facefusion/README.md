# PROTOTYPE: FaceFusion eval

> **Question:** Does FaceFusion beat booth InSwapper on Identity + Naturalness? See `QUESTION.md`.

## Quick start (no FaceFusion install)

Uses your selfie + in-repo **FF box/XSeg masks** (`ff_native`) vs current booth API.

```powershell
# From repo root — selfie at .scratch/diagnose/my-upload.jpg (or diagnose-selfie page)
python prototype/facefusion/run.py check
python prototype/facefusion/run.py all --upload .scratch/diagnose/my-upload.jpg

npm run prototype:facefusion:serve
# Open http://127.0.0.1:8766/eval.html
```

Outputs: `prototype/facefusion/outputs/booth/` and `outputs/ff_native/`.

## Optional: official FaceFusion CLI

```powershell
powershell -ExecutionPolicy Bypass -File prototype/facefusion/setup.ps1
python prototype/facefusion/run.py cli ff_cli_inswapper --upload .scratch/diagnose/my-upload.jpg
```

Models: reuse `apps/api/engine/models/` where possible; first CLI run may download extras into FaceFusion `.assets`.

## Commands

| Command | What |
|---------|------|
| `run.py check` | Upload + gallery + CLI status |
| `run.py booth` | Current API pipeline only |
| `run.py native` | FF masks in-repo |
| `run.py all` | booth + native + CLI if installed |
| `run.py cli ff_cli_inswapper` | Official FaceFusion headless |

## Score

`eval.html` loads `manifest.json`. Rate Identity / Naturalness 1–5 per portrait per method.

Throwaway — fold winners into `apps/api` after eval.
