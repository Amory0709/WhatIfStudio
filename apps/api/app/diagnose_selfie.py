"""Local dev selfie capture for swap identity diagnostics."""
from __future__ import annotations

import io
import logging
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse
from PIL import Image

from .ethics import validate_face_upload

log = logging.getLogger("whatif.diagnose_selfie")

REPO_ROOT = Path(__file__).resolve().parents[3]
DIAGNOSE_DIR = REPO_ROOT / ".scratch" / "diagnose"
UPLOAD_PATH = DIAGNOSE_DIR / "my-upload.jpg"

router = APIRouter(tags=["diagnose"])


@router.get("/diagnose-selfie", response_class=HTMLResponse)
async def diagnose_selfie_page() -> str:
    return _PAGE_HTML


@router.post("/api/diagnose/selfie")
async def save_diagnose_selfie(face: UploadFile = File(...)) -> JSONResponse:
    raw = await face.read()
    content_type = face.content_type or "image/jpeg"
    validate_face_upload(raw, content_type)

    try:
        img = Image.open(io.BytesIO(raw)).convert("RGB")
    except Exception as exc:
        raise HTTPException(400, "Unreadable image") from exc

    DIAGNOSE_DIR.mkdir(parents=True, exist_ok=True)
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=92)
    UPLOAD_PATH.write_bytes(buf.getvalue())

    log.info("diagnose selfie saved: %s (%d bytes)", UPLOAD_PATH, UPLOAD_PATH.stat().st_size)
    return JSONResponse(
        {
            "ok": True,
            "path": str(UPLOAD_PATH),
            "size_bytes": UPLOAD_PATH.stat().st_size,
        }
    )


_PAGE_HTML = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>诊断自拍 · WhatIf Studio</title>
  <style>
    :root {
      color-scheme: dark;
      --bg: #0f1115;
      --panel: #1a1d24;
      --text: #f4f4f5;
      --muted: #a1a1aa;
      --accent: #3b82f6;
      --accent-hover: #2563eb;
      --danger: #ef4444;
      --ok: #22c55e;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      min-height: 100vh;
      font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
      background: var(--bg);
      color: var(--text);
      display: flex;
      justify-content: center;
      padding: 24px 16px 40px;
    }
    main {
      width: min(420px, 100%);
      display: flex;
      flex-direction: column;
      gap: 16px;
    }
    h1 { font-size: 1.25rem; margin: 0; }
    p { margin: 0; color: var(--muted); line-height: 1.5; font-size: 0.95rem; }
    .panel {
      background: var(--panel);
      border-radius: 16px;
      padding: 16px;
      display: flex;
      flex-direction: column;
      gap: 12px;
    }
    .viewport {
      position: relative;
      aspect-ratio: 3 / 4;
      border-radius: 12px;
      overflow: hidden;
      background: #000;
    }
    video, img.preview {
      width: 100%;
      height: 100%;
      object-fit: cover;
      display: block;
    }
    video { transform: scaleX(-1); }
    img.preview { display: none; }
    .viewport.has-preview video { display: none; }
    .viewport.has-preview img.preview { display: block; }
    .actions { display: flex; gap: 8px; flex-wrap: wrap; }
    button {
      flex: 1 1 auto;
      min-height: 44px;
      border: none;
      border-radius: 10px;
      font-size: 0.95rem;
      font-weight: 600;
      cursor: pointer;
      padding: 10px 14px;
    }
    button:disabled { opacity: 0.45; cursor: not-allowed; }
    #captureBtn { background: var(--accent); color: #fff; }
    #captureBtn:hover:not(:disabled) { background: var(--accent-hover); }
    #retakeBtn, #saveBtn { background: #2a2f3a; color: var(--text); }
    #saveBtn:not(:disabled) { background: var(--ok); color: #052e16; }
    .status {
      min-height: 1.25rem;
      font-size: 0.9rem;
      color: var(--muted);
    }
    .status.error { color: var(--danger); }
    .status.ok { color: var(--ok); }
    code {
      display: block;
      margin-top: 8px;
      padding: 10px 12px;
      background: #0b0d11;
      border-radius: 8px;
      font-size: 0.8rem;
      overflow-x: auto;
      white-space: pre-wrap;
      word-break: break-all;
    }
    .hidden { display: none !important; }
  </style>
