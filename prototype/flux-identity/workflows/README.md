# ComfyUI workflows (export yourself)

The prototype does **not** ship pinned ComfyUI graphs — node packs differ by install. Export **API format** from ComfyUI after you build:

1. **PuLID-Flux face inpaint** — identity from upload, portrait supplies scene/clothes mask  
2. **InstantID-Flux face inpaint** — same layout for fair comparison  

## Node titles (required for `comfy_client.py`)

Rename these nodes in ComfyUI before export:

| Node title | Role |
|------------|------|
| `PORTRAIT` | LoadImage — gallery portrait |
| `UPLOAD` | LoadImage — visitor selfie |
| `STRENGTH` | KSampler (or inpaint node) — wire `denoise` or `strength` |

Save as:

- `pulid_inpaint_api.json`
- `instantid_inpaint_api.json`

## Suggested packs

- [PuLID-ComfyUI](https://github.com/balakong/ComfyUI_PuLID_Flux) or current PuLID-Flux nodes for your Comfy version  
- [InstantID ComfyUI](https://github.com/cubiq/ComfyUI_InstantID) — check Flux-compatible forks/workflows  

## Manual path (no API)

Generate PNGs in ComfyUI, name files:

```text
<tier-id>_strength_0.45.png
<tier-id>_strength_0.65.png
<tier-id>_strength_0.85.png
```

Then:

```powershell
python prototype/flux-identity/run.py import --method pulid_inpaint --dir C:\path\to\exports
python prototype/flux-identity/run.py manifest
```

## img2img round (optional)

Only after inpaint scores — top config per method at denoise ~0.25–0.35. Import into `pulid_img2img` / `instantid_img2img` folders the same way.
