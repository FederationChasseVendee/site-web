import { existsSync, readFileSync, readdirSync } from "node:fs";
import { extname, join, relative } from "node:path";

const base = "/site-web/";
const distDirectory = "dist";
const site = JSON.parse(readFileSync("src/content/site.json", "utf8"));

function walk(directory) {
  return readdirSync(directory, { withFileTypes: true }).flatMap((entry) => {
    const path = join(directory, entry.name);
    return entry.isDirectory() ? walk(path) : [path];
  });
}

function targetFor(url) {
  const withoutBase = url.slice(base.length).split(/[?#]/)[0];
  if (!withoutBase) return join(distDirectory, "index.html");
  return withoutBase.endsWith("/")
    ? join(distDirectory, withoutBase, "index.html")
    : join(distDirectory, withoutBase);
}

const htmlFiles = walk(distDirectory).filter((file) => extname(file) === ".html");
const routeFiles = htmlFiles.filter((file) => !file.endsWith("404.html"));
const documentFiles = walk(join(distDirectory, "assets", "documents"))
  .filter((file) => extname(file).toLowerCase() === ".pdf");

for (const htmlFile of htmlFiles) {
  const html = readFileSync(htmlFile, "utf8");
  const displayPath = relative(distDirectory, htmlFile);
  const h1Count = (html.match(/<h1(?:\s|>)/g) ?? []).length;

  if (!html.includes('href="#contenu"') || !html.includes('<main id="contenu">')) {
    throw new Error(`Lien d’évitement ou zone principale absent dans ${displayPath}`);
  }
  if (h1Count !== 1) {
    throw new Error(`${displayPath} doit contenir exactement un titre h1 (trouvé : ${h1Count}).`);
  }
  if (html.includes("\uFFFD")) {
    throw new Error(`Caractère de remplacement Unicode détecté dans ${displayPath}.`);
  }

  for (const image of html.matchAll(/<img\b[^>]*>/g)) {
    if (!/\salt="[^"]*"/.test(image[0])) {
      throw new Error(`Image sans attribut alt dans ${displayPath}`);
    }
  }

  for (const match of html.matchAll(/(?:href|src)="(\/site-web\/[^"]*)"/g)) {
    const target = targetFor(match[1]);
    if (!existsSync(target)) {
      throw new Error(`Cible locale absente dans ${displayPath} : ${match[1]}`);
    }
  }

  for (const anchor of html.matchAll(/<a\b[^>]*target="_blank"[^>]*>.*?<\/a>/gs)) {
    if (!/\srel="[^"]*noreferrer[^"]*"/.test(anchor[0]) || !anchor[0].includes("nouvel onglet")) {
      throw new Error(`Lien externe non annoncé ou sans rel=noreferrer dans ${displayPath}`);
    }
  }
}

for (const file of documentFiles) {
  if (readFileSync(file).subarray(0, 4).toString("ascii") !== "%PDF") {
    throw new Error(`Le document ${relative(distDirectory, file)} n’est pas un PDF valide.`);
  }
}

const redirectDirectory = join("src", "content", "redirects");
const redirectFiles = walk(redirectDirectory).filter((file) => extname(file) === ".md");
for (const file of redirectFiles) {
  const source = readFileSync(file, "utf8");
  const destination = source.match(/^destination:\s*(.+)$/m)?.[1]?.trim();
  if (!destination) {
    throw new Error(`Destination absente dans ${file}.`);
  }

  const route = relative(redirectDirectory, file).replace(/\\/g, "/").replace(/\.md$/, "");
  const html = readFileSync(join(distDirectory, ...route.split("/"), "index.html"), "utf8");
  const resolvedDestination = `${base}${destination.replace(/^\/+/, "")}`;
  const canonicalDestination = new URL(resolvedDestination, "https://federationchassevendee.github.io").href;

  if (!html.includes(`content="0; url=${resolvedDestination}"`)) {
    throw new Error(`Redirection HTML absente ou incorrecte pour /${route}/.`);
  }
  if (!html.includes(`rel="canonical" href="${canonicalDestination}"`)) {
    throw new Error(`URL canonique incorrecte pour /${route}/.`);
  }
  if (!html.includes(`href="${resolvedDestination}"`)) {
    throw new Error(`Lien de secours visible absent pour /${route}/.`);
  }
}

const homeHtml = readFileSync(join(distDirectory, "index.html"), "utf8");
const navigationBlocks = [...homeHtml.matchAll(/<nav[^>]*aria-label="Navigation principale"[^>]*>(.*?)<\/nav>/gs)];
if (navigationBlocks.length !== 2) {
  throw new Error("Les navigations principale mobile et bureau n’ont pas été trouvées.");
}

const expectedNavigation = site.navigation.map(({ url }) => `${base}${url}`);
for (const [, navigationHtml] of navigationBlocks) {
  const links = [...navigationHtml.matchAll(/href="(\/site-web\/[^"#?]*)"/g)].map((match) => match[1]);
  if (links.length !== 6 || expectedNavigation.some((href) => !links.includes(href))) {
    throw new Error("La navigation principale doit contenir exactement les six rubriques configurées.");
  }
}

for (const action of site.primaryActions) {
  const href = /^https?:|^mailto:|^tel:/.test(action.url) ? action.url : `${base}${action.url}`;
  if (!homeHtml.includes(`href="${href}"`)) {
    throw new Error(`Action prioritaire absente de l’accueil : ${action.label}`);
  }
}

if (!homeHtml.includes(`href="${base}" aria-label="${site.shortName} — Accueil"`)) {
  throw new Error("Le logo ne fournit pas de retour explicite vers l’accueil.");
}

for (const htmlFile of routeFiles) {
  if (htmlFile.endsWith(join(distDirectory, "index.html"))) continue;
  const html = readFileSync(htmlFile, "utf8");
  if (!html.includes('aria-label="Fil d’Ariane"')) {
    throw new Error(`Fil d’Ariane absent dans ${relative(distDirectory, htmlFile)}`);
  }
}

console.log(
  `${routeFiles.length} routes, ${redirectFiles.length} redirections, ${documentFiles.length} PDF, leurs liens, leurs médias et les repères d’accessibilité ont été vérifiés sous ${base}.`,
);
