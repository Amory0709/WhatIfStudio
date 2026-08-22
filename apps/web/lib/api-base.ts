/** API origin for browser fetches. Empty string = same-origin (Next dev rewrite → :8000). */
export function getApiBase(): string {
  const env = process.env.NEXT_PUBLIC_API_URL?.trim();
  if (env) return env.replace(/\/$/, '');
  return '';
}
