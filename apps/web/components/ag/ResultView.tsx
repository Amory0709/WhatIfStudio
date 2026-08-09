"use client";
import { useState } from 'react';
import { motion } from 'framer-motion';
import { Printer, ChevronLeft } from 'lucide-react';

export function ResultView({
  imageUrl,
  title,
  onReset,
}: {
  imageUrl: string;
  title: string;
  onReset: () => void;
}) {
  const [isPrinting, setIsPrinting] = useState(false);
  const [printComplete, setPrintComplete] = useState(false);

  const handlePrint = () => {
    if (isPrinting) return;
    setIsPrinting(true);
    setTimeout(() => setPrintComplete(true), 4000);
  };

  // Build a print-friendly filename from the artwork title.
  const fileName =
    'whatif-' + (title || 'portrait').toLowerCase().replace(/[^a-z0-9]+/g, '-') + '.png';

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="relative flex flex-col items-center justify-center w-full h-full px-6 py-10"
    >
      {/* Printer + portrait centerpiece. The printer slot animates from top -> middle. */}
      <div className="relative w-64 md:w-80 flex flex-col items-center">
        {/* Printer top slot (static visual cue) */}
        <div className="w-full h-4 bg-muted-foreground/10 rounded-full shadow-inner mb-[-2px] z-20 relative overflow-hidden">
          <div className="absolute inset-0 bg-gradient-to-b from-black/20 to-transparent" />
        </div>

        {/* Image well — height grows with the printer so the caption below never collides. */}
        <div
          className={
            'relative w-[90%] overflow-hidden z-10 transition-all duration-500 ' +
            (printComplete ? 'h-[420px] md:h-[480px]' : 'h-[360px] md:h-[420px]')
          }
        >
          <motion.div
            initial={{ y: '-100%' }}
            animate={{ y: printComplete ? '0%' : '0%' }}
            transition={{ duration: 4, ease: 'linear' }}
            className="w-full aspect-[2/3] relative bg-white p-2 shadow-xl border border-border"
          >
            <img
              src={imageUrl}
              alt="Printed Portrait"
              className="w-full h-full object-cover contrast-125 sepia-[.3]"
            />
            {/* SLB watermark — fixed at top-right of the printed sheet. */}
            <div className="absolute top-3 right-3 font-sans italic text-xl text-white drop-shadow-md mix-blend-overlay">
              SLB
            </div>
          </motion.div>

          {/* Scan line that sweeps top -> bottom during print */}
          {!printComplete && (
            <motion.div
              initial={{ top: '0%' }}
              animate={{ top: '100%' }}
              transition={{ duration: 4, ease: 'linear' }}
              className="absolute left-0 right-0 h-1 bg-primary/50 blur-[2px] z-20"
            />
          )}
        </div>
      </div>

      {/* Caption + actions — appear below the printer, never overlap the portrait. */}
      <div
        className={
          'mt-10 md:mt-14 flex flex-col items-center gap-5 text-center transition-opacity duration-700 ' +
          (printComplete ? 'opacity-100' : 'opacity-0 pointer-events-none')
        }
      >
        <p className="font-sans italic text-xl text-foreground">
          Your masterpiece is ready.
        </p>
        <a
          href={imageUrl}
          download={fileName}
          className="px-6 py-3 bg-primary text-primary-foreground font-sans text-xs uppercase tracking-widest hover:bg-primary/90 transition-colors"
        >
          Download Print
        </a>
        <button
          onClick={onReset}
          className="px-6 py-3 border border-border font-sans text-xs uppercase tracking-widest text-foreground hover:bg-primary/5 hover:text-primary transition-all flex items-center gap-2"
        >
          <ChevronLeft className="w-4 h-4" /> Back to Homepage
        </button>
      </div>

      {/* Print trigger — sits above the printer when the print is NOT yet running. */}
      {!isPrinting && (
        <div className="mt-10 flex justify-center">
          <button
            onClick={handlePrint}
            className="group flex items-center gap-4 px-8 py-4 bg-primary text-primary-foreground font-sans text-sm uppercase tracking-widest hover:bg-primary/90 transition-colors"
          >
            <Printer className="w-5 h-5 group-hover:scale-110 transition-transform" />
            Print Portrait
          </button>
        </div>
      )}
    </motion.div>
  );
}
