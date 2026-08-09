"use client";
import { useState, useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Camera, Upload, X } from 'lucide-react';
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
    try {
      const fd = new FormData();
      fd.append('source_id', target.id);
      fd.append('face', f);
      // Hit FastAPI directly. Going through Next.js dev proxy (`/api/swap`)
      // triggers a ~30s socket hang-up while the CPU-bound face-swap is still
      // running; bypassing the proxy lets the ~30s request complete cleanly.
      const r = await fetch('http://127.0.0.1:8000/api/swap', { method: 'POST', body: fd });
      if (!r.ok) {
        const d = (await r.json().catch(() => ({}))).detail;
        throw new Error(d || 'Swap failed');
      }
      const blob = await r.blob();
      const url = URL.createObjectURL(blob);
      sessionStorage.setItem('print:' + target.id, url);
      onComplete(url);
    } catch (e: any) {
      setError(e?.message || 'Something went wrong');
    } finally {
      setBusy(false);
    }
  };

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

      <div className="w-full md:w-1/2 max-w-sm">
        <motion.div
          layoutId={'img-' + target.id}
          className="aspect-[2/3] w-full bg-muted overflow-hidden shadow-2xl relative border border-border/40"
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

        {busy && (
          <p className="mt-8 font-sans text-xs uppercase tracking-widest text-muted-foreground animate-pulse">
            Composing portrait…
          </p>
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
