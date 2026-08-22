# WhatIf Studio

An SLB booth experience: a visitor supplies their face and receives a composite image placing them into a pre-authored gallery portrait.

## Language

**Portrait**:
A fictional, pre-authored gallery image that supplies the outfit, environment, pose, and framing for the composite.
_Avoid_: Target, source image, template (when meaning the gallery side)

**Visitor**:
The person using the booth; identified by the face they upload.
_Avoid_: User (too generic), customer

**Upload**:
The visitor's selfie; supplies identity (who the face should look like).
_Avoid_: Source face, reference photo

**Composite**:
The booth output: the visitor's likeness wearing the portrait's outfit, placed in the portrait's scene.
_Avoid_: Swap result, generated image (too vague)

**Identity**:
How recognizably the composite face matches the visitor in the upload — likeness to the real person.
_Avoid_: Likeness (as a standalone noun in UI copy), embedding

**Scene fidelity**:
How unchanged the portrait's clothes, background, props, and overall composition remain in the composite.
_Avoid_: Pixel-perfect, unchanged (overloaded — specify scene vs face)

**Naturalness**:
How believably the visitor's face sits in the portrait's lighting, skin tone, and texture — not pasted-on.
_Avoid_: Realistic, cinematic (too vague)

**Booth station**:
One physical demo machine running the web UI and calling the composite API. The deployment assumes several stations may run at once.
_Avoid_: Client, kiosk (unless that is the official SLB term)

**Composite job**:
An asynchronous unit of work: one upload applied to one portrait, producing one composite when complete.
_Avoid_: Swap request, task (too generic)

**Eval gate**:
The structured review (Identity, Scene fidelity, Naturalness scored 1–5) that must pass before the production pipeline is replaced.
_Avoid_: QA sign-off, acceptance test

**Identity pipeline**:
The generative system (Flux + PuLID or InstantID) that produces the visitor's face inside a portrait. Replaces the former ONNX face-swap pipeline once the eval gate passes.
_Avoid_: Swap model, swap backend (legacy terms for the old pipeline)
