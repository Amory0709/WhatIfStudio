import { notFound } from "next/navigation";
import { loadOne, loadGallery } from "@/lib/gallery";
import { StudioShell } from "@/components/ag/StudioShell";
import { buildAGItems } from "@/components/ag/types";

export async function generateStaticParams() {
  const all = await loadGallery();
  return all.map((a) => ({ id: a.id }));
}

export const dynamicParams = false;

export default async function PrintPage({ params }: { params: { id: string } }) {
  const all = await loadGallery();
  const items = buildAGItems(all);
  const art = await loadOne(params.id);
  if (!art) return notFound();
  // SSR placeholder so ResultView renders into HTML. The client effect below replaces
  // this with the real sessionStorage blob URL (the swapped-face PNG) once mounted.
  const initialPrintUrl = art.image ?? `/gallery/${params.id}.jpg`;
  return (
    <main className="relative min-h-screen overflow-hidden">
      <StudioShell items={items} initialId={params.id} initialStep="result" initialPrintUrl={initialPrintUrl} />
    </main>
  );
}
