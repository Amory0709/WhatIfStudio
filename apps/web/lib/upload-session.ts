export type UploadSessionStatus = 'pending' | 'processing' | 'ready' | 'failed' | 'expired';

export type UploadSessionInfo = {
  session_id: string;
  source_id: string;
  status: UploadSessionStatus;
  expires_at: number;
  mobile_upload_url: string;
  error?: string | null;
};

/** Same-origin API calls — works via Next rewrite in dev and FastAPI static hosting in prod. */
function apiPath(path: string): string {
  return path.startsWith('/') ? path : `/${path}`;
}

export async function createUploadSession(sourceId: string): Promise<UploadSessionInfo> {
  const r = await fetch(apiPath('/api/upload-sessions'), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ source_id: sourceId }),
  });
  if (!r.ok) {
    const d = (await r.json().catch(() => ({}))).detail;
    throw new Error(typeof d === 'string' ? d : 'Could not start mobile upload');
  }
  return r.json();
}

export async function getUploadSession(sessionId: string): Promise<UploadSessionInfo> {
  const r = await fetch(apiPath(`/api/upload-sessions/${sessionId}`));
  if (!r.ok) {
    const d = (await r.json().catch(() => ({}))).detail;
    throw new Error(typeof d === 'string' ? d : 'Could not read upload session');
  }
  return r.json();
}

export async function fetchUploadSessionResult(sessionId: string): Promise<Blob> {
  const r = await fetch(apiPath(`/api/upload-sessions/${sessionId}/result`));
  if (!r.ok) {
    const d = (await r.json().catch(() => ({}))).detail;
    throw new Error(typeof d === 'string' ? d : 'Could not fetch result');
  }
  return r.blob();
}

export function resolveMobileUploadUrl(apiUrl: string): string {
  if (/^https?:\/\//i.test(apiUrl)) return apiUrl;

  const envPublic = process.env.NEXT_PUBLIC_PUBLIC_URL?.trim().replace(/\/$/, '');
  if (envPublic) return `${envPublic}${apiUrl.startsWith('/') ? apiUrl : `/${apiUrl}`}`;

  if (typeof window !== 'undefined') {
    const { hostname, origin } = window.location;
    if (hostname !== 'localhost' && hostname !== '127.0.0.1') {
      return `${origin}${apiUrl.startsWith('/') ? apiUrl : `/${apiUrl}`}`;
    }
  }

  return apiUrl.startsWith('/') && typeof window !== 'undefined'
    ? `${window.location.origin}${apiUrl}`
    : apiUrl;
}

export function isLocalhostUploadUrl(url: string): boolean {
  return /\/\/(127\.0\.0\.1|localhost)(:\d+)?/i.test(url);
}
