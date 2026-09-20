import { existsSync, readFileSync, readdirSync } from "node:fs";
import { basename, join } from "node:path";

const base = "/site-web/";
const contentDirectory = "src/content/pages";
const reserved = new Set(["404", "index"]);
const pageFiles = readdirSync(contentDirectory).filter((file) => file.endsWith(".md"));
const homeHtml = readFileSync("dist/index.html", "utf8");
const slugs = new Set();
const visibleSlugs = new Set();

for (const file of pageFiles) {
  const slug = basename(file, ".md").toLowerCase();
  if (reserved.has(slug)) {
    throw new Error(`Slug réservé détecté : ${slug}`);
  }
  if (slugs.has(slug)) {
    throw new Error(`Slug en double détecté : ${slug}`);
  }
  slugs.add(slug);

  const source = readFileSync(join(contentDirectory, file), "utf8");
  const visible = !/^showInNavigation:\s*false\s*$/m.test(source);
  const href = `href="${base}${slug}/"`;
  const route = join("dist", slug, "index.html");

  if (!existsSync(route)) {
    throw new Error(`Route manquante pour ${file} : ${route}`);
  }
  if (visible && !homeHtml.includes(href)) {
    throw new Error(`Lien de navigation manquant pour ${file}`);
  }
  if (!visible && homeHtml.includes(href)) {
    throw new Error(`La page masquée ${file} apparaît dans la navigation`);
  }
  if (visible) visibleSlugs.add(slug);
}

const expectedNavigation = new Set([base, ...[...visibleSlugs].map((slug) => `${base}${slug}/`)]);
const navigationBlocks = [...homeHtml.matchAll(/<nav[^>]*aria-label="Navigation principale"[^>]*>(.*?)<\/nav>/g)];

if (navigationBlocks.length !== 2) {
  throw new Error("Les navigations mobile et bureau n’ont pas été trouvées.");
}

for (const [, navigationHtml] of navigationBlocks) {
  const actualNavigation = new Set(
    [...navigationHtml.matchAll(/href="(\/site-web\/[^"#?]*)"/g)].map((match) => match[1]),
  );

  for (const href of expectedNavigation) {
    if (!actualNavigation.has(href)) {
      throw new Error(`Lien attendu absent de la navigation : ${href}`);
    }
  }
  for (const href of actualNavigation) {
    if (!expectedNavigation.has(href)) {
      throw new Error(`Lien obsolète ou inconnu dans la navigation : ${href}`);
    }
  }
}

const htmlFiles = [
  "dist/index.html",
  "dist/404.html",
  ...[...slugs].map((slug) => join("dist", slug, "index.html")),
];

for (const htmlFile of htmlFiles) {
  const html = readFileSync(htmlFile, "utf8");
  for (const match of html.matchAll(/(?:href|src)="(\/site-web\/[^"#?]*)"/g)) {
    const relativePath = match[1].slice(base.length);
    if (!relativePath) continue;

    const target = relativePath.endsWith("/")
      ? join("dist", relativePath, "index.html")
      : join("dist", relativePath);

    if (!existsSync(target)) {
      throw new Error(`Cible locale absente dans ${htmlFile} : ${match[1]}`);
    }
  }
}

console.log(`Navigation et routes vérifiées pour ${pageFiles.length} page(s) secondaire(s).`);
