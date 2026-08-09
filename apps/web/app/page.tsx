import { StudioShell } from "@/components/ag/StudioShell";
import { loadGallery } from '@/lib/gallery';
import { buildAGItems } from '@/components/ag/types';

export default async function HomePage() {
  const real = await loadGallery();
  const items = buildAGItems(real);
  return (
    <main className="relative min-h-screen overflow-hidden">
      <StudioShell items={items} />
    </main>
  );
}
