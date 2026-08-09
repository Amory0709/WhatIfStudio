"use client";
import { useMemo } from 'react';

const PALETTES: Record<string, string> = {
  amber:  'from-[#E8C088] via-[#C68B4F] to-[#5C3214]',
  silver: 'from-[#E6E6E6] via-[#9C9C9C] to-[#2A2A2A]',
  forest: 'from-[#9CB69C] via-[#4F6B4F] to-[#1E2A1E]',
  wine:   'from-[#8B3A3A] via-[#5A1E1E] to-[#1A0606]',
  ivory:  'from-[#F1ECDF] via-[#D8CFB7] to-[#8B8268]',
  slate:  'from-[#A6A8AD] via-[#5B5F66] to-[#16181B]',
  opal:   'from-[#E8E1F5] via-[#9C9BC2] to-[#2D2A4A]',
  rust:   'from-[#D8916A] via-[#A04A2A] to-[#2E1006]',
};

export function GradientTile({ palette, className = '' }: { palette: string; className?: string }) {
  const cls = useMemo(() => PALETTES[palette] || PALETTES.ivory, [palette]);
  return (
    <div className={'relative h-full w-full overflow-hidden bg-gradient-to-br ' + cls + ' ' + className}>
      <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_30%_20%,rgba(255,255,255,0.35),transparent_60%)]" />
    </div>
  );
}
