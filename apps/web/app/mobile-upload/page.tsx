"use client";

import { Suspense, useCallback, useRef, useState } from 'react';
import { useSearchParams } from 'next/navigation';
import { Check, Loader2, Upload } from 'lucide-react';

function MobileUploadInner() {
  const params = useSearchParams();
  const sessionId = params.get('session')?.trim() ?? '';
  const sourceId = params.get('source')?.trim() ?? '';
  const fileRef = useRef<HTMLInputElement>(null);

  const [busy, setBusy] = useState(false);
  const [done, setDone] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const upload = useCallback(
    async (file: File) => {
      if (!sessionId) {
        setError('Missing upload session. Scan the QR code again from the booth.');
        return;
      }
      setBusy(true);
      setError(null);
      try {
        const fd = new FormData();
        fd.append('face', file);
        const r = await fetch(`/api/upload-sessions/${sessionId}/face`, {
          method: 'POST',
          body: fd,
        });
        if (!r.ok) {
          const d = (await r.json().catch(() => ({}))).detail;
          throw new Error(typeof d === 'string' ? d : 'Upload failed');
        }
        setDone(true);
      } catch (e: unknown) {
        setError(e instanceof Error ? e.message : 'Upload failed');
      } finally {
        setBusy(false);
      }
    },
    [sessionId],
  );

  const onFile = (e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0];
    if (f) void upload(f);
  };

  if (!sessionId) {
    return (
      <main className="mx-auto flex min-h-screen max-w-md flex-col justify-center px-6 py-12">
        <h1 className="text-2xl italic">Invalid link</h1>
        <p className="mt-3 font-sans text-sm text-muted-foreground">
          Scan the QR code at the exhibition booth to open a fresh upload link.
        </p>
      </main>
    );
  }

  return (
    <main className="mx-auto flex min-h-screen max-w-md flex-col justify-center px-6 py-12">
      <p className="font-sans text-xs uppercase tracking-widest text-muted-foreground">What If Studio</p>
      <h1 className="mt-2 text-3xl italic">Send your portrait</h1>
      <p className="mt-3 font-sans text-sm font-light text-muted-foreground">
        Choose a clear photo of your face. The booth display will compose your artwork automatically
        {sourceId ? ` for portrait ${sourceId}` : ''}.
      </p>

      <input ref={fileRef} type="file" accept="image/*" capture="user" className="hidden" onChange={onFile} />

      {done ? (
        <div className="mt-10 rounded border border-primary/30 bg-primary/5 p-6 text-center" role="status">
          <Check className="mx-auto h-8 w-8 text-primary" aria-hidden="true" />
          <p className="mt-4 font-sans text-lg text-foreground">Portrait received</p>
          <p className="mt-2 font-sans text-sm text-muted-foreground">
            Return to the booth screen — your artwork is being composed.
          </p>
        </div>
      ) : (
        <button
          type="button"
          disabled={busy}
          onClick={() => fileRef.current?.click()}
          className="mt-10 flex items-center justify-center gap-3 rounded-full bg-primary px-8 py-4 font-sans text-xs uppercase tracking-widest text-primary-foreground transition-colors hover:bg-primary/90 disabled:opacity-60"
        >
          {busy ? <Loader2 className="h-4 w-4 animate-spin" /> : <Upload className="h-4 w-4" />}
          {busy ? 'Uploading…' : 'Choose photo'}
        </button>
      )}

      {error && (
        <p className="mt-4 rounded border border-rust/30 bg-rust/5 p-3 text-sm text-rust" role="alert">
          {error}
        </p>
      )}
    </main>
  );
}

export default function MobileUploadPage() {
  return (
    <Suspense
      fallback={
        <main className="grid min-h-screen place-items-center">
          <Loader2 className="h-6 w-6 animate-spin text-primary" />
        </main>
      }
    >
      <MobileUploadInner />
    </Suspense>
  );
}
