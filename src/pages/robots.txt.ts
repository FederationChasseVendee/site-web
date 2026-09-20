import type { APIRoute } from "astro";

export const GET: APIRoute = ({ site }) => {
  if (!site) throw new Error("L’URL de production Astro est requise pour générer robots.txt.");
  const sitemap = new URL("/site-web/sitemap.xml", site);
  return new Response(`User-agent: *
Allow: /site-web/

Sitemap: ${sitemap.href}
`, { headers: { "Content-Type": "text/plain; charset=utf-8" } });
};
