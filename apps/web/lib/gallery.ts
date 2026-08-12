import "server-only";
import { promises as fs } from "fs";
import path from "path";

export type Artwork = {
  id: string;
  title: string;
  artist: string;
  year: number;
  palette: string;
  image?: string;
};

const EXTS = ["jpg", "jpeg", "png", "webp"] as const;

async function resolveImageFile(id: string, galleryDir: string): Promise<string | null> {
  for (const ext of EXTS) {
    const p = path.join(galleryDir, id + "." + ext);
    try {
      const s = await fs.stat(p);
      if (s.isFile()) return id + "." + ext;
    } catch { /* keep trying */ }
  }
  return null;
}

export async function loadGallery(): Promise<Artwork[]> {
  const dataFile = path.join(process.cwd(), "..", "..", "data", "gallery.json");
  const galleryDir = path.join(process.cwd(), "public", "gallery");
  const raw: Artwork[] = JSON.parse(await fs.readFile(dataFile, "utf8"));
  return Promise.all(
    raw.map(async (art) => {
      const file = await resolveImageFile(art.id, galleryDir);
      return file ? { ...art, image: "/gallery/" + file } : art;
    }),
  );
}

export async function loadOne(id: string): Promise<Artwork | undefined> {
  const all = await loadGallery();
  return all.find((a) => a.id === id);
}
