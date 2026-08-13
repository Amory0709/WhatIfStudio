"use client";
import { useState, useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Camera, Loader2, Upload, X } from 'lucide-react';
import { AgreementModal } from './AgreementModal';
import { GradientTile } from './GradientTile';
import type { AGArtwork } from './types';

export function DetailView({ target, onComplete, onBack }: { target: AGArtwork; onComplete: (printUrl: string) => void; onBack: () => void }) {
  const [showAgreement, setShowAgreement] = useState(false);
  const [method, setMethod] = useState<'upload' | 'camera' | null>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const [showCam, setShowCam] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [startedAt, setStartedAt] = useState<number | null>(null);
  const [elapsed, setElapsed] = useState(0);
  const [finishedIn, setFinishedIn] = useState<number | null>(null);

  const fileInputRef = useRef<HTMLInputElement>(null);
  const videoRef = useRef<HTMLVideoElement>(null);
  const streamRef = useRef<MediaStream | null>(null);

  const handleActionClick = (m: 'upload' | 'camera') => {
    setMethod(m);
    setShowAgreement(true);
  };

  const handleAgree = () => {
    setShowAgreement(false);
    if (method === 'upload') {
      fileInputRef.current?.click();
    } else if (method === 'camera') {
      setShowCam(true);
    }
  };

  // 摄像头
  useEffect(() => {
    if (!showCam) return;
    let cancelled = false;
    (async () => {
      try {
        const stream = await navigator.mediaDevices.getUserMedia({
          video: { facingMode: 'user', width: 720, height: 900 },
        });
        if (cancelled) {
          stream.getTracks().forEach((t) => t.stop());
          return;
        }
        streamRef.current = stream;
        if (videoRef.current) videoRef.current.srcObject = stream;
      } catch (e: any) {
        setError(e?.message || 'Camera unavailable');
      }
    })();
    return () => {
      cancelled = true;
      streamRef.current?.getTracks().forEach((t) => t.stop());
      streamRef.current = null;
    };
  }, [showCam]);

  const runSwap = async (f: File) => {
    setBusy(true);
    setError(null);
    setFinishedIn(null);
    const t0 = Date.now();
    setStartedAt(t0);
    setElapsed(0);
    try {
      const fd = new FormData();
      fd.append('source_id', target.id);
      fd.append('face', f);
      // Same-origin in production (FastAPI serves both API + static on :7860).
      // Override with NEXT_PUBLIC_API_URL=http://127.0.0.1:8000 when running
      // the Next.js dev server on :3000 with a separate FastAPI on :8000.
      const API_BASE = process.env.NEXT_PUBLIC_API_URL || '';
      const r = await fetch(`${API_BASE}/api/swap`, { method: 'POST', body: fd });
      if (!r.ok) {
        const d = (await r.json().catch(() => ({}))).detail;
        throw new Error(d || 'Swap failed');
      }
      const blob = await r.blob();
      const url = URL.createObjectURL(blob);
      sessionStorage.setItem('print:' + target.id, url);
      setFinishedIn(Math.round((Date.now() - t0) / 1000));
      onComplete(url);
    } catch (e: any) {
      setError(e?.message || 'Something went wrong');
    } finally {
      setBusy(false);
      setStartedAt(null);
    }
  };

  // Tick the elapsed-seconds counter while busy.
  useEffect(() => {
    if (!startedAt) return;
    const id = setInterval(() => {
      setElapsed(Math.floor((Date.now() - startedAt) / 1000));
    }, 250);
    return () => clearInterval(id);
  }, [startedAt]);

  const onFileChosen = (e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0];
    if (!f) return;
    setPreview(URL.createObjectURL(f));
    void runSwap(f);
  };

  const snap = () => {
    const v = videoRef.current;
    if (!v) return;
    const c = document.createElement('canvas');
    c.width = v.videoWidth;
    c.height = v.videoHeight;
    const ctx = c.getContext('2d');
    if (!ctx) return;
    ctx.drawImage(v, 0, 0);
    c.toBlob(
      (b) => {
        if (!b) return;
        const f = new File([b], 'capture.png', { type: 'image/png' });
        setPreview(URL.createObjectURL(f));
        setShowCam(false);
        void runSwap(f);
      },
      'image/png',
      0.95,
    );
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 50 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -50 }}
      className="absolute inset-0 flex flex-col md:flex-row items-center justify-center p-6 md:p-20 gap-10 md:gap-20"
    >
      <input ref={fileInputRef} type="file" accept="image/*" className="hidden" onChange={onFileChosen} />

      <button onClick={onBack} className="absolute top-6 left-6 md:top-8 md:left-10 text-xs font-sans uppercase tracking-widest text-muted-foreground hover:text-primary">
        ← Back
      </button>

      <div className="w-full md:w-1/2 max-w-md">
        <motion.div
          layoutId={'img-' + target.id}
          className="aspect-[3/2] w-full bg-muted overflow-hidden shadow-2xl relative border border-border/40"
        >
          {target.image ? (
            <img src={target.image} alt={target.title} className="w-full h-full object-cover" />
          ) : (
            <GradientTile palette={target.palette} />
          )}
        </motion.div>
      </div>

      <div className="w-full md:w-1/2 flex flex-col justify-center max-w-md">
        <h2 className="text-4xl md:text-5xl mb-4 italic">Become the Subject</h2>
        <p className="text-muted-foreground font-sans font-light mb-12">
          Lend your visage to the masterworks. Select a method to provide your portrait for the exhibition.
        </p>

        <div className="flex flex-col gap-4">
          <button
            onClick={() => handleActionClick('upload')}
            disabled={busy}
            className="flex items-center gap-6 p-6 border border-border hover:bg-primary/5 hover:border-primary/30 transition-all group disabled:opacity-50"
          >
            <Upload className="w-6 h-6 text-muted-foreground group-hover:text-primary transition-colors" />
            <div className="text-left">
              <div className="font-sans italic text-2xl text-foreground group-hover:text-primary group-hover:italic transition-all">Upload Archive</div>
              <div className="font-sans text-xs text-muted-foreground mt-1">Select a file from your device</div>
            </div>
          </button>

          <button
            onClick={() => handleActionClick('camera')}
            disabled={busy}
            className="flex items-center gap-6 p-6 border border-border hover:bg-primary/5 hover:border-primary/30 transition-all group disabled:opacity-50"
          >
            <Camera className="w-6 h-6 text-muted-foreground group-hover:text-primary transition-colors" />
            <div className="text-left">
              <div className="font-sans italic text-2xl text-foreground group-hover:text-primary group-hover:italic transition-all">Capture Now</div>
              <div className="font-sans text-xs text-muted-foreground mt-1">Use your device camera</div>
            </div>
          </button>
        </div>

        {(busy || finishedIn !== null) && (
          <ComposingProgress
            elapsed={elapsed}
            finishedIn={finishedIn}
            busy={busy}
          />
        )}
        {error && (
          <p className="mt-4 rounded border border-rust/30 bg-rust/5 p-3 text-sm text-rust">{error}</p>
        )}
      </div>

      <AnimatePresence>
        {showCam && (
          <div className="fixed inset-0 z-50 grid place-items-center bg-ink/80 p-6 backdrop-blur">
            <motion.div
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.95 }}
              className="relative max-w-md overflow-hidden rounded-[3px] border border-paper/20 bg-paper p-4 shadow-2xl"
            >
              <video ref={videoRef} autoPlay playsInline muted className="aspect-[3/4] w-full -scale-x-100 rounded object-cover" />
              <div className="mt-4 flex items-center justify-between">
                <button onClick={() => setShowCam(false)} className="text-sm text-ink/60 hover:text-ink">Cancel</button>
                <button onClick={snap} className="font-sans text-xs uppercase tracking-widest bg-primary text-primary-foreground px-6 py-3 rounded-full hover:bg-primary/90 transition-colors">
                  Capture
                </button>
              </div>
              <button onClick={() => setShowCam(false)} className="absolute top-3 right-3 text-ink/40 hover:text-ink">
                <X className="w-4 h-4" />
              </button>
            </motion.div>
          </div>
        )}
      </AnimatePresence>

      <AnimatePresence>
        {showAgreement && (
          <AgreementModal
            onClose={() => setShowAgreement(false)}
            onAgree={handleAgree}
            method={method}
          />
        )}
      </AnimatePresence>
    </motion.div>
  );
}

