import { notFound } from "next/navigation";
import { loadOne, loadGallery } from "@/lib/gallery";
import { StudioShell } from "@/components/ag/StudioShell";
import { buildAGItems } from "@/components/ag/types";

export default async function SwapPage({ params }: { params: { id: string } }) {
  const all = await loadGallery();
  const items = buildAGItems(all);
  const art = await loadOne(params.id);
  if (!art) return notFound();
  // 直接复用 StudioShell；initialId 让它在挂载时跳到 detail
  return (
    <main className="relative min-h-screen overflow-hidden">
      <StudioShell items={items} initialId={params.id} />
    </main>
  );
}
