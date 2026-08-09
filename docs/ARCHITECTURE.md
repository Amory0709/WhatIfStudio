# Architecture

## Frontend (apps/web, Next.js 14)
- Routes: /, /swap/[id], /print/[id]
- Tailwind + Framer Motion
- Camera via getUserMedia(); upload via file input
- POST /api/swap -> watermarked PNG

## Backend (apps/api, FastAPI)
- /api/swap accepts source_id + face file
- Ethics gate: NSFW, face detection, MIME, size
- Calls modules.processors.frame.face_swapper.process_frames
- Burns SLB watermark via Pillow

## Engine
Vendored Deep-Live-Cam modules/ package.

## Ethics gate
apps/api/app/ethics.py refuses any request failing NSFW, face detection, or file validation.
