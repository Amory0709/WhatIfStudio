/** @type {import("next").NextConfig} */
// Earlier we proxied /api/swap through the Next.js dev server to FastAPI on
// 127.0.0.1:8000. The swap engine takes ~30s on CPU (insightface+onnxruntime),
// but the Next.js dev proxy gives up around 30s and the browser sees a 500
// ("socket hang up"). We solve this by having the browser call the API
// DIRECTLY at http://127.0.0.1:8000/api/swap — same-origin enforcement is
// already relaxed for the dev port. No rewrite is configured here on purpose.
const nextConfig = {
  reactStrictMode: true,
  async rewrites() {
    return [];
  },
};
export default nextConfig;
