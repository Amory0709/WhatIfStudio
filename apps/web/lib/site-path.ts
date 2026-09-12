/** Prefix same-origin assets and routes for a GitHub Pages project site. */
export function sitePath(path: string): string {
  const base = (process.env.NEXT_PUBLIC_BASE_PATH || '').replace(/\/$/, '');
  if (!base || !path.startsWith('/') || path.startsWith('//') || path === base || path.startsWith(base + '/')) return path;
  return base + path;
}
