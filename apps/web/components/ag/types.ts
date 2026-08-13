export type AGArtwork = {
  id: string;
  title: string;
  artist: string;
  year: number;
  palette: string;
  image?: string;
  subtitle?: string;
};

const BASE_TITLES = [
  'Renoir', 'Vermeer', 'Rembrandt', 'Sargent',
  'Klimt', 'Da Vinci', 'Monet', 'Van Gogh',
  'Picasso', 'Frida', 'Botticelli', 'Goya',
];

// 50-card 3D gallery track 的填充图:循环使用本仓库的 14 张人像照片,
// 这样 i>=14 的占位卡也指向真实存在的文件,不会 404。
const BASE_FILLER = [
  '/gallery/tier-2-people-armoring-manufacturing-facility-lawrence-nal-6613-4inch.jpg',
  '/gallery/tier-2-people-chx-manufacturing-facility-chemicals-midland-nal-1432-4inch.jpg',
  '/gallery/tier-2-people-chx-production-facility-chemicals-midland-nal-8280-4inch.jpg',
  '/gallery/tier-2-people-chx-production-facility-chemicals-midland-nal-9096-4inch.jpg',
  '/gallery/tier-2-people-chx-production-facility-chemicals-midland-nal-9678-4inch.jpg',
  '/gallery/tier-2-people-chx-production-facility-chemicals-midland-nal-9823-4inch.jpg',
  '/gallery/tier-2-people-drilling-offshore-operations-el-nido-asa-3917-4inch.jpg',
  '/gallery/tier-2-people-land-operations-phitsanulok-asa-2753-4inch.jpg',
  '/gallery/tier-2-people-lead-extrusion-manufacturing-facility-lawrence-nal-6076-2-4inch.jpg',
  '/gallery/tier-2-project-electris-completions-chpc-ardmore-houston-nal-0205-4inch.jpg',
  '/gallery/tier-2-project-electris-completions-chpc-ardmore-houston-nal-0361-4inch.jpg',
  '/gallery/tier-2-project-electris-completions-chpc-ardmore-houston-nal-0434-4inch.jpg',
  '/gallery/family-day-19-4inch.jpg',
  '/gallery/family-day-9-4inch.jpg',
];

const PALETTE_LABELS = ['amber', 'silver', 'forest', 'wine', 'ivory', 'slate', 'opal', 'rust'];

export function buildAGItems(realItems: AGArtwork[]): AGArtwork[] {
  const items: AGArtwork[] = [];
  const real = realItems ?? [];
  for (let i = 0; i < 50; i++) {
    const base = BASE_TITLES[i % BASE_TITLES.length];
    const img = BASE_FILLER[i % BASE_FILLER.length];
    if (i < real.length) {
      const r = real[i];
      items.push({
        id: r.id ?? String(i + 1),
        title: r.title ?? (base + ' ' + (i + 1)),
        artist: r.artist ?? 'Curated',
        year: r.year ?? 2024,
        palette: r.palette ?? PALETTE_LABELS[i % PALETTE_LABELS.length],
        image: r.image ?? img,
      });
    } else {
      items.push({
        id: 'fig-' + (i + 1),
        title: base + ' ' + (i + 1),
        artist: 'Curated',
        year: 2024,
        palette: PALETTE_LABELS[i % PALETTE_LABELS.length],
        image: img,
      });
    }
  }
  return items;
}
