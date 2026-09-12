import "./globals.css";
import localFont from "next/font/local";
import type { Metadata } from "next";
const slb = localFont({
  src: [
    { path: '../public/fonts/SLBSans-Regular.woff2', weight: '400' },
    { path: '../public/fonts/SLBSans-Bold.woff2', weight: '700' },
  ],
  variable: '--font-slb',
  display: 'swap',
});
export const metadata: Metadata = { title: "WhatIf Studio · SLB", description: "Step into the frame." };
export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (<html lang="en" className={slb.variable}><body className="min-h-screen bg-paper text-ink antialiased">{children}</body></html>);
}