</head>
<body>
  <main>
    <header>
      <h1>诊断自拍</h1>
      <p>拍一张正脸照，保存到本地供换脸 identity 诊断脚本使用。</p>
    </header>

    <section class="panel" aria-labelledby="camera-heading">
      <h2 id="camera-heading" class="hidden">Camera</h2>
      <div class="viewport" id="viewport">
        <video id="video" autoplay playsinline muted aria-label="摄像头预览"></video>
        <img id="preview" class="preview" alt="已拍摄的照片预览" />
      </div>
      <div class="actions">
        <button type="button" id="captureBtn">拍照</button>
        <button type="button" id="retakeBtn" class="hidden" disabled>重拍</button>
        <button type="button" id="saveBtn" disabled>保存到项目</button>
      </div>
      <p id="status" class="status" role="status" aria-live="polite"></p>
    </section>

    <section class="panel hidden" id="nextPanel">
      <p><strong>已保存。</strong> 在项目根目录运行：</p>
      <code id="cmdBlock"></code>
    </section>
  </main>

  <script>
    const video = document.getElementById("video");
    const preview = document.getElementById("preview");
    const viewport = document.getElementById("viewport");
    const captureBtn = document.getElementById("captureBtn");
    const retakeBtn = document.getElementById("retakeBtn");
    const saveBtn = document.getElementById("saveBtn");
    const statusEl = document.getElementById("status");
    const nextPanel = document.getElementById("nextPanel");
    const cmdBlock = document.getElementById("cmdBlock");

    let stream = null;
    let blob = null;

    function setStatus(msg, kind) {
      statusEl.textContent = msg || "";
      statusEl.className = "status" + (kind ? " " + kind : "");
    }

    async function startCamera() {
      setStatus("正在打开摄像头…");
      try {
        stream = await navigator.mediaDevices.getUserMedia({
          video: { facingMode: "user", width: { ideal: 720 }, height: { ideal: 960 } },
          audio: false,
        });
        video.srcObject = stream;
        setStatus("对准正脸，点击拍照。");
      } catch (err) {
        setStatus(err.message || "无法访问摄像头", "error");
        captureBtn.disabled = true;
      }
    }

    function stopCamera() {
      if (stream) {
        stream.getTracks().forEach((t) => t.stop());
        stream = null;
      }
      video.srcObject = null;
    }

    captureBtn.addEventListener("click", () => {
      if (!video.videoWidth) return;
      const canvas = document.createElement("canvas");
      canvas.width = video.videoWidth;
      canvas.height = video.videoHeight;
      const ctx = canvas.getContext("2d");
      ctx.translate(canvas.width, 0);
      ctx.scale(-1, 1);
      ctx.drawImage(video, 0, 0);
      canvas.toBlob(
        (b) => {
          if (!b) {
            setStatus("拍照失败", "error");
            return;
          }
          blob = b;
          preview.src = URL.createObjectURL(b);
          viewport.classList.add("has-preview");
          stopCamera();
          captureBtn.classList.add("hidden");
          retakeBtn.classList.remove("hidden");
          retakeBtn.disabled = false;
          saveBtn.disabled = false;
          setStatus("满意就点「保存到项目」。");
        },
        "image/jpeg",
        0.92,
      );
    });

    retakeBtn.addEventListener("click", async () => {
      blob = null;
      preview.removeAttribute("src");
      viewport.classList.remove("has-preview");
      captureBtn.classList.remove("hidden");
      retakeBtn.classList.add("hidden");
      saveBtn.disabled = true;
      nextPanel.classList.add("hidden");
      await startCamera();
    });

    saveBtn.addEventListener("click", async () => {
      if (!blob) return;
      saveBtn.disabled = true;
      setStatus("正在保存…");
      try {
        const fd = new FormData();
        fd.append("face", blob, "my-upload.jpg");
        const res = await fetch("/api/diagnose/selfie", { method: "POST", body: fd });
        const data = await res.json().catch(() => ({}));
        if (!res.ok) {
          throw new Error(data.detail || "保存失败");
        }
        setStatus("已保存到 " + data.path, "ok");
        cmdBlock.textContent =
          ".\\\\apps\\\\api\\\\.venv\\\\Scripts\\\\python.exe scripts\\\\diagnose_swap_identity.py\\n" +
          ".\\\\apps\\\\api\\\\.venv\\\\Scripts\\\\python.exe scripts\\\\diagnose_swap_stages.py";
        nextPanel.classList.remove("hidden");
      } catch (err) {
        setStatus(err.message || "保存失败", "error");
        saveBtn.disabled = false;
      }
    });

    window.addEventListener("beforeunload", stopCamera);
    startCamera();
  </script>
</body>
</html>
"""
