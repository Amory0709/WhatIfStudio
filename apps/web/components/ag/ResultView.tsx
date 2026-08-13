"use client";
import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { Printer, ChevronLeft } from 'lucide-react';
import {
  getBoothPrintStatus,
  boothPrint,
  type BoothPrintStatus,
} from '@/lib/print';

export function ResultView({
  imageUrl,
  title,
  onReset,
}: {
  imageUrl: string;
  title: string;
  onReset: () => void;
}) {
  // Booth-mode integration. The server exposes /api/print/status which
  // returns { available: true, ... } only when BOOTH_PRINTER_NAME is set
  // in the API process environment. We poll once on mount; if it's off,
  // the "Print Here" button is hidden entirely.
  const [booth, setBooth] = useState<BoothPrintStatus>({
    available: false,
    printer: null,
    media: '',
    copies: 1,
    state: 'offline',
    message: 'Checking…',
    connected: false,
  });
  const [boothBusy, setBoothBusy] = useState(false);
  const [boothMsg, setBoothMsg] = useState<string | null>(null);

  // Poll /api/print/status every 5 s while the print step is mounted so
  // the status pill above the button stays in sync with the CUPS queue
  // (a printer can drop offline between prints without the user knowing).
  useEffect(() => {
    let cancelled = false;
    const refresh = () => {
      void getBoothPrintStatus().then((s) => {
        if (!cancelled) setBooth(s);
      });
    };
    refresh();
    const id = setInterval(refresh, 5000);
    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, []);

  // "Print via My Device" — opens the OS print dialog with our @media
  // print rules (see globals.css) producing a 4R-only page.
  const handleSystemPrint = () => {
    // Defer to next tick so React finishes painting before the print
    // dialog blocks the main thread. Some browsers snapshot the DOM
    // synchronously on window.print(), which would race the state update.
    setTimeout(() => window.print(), 0);
  };

  // "Print Here" — uploads the swapped PNG to /api/print, which shells
  // out to `lp` against the locally-paired booth printer.
  const handleBoothPrint = async () => {
    if (boothBusy || !imageUrl) return;
    setBoothBusy(true);
    setBoothMsg(null);
    const res = await boothPrint(imageUrl, title);
    setBoothBusy(false);
    if (res.ok) {
      setBoothMsg(
        res.job_id
          ? `Sent · CUPS job ${res.job_id}`
          : `Sent to ${booth.printer || 'booth printer'}`,
      );
    } else {
      setBoothMsg(`Failed: ${res.error}`);
    }
  };

  // Build a print-friendly filename from the artwork title.
  const fileName =
    'whatif-' +
    (title || 'portrait').toLowerCase().replace(/[^a-z0-9]+/g, '-') +
    '.png';

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="relative flex flex-col items-center justify-start w-full h-full px-6 pt-40 md:pt-56 pb-8 overflow-y-auto"
    >
      {/* Printer slot + portrait tray. The slot is a static visual cue at
          the top; the portrait itself slides DOWN from behind the slot
          into the well over 4 s on mount — like a photo printer ejecting
          a finished print. The well is sized to the actual 4R LANDSCAPE
          physical dimensions (6 in wide × 4 in tall = 152 × 102 mm). On
          narrow viewports max-w caps it so the preview still fits the
          screen. The slot is the same width as the well/photo so the
          three elements visually line up at the 4R print size. pt-16
          (mobile) / pt-24 (desktop) leaves just enough room for the
          fixed header (~64 px) without pushing the buttons below the
          viewport fold. */}
      <div className="relative w-[6in] max-w-[calc(100vw-3rem)] flex flex-col items-center">
        {/* Printer top slot — full container width (100%), so it extends
            ~5% beyond the well on each side. z-20 keeps the slot on
            top of the photo during the slide, so the paper appears to
            pass behind the slot lip (real-printer effect). mb-[-2px]
            pulls it down 2px into the well so there is no visible gap
            between the slot and the paper. */}
        <div className="w-full h-4 bg-muted-foreground/10 rounded-full shadow-inner mb-[-2px] z-20 relative overflow-hidden">
          <div className="absolute inset-0 bg-gradient-to-b from-black/20 to-transparent" />
        </div>

        {/* Portrait well — 90% of container width, centered by the
            parent flex (items-center). The shadow lives HERE, not on
            the motion.div, and the well wrapper has NO overflow-hidden,
            so shadow shows on all four sides of the photo. The actual
            clipping of the sliding photo is done by an inner div below
            — that way the well wrapper stays unclipped and the shadow
            around the print is preserved. */}
        <div className="relative w-[90%] z-10 shadow-xl rounded-[2px]">
          {/* Inner clip container — the overflow-hidden lives here, not
              on the well wrapper. Why: the well wrapper needs to render
              its box-shadow outside its own box (shadow-xl spreads ~25
              px in every direction). If we put overflow-hidden on the
              well wrapper, that shadow gets clipped at the box edges
              and the print loses its lift. So we keep the well wrapper
              overflow-visible and put overflow-hidden one level in, on
              a container sized to match the photo (aspect-[3/2]). The
              photo (motion.div) fills this clip container absolutely;
              during the slide it sits at y: -110% which is fully
              outside the clip's top edge → invisible until the slide
              pulls it down. */}
          <div className="relative w-full aspect-[3/2] overflow-hidden">
            <motion.div
              // Re-trigger the slide animation when the user navigates
              // between different prints (different imageUrl → different key).
              key={imageUrl}
              initial={{ y: '-110%' }}
              animate={{ y: 0 }}
              transition={{ duration: 4, ease: [0.4, 0.0, 0.2, 1] }}
              className="absolute inset-0 bg-white p-2 border border-border"
            >
              <img
                src={imageUrl}
                alt="Printed Portrait"
                className="w-full h-full object-cover contrast-125 sepia-[.3]"
              />
            </motion.div>

            {/* Scan line that sweeps top -> bottom during the slide.
                Lives inside the clip container so it stays bounded by
                the print area (does not poke out above the slot). */}
            <motion.div
              key={`scan-${imageUrl}`}
              initial={{ top: '0%' }}
              animate={{ top: '100%' }}
              transition={{ duration: 4, ease: [0.4, 0.0, 0.2, 1] }}
              className="absolute left-0 right-0 h-[2px] bg-primary/30 blur-[1px] z-20 pointer-events-none"
              aria-hidden="true"
            />
          </div>
        </div>
      </div>

      {/* Caption + actions — visible immediately, no gated animation. */}
      <div className="mt-4 md:mt-8 flex flex-col items-center gap-3 text-center">
        <p className="font-sans italic text-xl text-foreground">
          Your masterpiece is ready.
        </p>

        {/* Booth printer (only if BOOTH_PRINTER_NAME is set on the server).
            The status pill above the button shows the printer name plus a
            clean Connected / Not connected label, derived from the live
            CUPS state (lpstat -p, polled every 5 s). The dot colour
            carries the busy / error detail; the rich lpstat message
            (paper-out, jam, etc.) is shown in a smaller line below for
            debugging. The button is disabled when the printer is not
            connected. */}
        {booth.available && (
          <div className="w-full max-w-xs flex flex-col items-center gap-1.5">
            <div
              className="flex items-center gap-2 text-[11px] font-sans uppercase tracking-widest text-muted-foreground whitespace-nowrap"
              role="status"
              aria-live="polite"
              title={booth.message}
            >
              <span
                className={
                  'inline-block w-2 h-2 rounded-full flex-shrink-0 ' +
                  (booth.state === 'ready'
                    ? 'bg-emerald-500'
                    : booth.state === 'busy'
                    ? 'bg-amber-500 animate-pulse'
                    : booth.state === 'error'
                    ? 'bg-red-500'
                    : 'bg-muted-foreground/40')
                }
                aria-hidden="true"
              />
              <span className="truncate max-w-full">
                {booth.printer || 'Booth printer'}
                {' · '}
                {booth.connected ? 'Connected' : 'Not connected'}
              </span>
            </div>
            {/* Rich lpstat reason — shown only when there's something
                actionable for the operator, e.g. "paper out", "offline".
                Hover the pill for the full untruncated text. */}
            {booth.message && !booth.connected && booth.message.toLowerCase() !== 'not connected' && (
              <p
                className="text-[10px] text-muted-foreground/70 text-center truncate max-w-xs"
                title={booth.message}
              >
                {booth.message}
              </p>
            )}
            <button
              onClick={handleBoothPrint}
              disabled={boothBusy || !booth.connected}
              className="mt-1 w-full px-6 py-3 bg-primary text-primary-foreground font-sans text-xs uppercase tracking-widest hover:bg-primary/90 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
            >
              <Printer className="w-4 h-4" />
              {boothBusy ? 'Sending…' : 'Print Here'}
            </button>
          </div>
        )}

        {/* System print dialog — works on every device. The user picks the
            paired Xiaomi / AirPrint printer from their OS print panel. */}
        <button
          onClick={handleSystemPrint}
          className="w-full max-w-xs px-6 py-3 border border-border font-sans text-xs uppercase tracking-widest text-foreground hover:bg-primary/5 hover:text-primary transition-all flex items-center justify-center gap-2"
        >
          <Printer className="w-4 h-4" /> Print via My Device
        </button>

        {/* Save a copy to disk. */}
        <a
          href={imageUrl}
          download={fileName}
          className="w-full max-w-xs px-6 py-3 border border-border font-sans text-xs uppercase tracking-widest text-foreground hover:bg-primary/5 hover:text-primary transition-all text-center"
        >
          Save PNG to My Device
        </a>

        {/* Booth print status / error inline. */}
        {boothMsg && (
          <p
            className={
              'mt-1 text-xs ' +
              (boothMsg.startsWith('Failed') ? 'text-rust' : 'text-muted-foreground')
            }
            role="status"
            aria-live="polite"
          >
            {boothMsg}
          </p>
        )}

        <button
          onClick={onReset}
          className="mt-2 px-6 py-3 text-foreground/60 font-sans text-xs uppercase tracking-widest hover:text-foreground transition-colors flex items-center gap-2"
        >
          <ChevronLeft className="w-4 h-4" /> Back to Homepage
        </button>
      </div>

      {/* Hidden print container. The @media print rules in globals.css show
          ONLY this block (filling the page) when the user invokes
          "Print via My Device", producing a clean 4R-only page. */}
      <div className="print-only" aria-hidden="true">
        <img src={imageUrl} alt={title} />
      </div>
    </motion.div>
  );
}