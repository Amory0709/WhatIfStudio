# GitHub Pages preview

The liquid glass preview is published at https://Amory0709.github.io/WhatIfStudio/.
The `liquid-glass-pages` branch contains its source; `gh-pages` contains the static export. The existing `main` branch is preserved.

Build from the repository root:

```sh
npm ci --ignore-scripts
NEXT_PUBLIC_BASE_PATH=/WhatIfStudio npm run build:web
```

Publish the contents of `apps/web/out/` at the root of `gh-pages`, including an empty `.nojekyll` file. GitHub Pages must use the `gh-pages` branch and `/` folder.

This is a frontend preview. The face compositing API, mobile upload sessions, and booth printer require the separate Python backend and are not hosted by GitHub Pages. Omitting `NEXT_PUBLIC_BASE_PATH` preserves the original root-hosted build.
