"""Minimal ComfyUI API client for the flux-identity prototype."""
from __future__ import annotations

import json
import time
import uuid
import urllib.error
import urllib.parse
import urllib.request
from copy import deepcopy
from pathlib import Path


def _post_json(url: str, payload: dict) -> dict:
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _get_json(url: str) -> dict:
    with urllib.request.urlopen(url, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _upload_image(comfy_url: str, path: Path, *, subfolder: str = "", image_type: str = "input") -> str:
    """Upload image; returns ComfyUI filename."""
    import mimetypes

    boundary = uuid.uuid4().hex
    mime = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    body = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="image"; filename="{path.name}"\r\n'
        f"Content-Type: {mime}\r\n\r\n"
    ).encode("utf-8") + path.read_bytes() + f"\r\n--{boundary}--\r\n".encode("utf-8")

    req = urllib.request.Request(
        f"{comfy_url.rstrip('/')}/upload/image",
        data=body,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        result = json.loads(resp.read().decode("utf-8"))
    return result["name"]


def _patch_workflow(
    workflow: dict,
    *,
    portrait_name: str,
    upload_name: str,
    strength: float,
) -> dict:
    """Patch placeholders in exported API workflow.

    Expected node inputs (set in your exported workflow):
      - LoadImage node titled \"PORTRAIT\" → inputs.image
      - LoadImage node titled \"UPLOAD\" → inputs.image
      - KSampler / inpaint node with denoise input titled \"STRENGTH\"
    """
    wf = deepcopy(workflow)
    for node in wf.values():
        if not isinstance(node, dict):
            continue
        meta = node.get("_meta", {}) or {}
        title = (meta.get("title") or "").upper()
        inputs = node.get("inputs") or {}
        if title == "PORTRAIT" and "image" in inputs:
            inputs["image"] = portrait_name
        elif title == "UPLOAD" and "image" in inputs:
            inputs["image"] = upload_name
        elif title == "STRENGTH" and "denoise" in inputs:
            inputs["denoise"] = strength
        elif title == "STRENGTH" and "strength" in inputs:
            inputs["strength"] = strength
    return wf


def queue_workflow(
    *,
    comfy_url: str,
    workflow: dict,
    portrait_path: Path,
    upload_path: Path,
    strength: float,
    output_path: Path,
    poll_seconds: float = 1.0,
    timeout_seconds: float = 600.0,
) -> Path:
    base = comfy_url.rstrip("/")
    portrait_name = _upload_image(base, portrait_path)
    upload_name = _upload_image(base, upload_path)
    patched = _patch_workflow(
        workflow,
        portrait_name=portrait_name,
        upload_name=upload_name,
        strength=strength,
    )
    client_id = uuid.uuid4().hex
    queued = _post_json(
        f"{base}/prompt",
        {"prompt": patched, "client_id": client_id},
    )
    prompt_id = queued["prompt_id"]

    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        history = _get_json(f"{base}/history/{prompt_id}")
        if prompt_id in history:
            outputs = history[prompt_id].get("outputs", {})
            for node_out in outputs.values():
                for img in node_out.get("images", []):
                    params = urllib.parse.urlencode(
                        {
                            "filename": img["filename"],
                            "subfolder": img.get("subfolder", ""),
                            "type": img.get("type", "output"),
                        }
                    )
                    url = f"{base}/view?{params}"
                    with urllib.request.urlopen(url, timeout=60) as resp:
                        output_path.write_bytes(resp.read())
                    return output_path
            raise RuntimeError(f"ComfyUI finished but no image in history for {prompt_id}")
        time.sleep(poll_seconds)

    raise TimeoutError(f"ComfyUI prompt {prompt_id} timed out after {timeout_seconds}s")


def ping(comfy_url: str) -> bool:
    try:
        _get_json(f"{comfy_url.rstrip('/')}/system_stats")
        return True
    except (urllib.error.URLError, TimeoutError, OSError):
        return False
