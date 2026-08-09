"use client";
import { motion } from 'framer-motion';
import { X, Check } from 'lucide-react';

export function AgreementModal({ onClose, onAgree, method }: { onClose: () => void; onAgree: () => void; method: string | null }) {
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
        className="relative bg-card border border-border p-8 md:p-12 max-w-lg w-full shadow-2xl flex flex-col"
      >
        <button onClick={onClose} className="absolute top-6 right-6 text-muted-foreground hover:text-primary">
          <X className="w-5 h-5" />
        </button>

        <h3 className="text-3xl italic mb-6">Terms of Exhibition</h3>
        <div className="font-sans text-sm font-light text-muted-foreground space-y-4 mb-10 h-48 overflow-y-auto pr-2 custom-scrollbar">
          <p>By proceeding, you grant What If Studio temporary consent to process your portrait for the sole purpose of artistic synthesis.</p>
          <p>Your image will not be permanently stored, distributed, or utilized outside the scope of this immediate digital exhibition.</p>
          <p>The resulting artwork is an algorithmic interpretation and remains a collaborative digital artifact. The 'slb' mark will be applied to signify its origin.</p>
          <p>Do you consent to these terms to initiate the {method} process?</p>
        </div>

        <div className="flex gap-4 mt-auto">
          <button
            onClick={onClose}
            className="flex-1 py-4 font-sans text-xs uppercase tracking-widest border border-border text-foreground hover:bg-primary/5 transition-colors"
          >
            Decline
          </button>
          <button
            onClick={onAgree}
            className="flex-1 py-4 font-sans text-xs uppercase tracking-widest bg-primary text-primary-foreground hover:bg-primary/90 transition-colors flex items-center justify-center gap-2"
          >
            <Check className="w-4 h-4" /> I Consent
          </button>
        </div>
      </motion.div>
    </div>
  );
}
