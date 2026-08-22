"use client";

import { useEffect, useRef, useState } from 'react';
import { motion } from 'framer-motion';
import { QRCodeSVG } from 'qrcode.react';
import { Loader2, Smartphone, Upload, X } from 'lucide-react';
import {
  createUploadSession,
  fetchUploadSessionResult,
  getUploadSession,
  isLocalhostUploadUrl,
  resolveMobileUploadUrl,
  type UploadSessionInfo,
} from '@/lib/upload-session';

type Props = {
  sourceId: string;
  onClose: () => void;
  onLocalFile: () => void;
  onRemoteComplete: (blob: Blob) => void;
  onRemoteError: (message: string) => void;
};

export function UploadArchiveModal({
  sourceId,
  onClose,
  onLocalFile,
  onRemoteComplete,
  onRemoteError,
}: Props) {
  const [session, setSession] = useState<UploadSessionInfo | null>(null);
  const [mobileUrl, setMobileUrl] = useState<string | null>(null);
  const [sessionError, setSessionError] = useState<string | null>(null);
  const [waitingForPhone, setWaitingForPhone] = useState(false);
  const handledRef = useRef(false);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const created = await createUploadSession(sourceId);
        if (cancelled) return;
        setSession(created);
        setMobileUrl(resolveMobileUploadUrl(created.mobile_upload_url));
      } catch (e: unknown) {
        if (cancelled) return;
        setSessionError(e instanceof Error ? e.message : 'Could not start mobile upload');
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [sourceId]);

  useEffect(() => {
    if (!session || handledRef.current) return;
    const sessionId = session.session_id;
    let cancelled = false;

    const poll = async () => {
      try {
        const next = await getUploadSession(sessionId);
        if (cancelled) return;
        setSession(next);
        setWaitingForPhone(next.status === 'pending' || next.status === 'processing');

        if (next.status === 'ready') {
          handledRef.current = true;
          const blob = await fetchUploadSessionResult(sessionId);
          if (cancelled) return;
          onRemoteComplete(blob);
          return;
        }
        if (next.status === 'failed') {
          handledRef.current = true;
          onRemoteError(next.error || 'Mobile upload failed');
          return;
        }
        if (next.status === 'expired') {
          handledRef.current = true;
          onRemoteError('Mobile upload session expired');
        }
      } catch (e: unknown) {
        if (cancelled || handledRef.current) return;
        onRemoteError(e instanceof Error ? e.message : 'Mobile upload failed');
      }
    };

    void poll();
    const id = setInterval(() => {
      if (!handledRef.current) void poll();
    }, 2000);
    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, [session?.session_id, onRemoteComplete, onRemoteError]);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        className="absolute inset-0 bg-white/70 backdrop-blur-md"
        onClick={onClose}
      />
      <motion.div
        initial={{ opacity: 0, scale: 0.95, y: 20 }}
        animate={{ opacity: 1, scale: 1, y: 0 }}
        exit={{ opacity: 0, scale: 0.95, y: 20 }}
        className="relative flex max-h-[90vh] w-full max-w-lg flex-col overflow-y-auto border border-border bg-card p-8 shadow-2xl md:p-10"
        role="dialog"
        aria-labelledby="upload-archive-title"
        aria-describedby="upload-archive-desc"
      >
        <button
          onClick={onClose}
          className="absolute right-6 top-6 text-muted-foreground hover:text-primary"
          aria-label="Close upload options"
        >
          <X className="h-5 w-5" />
        </button>

        <h3 id="upload-archive-title" className="mb-2 text-3xl italic">
          Upload Archive
        </h3>
        <p id="upload-archive-desc" className="mb-8 font-sans text-sm font-light text-muted-foreground">
          Choose a file on this device, or scan the code with your phone to upload from your camera roll.
        </p>

        <button
          type="button"
          onClick={onLocalFile}
          className="mb-8 flex items-center gap-4 border border-border p-5 text-left transition-all hover:border-primary/30 hover:bg-primary/5"
        >
          <Upload className="h-6 w-6 shrink-0 text-muted-foreground" />
          <div>
            <div className="font-sans text-lg italic text-foreground">Select from this device</div>
            <div className="mt-1 font-sans text-xs text-muted-foreground">Browse photos on this screen</div>
          </div>
        </button>

        <div className="border border-border/70 bg-muted/20 p-6">
          <div className="mb-4 flex items-center gap-3">
            <Smartphone className="h-5 w-5 text-primary" aria-hidden="true" />
            <div className="font-sans text-sm uppercase tracking-widest text-foreground">Scan to upload</div>
          </div>

          {sessionError ? (
            <p className="text-sm text-rust">{sessionError}</p>
          ) : mobileUrl ? (
            <div className="flex flex-col items-center gap-4 sm:flex-row sm:items-start">
              <div className="rounded bg-white p-3 shadow-sm">
                <QRCodeSVG value={mobileUrl} size={168} level="M" includeMargin />
              </div>
              <div className="min-w-0 text-center sm:text-left">
                <p className="font-sans text-sm text-muted-foreground">
                  Open your phone camera, scan the code, and upload a portrait photo.
                </p>
                <p className="mt-3 break-all font-mono text-[11px] text-muted-foreground/80">{mobileUrl}</p>
                {mobileUrl && isLocalhostUploadUrl(mobileUrl) && (
                  <p className="mt-3 rounded border border-rust/30 bg-rust/5 p-3 text-xs text-rust">
                    QR points at this computer only. Set <code className="font-mono">PUBLIC_BASE_URL</code> or{' '}
                    <code className="font-mono">NEXT_PUBLIC_PUBLIC_URL</code> to your LAN address (for example{' '}
                    <code className="font-mono">http://100.96.140.78:3000</code>) and restart.
                  </p>
                )}
                {waitingForPhone && (
                  <p className="mt-4 flex items-center justify-center gap-2 font-sans text-xs text-primary sm:justify-start" role="status" aria-live="polite">
                    <Loader2 className="h-3.5 w-3.5 animate-spin" />
                    Waiting for phone upload…
                  </p>
                )}
              </div>
            </div>
          ) : (
            <div className="flex items-center justify-center gap-2 py-8 text-sm text-muted-foreground">
              <Loader2 className="h-4 w-4 animate-spin" />
              Preparing QR code…
            </div>
          )}
        </div>
      </motion.div>
    </div>
  );
}
