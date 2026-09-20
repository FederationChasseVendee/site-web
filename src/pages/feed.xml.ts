import type { APIRoute } from "astro";
import { getArticlesByStatus } from "../lib/news";
import { normalizeSlug } from "../lib/content";

const escapeXml = (value: string) => value
  .replaceAll("&", "&amp;")
  .replaceAll("<", "&lt;")
  .replaceAll(">", "&gt;")
  .replaceAll('"', "&quot;")
  .replaceAll("'", "&apos;");

export const GET: APIRoute = async ({ site }) => {
  if (!site) throw new Error("L’URL de production Astro est requise pour générer le flux.");
  const root = new URL("/site-web/", site);
  const feedUrl = new URL("feed.xml", root);
  const articles = (await getArticlesByStatus(false)).slice(0, 20);
  const updated = articles[0]?.data.date ?? new Date("2026-09-21T00:00:00Z");
  const entries = articles.map((article) => {
    const url = new URL(`${normalizeSlug(article.id)}/`, root).href;
    return `  <entry>
    <title>${escapeXml(article.data.title)}</title>
    <id>${escapeXml(url)}</id>
    <link href="${escapeXml(url)}" />
    <published>${article.data.date.toISOString()}</published>
    <updated>${article.data.date.toISOString()}</updated>
    <category term="${escapeXml(article.data.category)}" />
    <summary>${escapeXml(article.data.summary)}</summary>
  </entry>`;
  }).join("\n");

  const xml = `<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom" xml:lang="fr">
  <title>Actualités — Fédération des Chasseurs de la Vendée</title>
  <id>${escapeXml(root.href)}</id>
  <link href="${escapeXml(root.href)}" />
  <link href="${escapeXml(feedUrl.href)}" rel="self" type="application/atom+xml" />
  <updated>${updated.toISOString()}</updated>
${entries}
</feed>
`;
  return new Response(xml, { headers: { "Content-Type": "application/atom+xml; charset=utf-8" } });
};
