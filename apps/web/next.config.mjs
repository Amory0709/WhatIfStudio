// In production the FastAPI process serves both the API and the static Next.js
// export on the same origin (port 7860 on Hugging Face Spaces). The browser
// posts to `/api/swap` directly — no rewrite / proxy needed.
//
// For local dev with Next.js on :3000 and FastAPI on :8000, set
// NEXT_PUBLIC_API_URL=http://127.0.0.1:8000 before `next dev` to point the
// client at the FastAPI port.
//
// `output: 'export'` is ONLY applied for `next build` (production). In dev,
// `next dev` would otherwise refuse to serve dynamic routes like `/swap/[id]`
// when output: export is set, because dev mode wants to render them on
// demand. NODE_ENV is set by `next dev`/`next build` for us.
/** @type {import("next").NextConfig} */
const isProd = process.env.NODE_ENV === 'production';
const nextConfig = {
  // Pure static export → drops into apps/web/out, then FastAPI serves it.
  ...(isProd && { output: 'export' }),
  // next/image is not used, but keep unoptimized in case a child component pulls it in.
  images: { unoptimized: true },
  reactStrictMode: true,
  async rewrites() {
    return [];
  },
};
export default nextConfig;