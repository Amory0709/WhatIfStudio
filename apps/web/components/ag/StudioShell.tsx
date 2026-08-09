"use client";
import { useState, useEffect } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import { ChevronLeft } from 'lucide-react';
import { GalleryView } from './GalleryView';
import { DetailView } from './DetailView';
import { ResultView } from './ResultView';
import type { AGArtwork } from './types';

type Step = 'gallery' | 'detail' | 'result';

const STEP_LABEL: Record<Step, string> = {
  gallery: '01 / Select',
  detail: '02 / Capture',
  result: '03 / Exhibit',
};

export function StudioShell({
  items,
  initialId,
  initialStep,
  initialPrintUrl,
}: {
  items: AGArtwork[];
  initialId?: string;
  initialStep?: Step;
  initialPrintUrl?: string | null;
}) {
  const findById = (id?: string) => (id ? items.find((i) => i.id === id) : undefined);
  const initial = findById(initialId);
  const [step, setStep] = useState<Step>(initialStep ?? (initial ? 'detail' : 'gallery'));
  const [selected, setSelected] = useState<AGArtwork | null>(initial ?? null);
  const [printUrl, setPrintUrl] = useState<string | null>(() => {
    // SSR: only the route-supplied placeholder is available (sessionStorage is browser-only).
    if (typeof window === 'undefined') return initialPrintUrl ?? null;
    // Client: prefer the real swapped blob URL from sessionStorage when present.
    if (initialId) {
      try {
        const stored = sessionStorage.getItem('print:' + initialId);
        if (stored) return stored;
      } catch {}
    }
    return initialPrintUrl ?? null;
  });

  useEffect(() => {
    if (step === 'result' && !printUrl && selected) {
      try {
        const url = sessionStorage.getItem('print:' + selected.id);
        if (url) setPrintUrl(url);
      } catch {}
    }
  }, [step, printUrl, selected]);

  const handleSelect = (img: AGArtwork) => {
    setSelected(img);
    setStep('detail');
    if (typeof window !== 'undefined') window.history.replaceState(null, '', '/swap/' + img.id);
  };

  const handleComplete = (url: string) => {
    setPrintUrl(url);
    setStep('result');
    if (typeof window !== 'undefined' && selected) {
      window.history.replaceState(null, '', '/print/' + selected.id);
    }
  };

  const handleBack = () => {
    if (step === 'result') {
      setStep('detail');
      if (typeof window !== 'undefined' && selected) window.history.replaceState(null, '', '/swap/' + selected.id);
    } else if (step === 'detail') {
      setStep('gallery');
      setSelected(null);
      if (typeof window !== 'undefined') window.history.replaceState(null, '', '/');
    }
  };

  const handleReset = () => {
    setStep('gallery');
    setSelected(null);
    setPrintUrl(null);
    if (typeof window !== 'undefined') window.history.replaceState(null, '', '/');
  };

  return (
    <div className="min-h-screen h-screen bg-background text-foreground overflow-hidden flex flex-col">
      {/* Header — 1:1 AG App */}
      <header className="py-3 px-6 md:py-4 md:px-10 flex items-center justify-between z-50 fixed top-0 left-0 right-0 backdrop-blur-2xl backdrop-saturate-150 bg-white/55 supports-[backdrop-filter]:bg-white/40 border-b border-white/40 shadow-[inset_0_-1px_0_rgba(0,0,0,0.05)] transition-all">
        <div className="flex items-center gap-4">
          <AnimatePresence>
            {step !== 'gallery' && (
              <motion.button
                initial={{ opacity: 0, x: -10 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: -10 }}
                onClick={handleBack}
                className="hover:text-muted-foreground transition-colors"
              >
                <ChevronLeft className="w-6 h-6" strokeWidth={1.5} />
              </motion.button>
            )}
          </AnimatePresence>
          <h1 className="text-2xl md:text-3xl tracking-wide text-foreground">
            What If <span className="font-sans text-xs uppercase tracking-widest text-primary ml-2">Studio</span>
          </h1>
        </div>
        <div className="text-xs font-sans tracking-widest uppercase text-muted-foreground">
          {STEP_LABEL[step]}
        </div>
      </header>

      {/* Main — AG App 不加 pt-16，header 是 fixed 浮层 */}
      <main className="flex-1 relative w-full h-[calc(100vh-0px)] perspective-1000 -translate-y-[5vh]">
        <AnimatePresence mode="wait">
          {step === 'gallery' && (
            <GalleryView key="gallery" items={items} onSelect={handleSelect} />
          )}
          {step === 'detail' && selected && (
            <DetailView key="detail" target={selected} onComplete={handleComplete} onBack={handleBack} />
          )}
          {step === 'result' && selected && printUrl && (
            <ResultView key="result" imageUrl={printUrl} title={selected.title} onReset={handleReset} />
          )}
        </AnimatePresence>
      </main>
    </div>
  );
}
