"use client";
import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { GradientTile } from './GradientTile';
import type { AGArtwork } from './types';

export function GalleryView({ items, onSelect }: { items: AGArtwork[]; onSelect: (img: AGArtwork) => void }) {
  const [currentIndex, setCurrentIndex] = useState(0);
  const [isMobile, setIsMobile] = useState(false);
  const total = items.length;

  useEffect(() => {
    const check = () => setIsMobile(typeof window !== 'undefined' && window.innerWidth < 768);
    check();
    window.addEventListener('resize', check);
    return () => window.removeEventListener('resize', check);
  }, []);

  const handleDragEnd = (_e: any, info: any) => {
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

  const activeIndex = ((currentIndex % total) + total) % total;
  function activeIndexCalc() { return ((currentIndex % total) + total) % total; }
  const activeImage = items[activeIndex];
  const R = isMobile ? 300 : 700;

  return (
    <div className="absolute inset-0 flex flex-col items-center justify-center overflow-hidden">
      <div
        className="relative w-full h-[50vh] md:h-[60vh] flex items-center justify-center touch-none preserve-3d translate-y-4 md:translate-y-8"
        style={{ perspective: '4000px' }}
      >
        <div
          className="w-full h-full preserve-3d"
          style={{ transform: 'scale(0.28) rotateX(-35deg)' }}
        >
          <div
            className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 pointer-events-none flex items-center justify-center font-sans italic select-none"
            style={{
              color: '#0033CC',
              transform:
                'translateX(' +
                (isMobile ? -1500 : -3000) +
                'px) translateY(500px) translateZ(-1000px) rotateX(80deg) rotateZ(-4deg)',
              fontSize: '1800px',
              opacity: 1,
              lineHeight: 0.8,
            }}
          >
            1
          </div>

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
                  transition={{ type: 'spring', stiffness: 50, damping: 20, mass: 1 }}
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
                      'w-full h-full relative overflow-hidden bg-muted transition-all duration-700 ' +
                      (isCenter
                        ? 'border-2 border-primary shadow-[0_30px_80px_-20px_rgba(0,51,204,0.5)] grayscale-0 ring-4 ring-primary/20'
                        : 'border border-border/50 grayscale opacity-40 hover:opacity-100 hover:grayscale-0 hover:border-primary/60 hover:scale-[1.06] transition-all duration-500 ease-out cursor-pointer')
                    }
                    style={{ backfaceVisibility: 'hidden' }}
                  >
                    {img.image ? (
                      <img src={img.image} alt={img.title} className="w-full h-full object-cover" />
                    ) : (
                      <GradientTile palette={img.palette} />
                    )}
                    {!isCenter && <div className="absolute inset-0 bg-white/10 backdrop-blur-[1px]" />}
                  </div>
                  <div
                    className={
                      'absolute inset-0 w-full h-full overflow-hidden bg-muted transition-all duration-700 ' +
                      (isCenter
                        ? 'border-2 border-primary shadow-[0_30px_80px_-20px_rgba(0,51,204,0.5)] grayscale-0 ring-4 ring-primary/20'
                        : 'border border-border/50 grayscale opacity-40 hover:opacity-100 hover:grayscale-0 hover:border-primary/60 hover:scale-[1.06] transition-all duration-500 ease-out cursor-pointer')
                    }
                    style={{ transform: 'rotateY(180deg)', backfaceVisibility: 'hidden' }}
                  >
                    {img.image ? (
                      <img src={img.image} alt={img.title} className="w-full h-full object-cover transform -scale-x-100" />
                    ) : (
                      <GradientTile palette={img.palette} />
                    )}
                    {!isCenter && <div className="absolute inset-0 bg-white/10 backdrop-blur-[1px]" />}
                  </div>
                </motion.div>
              );
            })}
          </motion.div>
        </div>
      </div>

      {/* Caption + Continue — always visible, updates as you spin the track. */}
      <div className="absolute bottom-24 left-0 right-0 flex flex-col items-center justify-center pointer-events-none">
        <AnimatePresence mode="wait">
          <motion.div
            key={activeImage.id}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            transition={{ duration: 0.3 }}
            className="text-center"
          >
            <p className="text-[10px] font-sans uppercase tracking-[0.3em] text-muted-foreground">
              {activeImage.artist} &middot; {activeImage.year}
            </p>
            <h2 className="mt-2 text-4xl md:text-5xl italic text-primary font-sans">
              {activeImage.title}
            </h2>
            <p className="mt-3 text-xs font-sans uppercase tracking-widest text-muted-foreground">
              Now Selected
            </p>
            <button
              type="button"
              onClick={() => onSelect(activeImage)}
              className="pointer-events-auto mt-5 px-8 py-3 bg-primary text-primary-foreground font-sans text-xs uppercase tracking-widest hover:bg-primary/90 transition-all hover:scale-[1.02] shadow-lg shadow-primary/30"
            >
              Continue &rarr;
            </button>
          </motion.div>
        </AnimatePresence>
      </div>

      <div className="absolute bottom-8 left-1/2 -translate-x-1/2 text-[10px] font-sans uppercase tracking-widest text-muted-foreground flex items-center gap-8 opacity-80 z-50">
        <button onClick={() => setCurrentIndex((p) => p - 1)} className="hover:text-primary transition-colors py-2">&larr; Prev</button>
        <span className="opacity-50 tracking-[0.2em]">Drag to Spin &infin;</span>
        <button onClick={() => setCurrentIndex((p) => p + 1)} className="hover:text-primary transition-colors py-2">Next &rarr;</button>
      </div>
    </div>
  );
}