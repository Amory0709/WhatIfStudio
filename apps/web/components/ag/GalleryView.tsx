"use client";
import { useState, useEffect } from 'react';
import { motion, AnimatePresence, useReducedMotion, type PanInfo } from 'framer-motion';
import { GradientTile } from './GradientTile';
import { LiquidLight } from './LiquidLight';
import type { AGArtwork } from './types';

export function GalleryView({ items, onSelect }: { items: AGArtwork[]; onSelect: (img: AGArtwork) => void }) {
  const [currentIndex, setCurrentIndex] = useState(0);
  const [isMobile, setIsMobile] = useState(false);
  const total = items.length;
  const reduceMotion = useReducedMotion();

  useEffect(() => {
    const check = () => setIsMobile(typeof window !== 'undefined' && window.innerWidth < 768);
    check();
    window.addEventListener('resize', check);
    return () => window.removeEventListener('resize', check);
  }, []);

  const handleDragEnd = (_e: MouseEvent | TouchEvent | PointerEvent, info: PanInfo) => {
    // info.offset is the cumulative drag distance (unclamped now that
    // dragConstraints are removed). ~80px ≈ one card width on the
    // 280px-wide carousel.
    const swipe = info.offset.x;
    const itemsToMove = Math.round(-swipe / 80);
    if (itemsToMove !== 0) {
      setCurrentIndex((prev) => prev + itemsToMove);
    } else if (swipe < -30) {
      setCurrentIndex((p) => p + 1);
    } else if (swipe > 30) {
      setCurrentIndex((p) => p - 1);
    }
  };

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.target instanceof HTMLElement && e.target.closest('button, a, input, textarea, select, [contenteditable]')) return;
      if (e.key === 'ArrowRight') setCurrentIndex((p) => p + 1);
      if (e.key === 'ArrowLeft') setCurrentIndex((p) => p - 1);
      if (e.key === 'Enter') {
        const a = items[activeIndexCalc()];
        if (a) onSelect(a);
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  });

  const activeIndex = total ? ((currentIndex % total) + total) % total : 0;
  function activeIndexCalc() { return ((currentIndex % total) + total) % total; }
  const activeImage = items[activeIndex];
  const R = isMobile ? 300 : 700;

  if (!activeImage) return <div className="flex h-full items-center justify-center">No portraits available.</div>;

  return (
    <div className="liquid-gallery absolute inset-0 flex flex-col items-center justify-center overflow-hidden">
      <LiquidLight />
      <div
        className="relative w-full h-[50vh] md:h-[60vh] flex items-center justify-center touch-none preserve-3d gallery-track"
        style={{ perspective: '4000px' }}
      >
        <div
          className="w-full h-full preserve-3d"
          style={{ transform: 'scale(0.28) rotateX(-35deg)' }}
        >
          <motion.div
            className="relative w-full h-full flex items-center justify-center preserve-3d"
            drag="x"
            dragSnapToOrigin
            dragElastic={0.2}
            dragMomentum={false}
            onDragEnd={handleDragEnd}
          >
            {items.map((img, index) => {
              const isCenter = index === activeIndex;
              const offset = index - currentIndex;
              const t = (offset / total) * Math.PI * 2;
              const t_mod = ((t % (Math.PI * 2)) + Math.PI * 2) % (Math.PI * 2);
              const isRightCircle = t_mod < Math.PI;
              const theta = 2 * t_mod;
              let x, z, dx, dz;
              if (isRightCircle) {
                x = R * (1 - Math.cos(theta));
                z = R * Math.sin(theta);
                dx = 2 * R * Math.sin(theta);
                dz = 2 * R * Math.cos(theta);
              } else {
                x = R * (-1 + Math.cos(theta));
                z = R * Math.sin(theta);
                dx = -2 * R * Math.sin(theta);
                dz = 2 * R * Math.cos(theta);
              }
              let angle = Math.atan2(dx, dz) * (180 / Math.PI);
              if (angle < 0) angle += 360;

              return (
                <motion.div
                  key={img.id}
                  className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[60vw] md:w-[420px] aspect-[3/2] preserve-3d cursor-pointer"
                  animate={{
                    x,
                    y: isCenter ? (isMobile ? -380 : -560) : 0,
                    z,
                    rotateY: angle,
                    scale: isCenter ? 2 : 0.9,
                    zIndex: isCenter ? 100 : 10,
                  }}
                  transition={reduceMotion ? { duration: 0 } : { type: 'spring', stiffness: 50, damping: 20, mass: 1 }}
                  onClick={() => {
                    if (isCenter) {
                      onSelect(img);
                    } else {
                      let diff = index - activeIndex;
                      if (diff > total / 2) diff -= total;
                      if (diff < -total / 2) diff += total;
                      setCurrentIndex((prev) => prev + diff);
                    }
                  }}
                >
                  <div
                    className={
                      'glass-artwork w-full h-full relative overflow-hidden transition-all duration-700 ' +
                      (isCenter
                        ? 'glass-artwork-active'
                        : 'glass-artwork-orbit hover:opacity-100 hover:scale-[1.04]')
                    }
                    style={{ backfaceVisibility: 'hidden' }}
                  >
                    {img.image ? (
                      <img src={img.image} alt={img.title} className="w-full h-full object-cover" />
                    ) : (
                      <GradientTile palette={img.palette} />
                    )}
                    <div className="glass-artwork-sheen" aria-hidden="true" />
                  </div>
                  <div
                    className={
                      'glass-artwork absolute inset-0 w-full h-full overflow-hidden transition-all duration-700 ' +
                      (isCenter
                        ? 'glass-artwork-active'
                        : 'glass-artwork-orbit hover:opacity-100 hover:scale-[1.04]')
                    }
                    style={{ transform: 'rotateY(180deg)', backfaceVisibility: 'hidden' }}
                  >
                    {img.image ? (
                      <img src={img.image} alt={img.title} className="w-full h-full object-cover transform -scale-x-100" />
                    ) : (
                      <GradientTile palette={img.palette} />
                    )}
                    <div className="glass-artwork-sheen" aria-hidden="true" />
                  </div>
                </motion.div>
              );
            })}
          </motion.div>
        </div>
      </div>

      {/* Caption + Continue — always visible, updates as you spin the track. */}
      <div className="gallery-caption absolute left-4 right-4 flex flex-col items-center justify-center pointer-events-none">
        <AnimatePresence mode="wait">
          <motion.div
            key={activeImage.id}
            initial={{ opacity: 0, y: reduceMotion ? 0 : 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: reduceMotion ? 0 : -10 }}
            transition={{ duration: 0.3 }}
            className="text-center max-w-full"
          >
            <p className="text-xs font-sans uppercase tracking-[0.22em] text-muted-foreground">
              {activeImage.artist} &middot; {activeImage.year}
            </p>
            <h2 className="gallery-title mt-2 text-3xl md:text-5xl italic text-primary font-sans">
              {activeImage.title}
            </h2>
            <p className="mt-3 text-xs font-sans uppercase tracking-widest text-muted-foreground">
              Now Selected
            </p>
            <button
              type="button"
              onClick={() => onSelect(activeImage)}
              className="glass-continue pointer-events-auto mt-4 px-8 py-3 font-sans text-sm uppercase tracking-widest transition-all hover:scale-[1.02]"
            >
              Continue &rarr;
            </button>
          </motion.div>
        </AnimatePresence>
      </div>

      <div className="glass-dock absolute left-1/2 -translate-x-1/2 text-xs font-sans uppercase tracking-widest flex items-center gap-3 md:gap-6 z-40">
        <button onClick={() => setCurrentIndex((p) => p - 1)} className="hover:text-primary transition-colors px-3 py-3">&larr; Prev</button>
        <span className="text-muted-foreground whitespace-nowrap tracking-[0.12em]">Drag to Spin &infin;</span>
        <button onClick={() => setCurrentIndex((p) => p + 1)} className="hover:text-primary transition-colors px-3 py-3">Next &rarr;</button>
      </div>
    </div>
  );
}