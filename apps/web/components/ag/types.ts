export type AGArtwork = {
  id: string;
  title: string;
  artist: string;
  year: number;
  palette: string;
  mood: string;
  image?: string;
  subtitle?: string;
};

const BASE_TITLES = [
  'Renoir', 'Vermeer', 'Rembrandt', 'Sargent',
  'Klimt', 'Da Vinci', 'Monet', 'Van Gogh',
  'Picasso', 'Frida', 'Botticelli', 'Goya',
];

// AG App 的 12 张 Unsplash 真人肖像 URL（1:1 还原）
const BASE_UNSPLASH = [
  '/gallery/ag-1.jpg',
  '/gallery/ag-2.jpg',
  '/gallery/ag-3.jpg',
  '/gallery/ag-4.jpg',
  '/gallery/ag-5.jpg',
  '/gallery/ag-6.jpg',
  '/gallery/ag-7.jpg',
  '/gallery/ag-8.jpg',
  '/gallery/ag-9.jpg',
  '/gallery/ag-10.jpg',
  '/gallery/ag-11.jpg',
  '/gallery/ag-12.jpg',
];

const PALETTE_LABELS = ['amber', 'silver', 'forest', 'wine', 'ivory', 'slate', 'opal', 'rust'];

export function buildAGItems(realItems: AGArtwork[]): AGArtwork[] {
  const items: AGArtwork[] = [];
  const real = realItems ?? [];
  for (let i = 0; i < 50; i++) {
    const base = BASE_TITLES[i % BASE_TITLES.length];
    const img = BASE_UNSPLASH[i % BASE_UNSPLASH.length];
    if (i < real.length) {
      const r = real[i];
      items.push({
        id: r.id ?? String(i + 1),
        title: r.title ?? (base + ' ' + (i + 1)),
        artist: r.artist ?? 'Curated',
        year: r.year ?? 2024,
        palette: r.palette ?? PALETTE_LABELS[i % PALETTE_LABELS.length],
        mood: r.mood ?? '—',
        image: r.image ?? img,
      });
    } else {
      items.push({
        id: 'fig-' + (i + 1),
        title: base + ' ' + (i + 1),
        artist: 'Curated',
        year: 2024,
        palette: PALETTE_LABELS[i % PALETTE_LABELS.length],
        mood: '—',
        image: img,
      });
    }
  }
  return items;
}
