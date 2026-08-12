// Client-side helpers for booth printer integration.
//
// - getBoothPrintStatus(): asks the API whether booth mode is configured.
// - boothPrint(imageUrl, title): uploads the blob URL (or relative URL) to
//   /api/print and waits for the CUPS job id.
//
// These no-op gracefully when the endpoint is unreachable or disabled, so the
// UI can always fall back to "Print via My Device" (window.print()).

const API_BASE = process.env.NEXT_PUBLIC_API_URL || '';

export type BoothPrintState = 'ready' | 'busy' | 'offline' | 'error';

export interface BoothPrintStatus {
  available: boolean;
  printer: string | null;
  media: string;
  copies: number;
  // Live CUPS state (polled every 5 s while the print step is shown).
  state: BoothPrintState;
  message: string;
  connected: boolean;
}

export const DISABLED_BOOTH_STATUS: BoothPrintStatus = {
  available: false,
  printer: null,
  media: '',
  copies: 1,
  state: 'offline',
  message: 'Not configured',
  connected: false,
};

export async function getBoothPrintStatus(): Promise<BoothPrintStatus> {
  try {
    const r = await fetch(`${API_BASE}/api/print/status`, { cache: 'no-store' });
    if (!r.ok) return DISABLED_BOOTH_STATUS;
    const data = await r.json();
    return {
      available: !!data.available,
      printer: data.printer || null,
      media: data.media || '',
      copies: Number(data.copies) || 1,
      state: (data.state as BoothPrintState) || 'offline',
      message: data.message || (data.available ? 'Checking…' : 'Not configured'),
      connected: !!data.connected,
    };
  } catch {
    return DISABLED_BOOTH_STATUS;
  }
}

export async function boothPrint(
  imageUrl: string,
  title: string,
): Promise<{ ok: true; job_id?: string } | { ok: false; error: string }> {
  try {
    const blob = await fetch(imageUrl).then((r) => r.blob());
    const fd = new FormData();
    fd.append(
      'image',
      new File([blob], 'portrait.jpg', { type: blob.type || 'image/jpeg' }),
    );
    fd.append('title', title || 'WhatIf Portrait');
    const r = await fetch(`${API_BASE}/api/print`, { method: 'POST', body: fd });
    if (!r.ok) {
      const txt = await r.text().catch(() => '');
      let msg = txt || `HTTP ${r.status}`;
      try {
        const parsed = JSON.parse(txt);
        if (parsed && parsed.detail) msg = parsed.detail;
      } catch {
        // not JSON, keep raw text
      }
      return { ok: false, error: msg };
    }
    const data = await r.json();
    return data && data.ok ? { ok: true as const, job_id: data.job_id } : { ok: false, error: 'Printer refused' };
  } catch (e: any) {
    return { ok: false, error: (e && e.message) || 'Network error' };
  }
}