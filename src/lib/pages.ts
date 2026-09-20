import { getCollection, type CollectionEntry } from "astro:content";

const reservedSlugs = new Set(["404", "index"]);

export interface SitePage {
  entry: CollectionEntry<"pages">;
  slug: string;
}

function normalizeSlug(id: string): string {
  return id
    .replace(/\\/g, "/")
    .replace(/\.(md|mdx)$/i, "")
    .replace(/^\/+|\/+$/g, "")
    .toLowerCase();
}

export async function getSitePages(): Promise<SitePage[]> {
  const entries = await getCollection("pages");
  const seen = new Set<string>();

  const pages = entries.map((entry) => {
    const slug = normalizeSlug(entry.id);
    const segments = slug.split("/");

    if (!slug || segments.some((segment) => reservedSlugs.has(segment))) {
      throw new Error(
        `Le fichier "${entry.id}" utilise un slug réservé. Choisissez un nom différent de "index" et "404".`,
      );
    }

    if (seen.has(slug)) {
      throw new Error(`Plusieurs pages produisent l’URL "/${slug}/". Chaque nom de fichier doit être unique.`);
    }

    seen.add(slug);
    return { entry, slug };
  });

  return pages.sort((a, b) => {
    const order = a.entry.data.navigationOrder - b.entry.data.navigationOrder;
    return order || a.entry.data.title.localeCompare(b.entry.data.title, "fr");
  });
}

export async function getNavigationPages(): Promise<SitePage[]> {
  return (await getSitePages()).filter(({ entry }) => entry.data.showInNavigation);
}
