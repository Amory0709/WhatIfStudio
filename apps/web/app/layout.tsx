import "./globals.css";
import type { Metadata } from "next";
export const metadata: Metadata = { title: "WhatIf Studio · SLB", description: "Step into the frame." };
export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (<html lang="en"><body className="min-h-screen bg-paper text-ink antialiased">{children}</body></html>);
}
