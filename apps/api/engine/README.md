# Vendored engine

This folder contains a copy of the Deep-Live-Cam `modules/` package used by the
API. We do not modify it; the API just imports its swap functions.

## Setup

1. Download the face-swap model into `./models/`:
   ```
   # See https://github.com/hacksider/Deep-Live-Cam for the link
   # to inswapper_128.onnx (and optionally inswapper_128_fp16.onnx)
   ```

2. If you want to refresh from upstream:
   ```bash
   rsync -a /path/to/Deep-Live-Cam/modules/ ./modules/
   ```

The API only needs `modules/` + `models/` — it does not run the GUI.
