import { getCollection, type CollectionEntry } from "astro:content";

export const NEWS_PAGE_SIZE = 12;

export function isArchivedArticle(entry: CollectionEntry<"articles">, now = new Date()): boolean {
  return entry.data.archived || Boolean(entry.data.expiresAt && entry.data.expiresAt < now);
}

export async function getArticlesByStatus(archived: boolean): Promise<CollectionEntry<"articles">[]> {
  const now = new Date();
  return (await getCollection("articles"))
    .filter((entry) => isArchivedArticle(entry, now) === archived)
    .sort((a, b) => b.data.date.valueOf() - a.data.date.valueOf());
}

export function pageCount(items: unknown[]): number {
  return Math.max(1, Math.ceil(items.length / NEWS_PAGE_SIZE));
}

export function pageItems<T>(items: T[], page: number): T[] {
  const start = (page - 1) * NEWS_PAGE_SIZE;
  return items.slice(start, start + NEWS_PAGE_SIZE);
}

export function formatFrenchDate(value: Date): string {
  return new Intl.DateTimeFormat("fr-FR", {
    day: "numeric",
    month: "long",
    year: "numeric",
  }).format(value);
}