// ---------------------------------------------------------------------------
// ComposingProgress
//
// Prominent, gallery-style "composing" indicator. Replaces the tiny pulsing
// line that was easy to miss: now a card with a spinning ring, an elapsed
// counter, and a soft ~30 s estimate (InsightFace + inswapper on a single
// source/face takes ~30 s on M-series CPUs). Once the swap resolves we
// freeze on the final elapsed time for ~1.2 s so the user can see how long
// it actually took before we hand off to the print view.
// ---------------------------------------------------------------------------
function ComposingProgress({
  elapsed,
  finishedIn,
  busy,
}: {
  elapsed: number;
  finishedIn: number | null;
  busy: boolean;
}) {
  const ESTIMATE_SECONDS = 30;
  const pct = Math.min(100, Math.round((elapsed / ESTIMATE_SECONDS) * 100));
  const remaining = Math.max(0, ESTIMATE_SECONDS - elapsed);
  const showFinished = !busy && finishedIn !== null;
  const label = showFinished
    ? `Composed in ${finishedIn}s`
    : `Composing portrait · ${elapsed}s`;
  const sub = showFinished
    ? 'Preparing your print…'
    : remaining > 0
    ? `About ${remaining}s remaining (typical)`
    : 'Almost there — finishing the final pass…';

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -8 }}
      transition={{ duration: 0.35, ease: 'easeOut' }}
      className="mt-8 flex items-center gap-4 rounded-[3px] border border-primary/30 bg-primary/5 px-5 py-4"
      role="status"
      aria-live="polite"
    >
      <div className="relative h-10 w-10 shrink-0">
        <svg viewBox="0 0 40 40" className="h-10 w-10 -rotate-90">
          <circle
            cx="20"
            cy="20"
            r="17"
            fill="none"
            stroke="white"
            strokeWidth="3"
            className="text-primary/15"
          />
          <circle
            cx="20"
            cy="20"
            r="17"
            fill="none"
            stroke="currentColor"
            strokeWidth="3"
            strokeLinecap="round"
            strokeDasharray={2 * Math.PI * 17}
            strokeDashoffset={(2 * Math.PI * 17) * (1 - pct / 100)}
            className="text-primary transition-[stroke-dashoffset] duration-500 ease-out"
          />
        </svg>
        {busy && (
          <Loader2 className="absolute inset-0 m-auto h-4 w-4 animate-spin text-primary" />
        )}
      </div>
      <div className="min-w-0">
        <div className="font-sans italic text-lg text-foreground leading-tight">
          {label}
        </div>
        <div className="mt-0.5 font-sans text-xs text-muted-foreground">
          {sub}
        </div>
      </div>
    </motion.div>
  );
}
