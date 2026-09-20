from __future__ import annotations

import concurrent.futures
import hashlib
import html
import json
import re
import shutil
import sys
import unicodedata
from datetime import datetime, timedelta, timezone
from io import BytesIO
from pathlib import Path
from urllib.parse import unquote, urljoin, urlparse
from xml.etree import ElementTree

import html2text
import requests
from bs4 import BeautifulSoup
from PIL import Image, ImageOps


ROOT = Path(__file__).resolve().parents[1]
SITEMAP_URL = "https://chasseur-vendeen.fr/post-sitemap.xml"
OLD_ORIGIN = "https://chasseur-vendeen.fr"
SITE_BASE = "/site-web/"
ARTICLES_DIRECTORY = ROOT / "src" / "content" / "articles"
IMAGES_DIRECTORY = ROOT / "public" / "assets" / "articles"
DOCUMENTS_DIRECTORY = ROOT / "public" / "assets" / "documents" / "actualites"
REPORT_PATH = ROOT / "docs" / "migration-actualites.json"
MARKDOWN_REPORT_PATH = ROOT / "docs" / "migration-actualites.md"
USER_AGENT = "FDC85 static migration (https://github.com/FederationChasseVendee/site-web)"
REQUEST_HEADERS = {"User-Agent": USER_AGENT, "Accept": "text/html,application/xhtml+xml"}
DOCUMENT_EXTENSIONS = {".pdf", ".doc", ".docx", ".odt", ".xls", ".xlsx"}
DOWNLOAD_EXTENSION_OVERRIDES = {"/download/62026/": ".png"}
LINK_REWRITES = {
    "https://permisdechasser.ofb.gouv.fr": f"{SITE_BASE}permis-et-formations/passer-son-permis/",
    "https://urlz.fr/rEcD": f"{SITE_BASE}contact/",
    "https://www.labellucie.com/": "https://labellucie.com/",
}
LINK_LABEL_REWRITES = {
    "https://permisdechasser.ofb.gouv.fr": "Consulter notre page « Passer son permis de chasser »",
}
TEMPORARY_PATTERNS = re.compile(
    r"\b(recrut|service civique|inscription|consultation publique|assemblee generale|"
    r"matinale|mobilisation|permanence|interdiction temporaire|risque incendie|"
    r"prolongation arrete|foyer|grippe aviaire|influenza aviaire)\b",
    re.IGNORECASE,
)


def slugify(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", unquote(value))
    ascii_value = normalized.encode("ascii", "ignore").decode("ascii").lower()
    return re.sub(r"[^a-z0-9]+", "-", ascii_value).strip("-")


def yaml_string(value: str) -> str:
    return json.dumps(re.sub(r"\s+", " ", value).strip(), ensure_ascii=False)


def get(session: requests.Session, url: str) -> requests.Response:
    response = session.get(url, headers=REQUEST_HEADERS, timeout=45)
    response.raise_for_status()
    response.encoding = "utf-8"
    return response


def parse_sitemap(session: requests.Session) -> list[str]:
    root = ElementTree.fromstring(get(session, SITEMAP_URL).content)
    namespace = {"s": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    return [node.text.strip() for node in root.findall("s:url/s:loc", namespace) if node.text]


def choose_category(article: BeautifulSoup) -> tuple[str, list[str]]:
    classes = article.get("class", [])
    categories = sorted({
        item.removeprefix("category-")
        for item in classes
        if item.startswith("category-") and not item.removeprefix("category-").isdigit()
    })
    if "flash-infos" in categories:
        return "Alertes", categories
    if "environnement" in categories:
        return "Environnement", categories
    if "chasse" in categories:
        return "Chasse", categories
    return "Fédération", categories


def archive_metadata(title: str, published: datetime, category: str) -> tuple[bool, datetime | None, str]:
    normalized_title = slugify(title).replace("-", " ")
    now = datetime.now(timezone.utc)
    expires_at = None
    reason = "active"

    season = re.search(r"20(\d{2})[-–]20(\d{2})", title)
    if season:
        expires_at = datetime(2000 + int(season.group(2)), 6, 30, tzinfo=timezone.utc)
        reason = "fin de saison mentionnée dans le titre"
    elif category == "Alertes":
        expires_at = published + timedelta(days=120)
        reason = "alerte valable 120 jours par défaut"
    elif TEMPORARY_PATTERNS.search(normalized_title):
        expires_at = published + timedelta(days=90)
        reason = "information temporaire ou événement daté"

    archived = published < datetime(2025, 1, 1, tzinfo=timezone.utc)
    if expires_at and expires_at < now:
        archived = True

    return archived, expires_at, reason if archived else "active"


def safe_filename(url: str, fallback: str) -> str:
    name = unquote(Path(urlparse(url).path).name)
    stem = slugify(Path(name).stem) or fallback
    suffix = Path(name).suffix.lower()
    return f"{stem}{suffix}"


def asset_directory_name(slug: str) -> str:
    if len(slug) <= 72:
        return slug
    digest = hashlib.sha1(slug.encode()).hexdigest()[:10]
    return f"{slug[:60].rstrip('-')}-{digest}"


def download_image(session: requests.Session, url: str, destination: Path) -> tuple[str, int, int]:
    response = get(session, url)
    image = Image.open(BytesIO(response.content))
    image = ImageOps.exif_transpose(image)
    if image.mode not in {"RGB", "RGBA"}:
        image = image.convert("RGB")
    image.thumbnail((1400, 1400), Image.Resampling.LANCZOS)
    destination.parent.mkdir(parents=True, exist_ok=True)
    if image.mode == "RGBA":
        background = Image.new("RGB", image.size, "white")
        background.paste(image, mask=image.getchannel("A"))
        image = background
    image.save(destination, "WEBP", quality=82, method=6)
    return destination.as_posix(), image.width, image.height


def download_document(session: requests.Session, url: str, destination: Path) -> None:
    response = get(session, url)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(response.content)


def absolute_internal_url(url: str) -> str:
    parsed = urlparse(url)
    if parsed.netloc == urlparse(OLD_ORIGIN).netloc:
        path = parsed.path.strip("/")
        suffix = "/" if path else ""
        anchor = f"#{parsed.fragment}" if parsed.fragment else ""
        return f"{SITE_BASE}{path}{suffix}{anchor}"
    return url


def clean_content(
    session: requests.Session,
    content: BeautifulSoup,
    slug: str,
    title: str,
    main_image_url: str | None,
) -> tuple[str, list[dict[str, str]], list[str]]:
    documents: list[dict[str, str]] = []
    failures: list[str] = []
    seen_documents: set[str] = set()
    seen_images: dict[str, str] = {}
    asset_directory = asset_directory_name(slug)

    for unwanted in content.select(
        "script, style, noscript, form, .sharedaddy, .shareaholic-canvas, "
        ".jp-relatedposts, .post-tags, .wp-block-spacer"
    ):
        unwanted.decompose()

    for heading in content.find_all("h1"):
        heading.name = "h2"

    for iframe in content.select("iframe[src]"):
        source = iframe.get("src", "")
        link = content.new_tag("a", href=source)
        link.string = f"Voir le contenu intégré lié à « {title} »"
        iframe.replace_with(link)

    for index, image in enumerate(content.select("img"), start=1):
        source = image.get("data-src") or image.get("data-lazy-src") or image.get("src")
        if not source:
            image.decompose()
            continue
        source = urljoin(OLD_ORIGIN, source)
        if main_image_url and source.split("?")[0] == main_image_url.split("?")[0]:
            image.decompose()
            continue
        try:
            if source in seen_images:
                local_url = seen_images[source]
            else:
                digest = hashlib.sha1(source.encode()).hexdigest()[:8]
                filename = f"{safe_filename(source, f'image-{index}').rsplit('.', 1)[0]}-{digest}.webp"
                destination = IMAGES_DIRECTORY / asset_directory / filename
                download_image(session, source, destination)
                local_url = f"/assets/articles/{asset_directory}/{filename}"
                seen_images[source] = local_url
            image["src"] = local_url
            image["alt"] = image.get("alt", "").strip() or f"Illustration de l’article « {title} »"
            for attribute in list(image.attrs):
                if attribute not in {"src", "alt"}:
                    del image[attribute]
        except Exception as error:  # Network and malformed legacy media are reported, not hidden.
            failures.append(f"image {source}: {error}")
            image.decompose()

    for index, anchor in enumerate(content.select("a[href]"), start=1):
        original_source = urljoin(OLD_ORIGIN, anchor.get("href", "").strip())
        source = original_source
        if not source:
            continue
        if original_source in LINK_LABEL_REWRITES:
            anchor.string = LINK_LABEL_REWRITES[original_source]
        source = LINK_REWRITES.get(source, source)
        source_path = urlparse(source).path
        extension = Path(source_path).suffix.lower() or DOWNLOAD_EXTENSION_OVERRIDES.get(source_path, "")
        if extension in DOCUMENT_EXTENSIONS or source_path in DOWNLOAD_EXTENSION_OVERRIDES:
            if source not in seen_documents:
                filename = safe_filename(source, f"document-{index}")
                if not Path(filename).suffix:
                    filename = f"{filename}{extension}"
                destination = DOCUMENTS_DIRECTORY / slug / filename
                try:
                    download_document(session, source, destination)
                    local_url = f"/assets/documents/actualites/{slug}/{filename}"
                    label = anchor.get_text(" ", strip=True) or Path(filename).stem.replace("-", " ")
                    documents.append({
                        "label": label,
                        "url": local_url,
                        "type": extension.removeprefix(".").upper(),
                    })
                    seen_documents.add(source)
                except Exception as error:
                    failures.append(f"document {source}: {error}")
                    anchor.unwrap()
                    continue
            else:
                local_url = next(item["url"] for item in documents if item["url"].endswith(safe_filename(source, "")))
            anchor["href"] = local_url
        else:
            anchor["href"] = absolute_internal_url(source)
        for attribute in list(anchor.attrs):
            if attribute != "href":
                del anchor[attribute]

    for element in content.find_all(True):
        for attribute in list(element.attrs):
            if attribute in {"class", "style", "id", "width", "height", "loading", "srcset", "sizes"}:
                del element[attribute]

    converter = html2text.HTML2Text()
    converter.body_width = 0
    converter.ignore_images = False
    converter.ignore_links = False
    converter.protect_links = True
    converter.unicode_snob = True
    markdown = converter.handle(str(content))
    markdown = re.sub(r"\n{3,}", "\n\n", markdown)
    markdown = re.sub(
        r"!\[([^\]]*)\]\((?:<)?(/assets/articles/[^)>]+)(?:>)?\)",
        lambda match: (
            f'<img src="{html.escape(match.group(2), quote=True)}" '
            f'alt="{html.escape(match.group(1), quote=True)}" loading="lazy" decoding="async">'
        ),
        markdown,
    )
    markdown = "\n".join(line.rstrip() for line in markdown.splitlines())
    markdown = re.sub(r"(?m)^[ \t]+$", "", markdown).strip()
    return markdown, documents, failures


def import_post(url: str) -> dict[str, object]:
    session = requests.Session()
    response = get(session, url)
    soup = BeautifulSoup(response.text, "html.parser")
    article = soup.select_one("article.single-postlike")
    content = article.select_one(".entry-content") if article else None
    if not article or not content:
        raise RuntimeError("contenu WordPress introuvable")

    slug = unquote(urlparse(response.url).path).strip("/")
    filename_slug = slugify(slug)
    heading = article.select_one("h1")
    og_title = soup.find("meta", property="og:title")
    title = (
        heading.get_text(" ", strip=True)
        if heading
        else (og_title.get("content", "") if og_title else soup.title.get_text(" ", strip=True))
    )
    title = re.sub(r"\s*[-–]\s*FDC\s*85\s*$", "", title, flags=re.IGNORECASE).strip()

    published_meta = soup.find("meta", property="article:published_time")
    if not published_meta or not published_meta.get("content"):
        raise RuntimeError("date de publication absente")
    published = datetime.fromisoformat(published_meta["content"].replace("Z", "+00:00"))

    category, wp_categories = choose_category(article)
    description_meta = soup.find("meta", property="og:description") or soup.find("meta", attrs={"name": "description"})
    summary = description_meta.get("content", "").strip() if description_meta else ""
    if not summary:
        summary = next(
            (paragraph.get_text(" ", strip=True) for paragraph in content.find_all("p") if paragraph.get_text(" ", strip=True)),
            title,
        )
    summary = re.sub(r"\s+", " ", summary).strip()
    if len(summary) > 240:
        summary = summary[:237].rsplit(" ", 1)[0] + "…"

    image_meta = soup.find("meta", property="og:image")
    first_content_image = content.select_one("img")
    image_source = (
        image_meta.get("content")
        if image_meta and image_meta.get("content")
        else (
            first_content_image.get("data-src") or first_content_image.get("src")
            if first_content_image
            else None
        )
    )
    main_image_source = urljoin(OLD_ORIGIN, image_source) if image_source else None
    image_data = None
    failures: list[str] = []
    if main_image_source:
        try:
            digest = hashlib.sha1(main_image_source.encode()).hexdigest()[:8]
            image_name = f"principale-{digest}.webp"
            asset_directory = asset_directory_name(filename_slug)
            local_path = IMAGES_DIRECTORY / asset_directory / image_name
            _, width, height = download_image(session, main_image_source, local_path)
            image_data = {
                "src": f"/assets/articles/{asset_directory}/{image_name}",
                "alt": title,
                "width": width,
                "height": height,
                "source": main_image_source,
            }
        except Exception as error:
            failures.append(f"image principale {main_image_source}: {error}")

    markdown, documents, content_failures = clean_content(
        session, content, filename_slug, title, main_image_source
    )
    failures.extend(content_failures)
    if not markdown:
        markdown = summary

    archived, expires_at, archive_reason = archive_metadata(title, published, category)
    frontmatter = [
        "---",
        f"title: {yaml_string(title)}",
        f"description: {yaml_string(summary)}",
        f"date: {published.date().isoformat()}",
        f"category: {yaml_string(category)}",
        f"summary: {yaml_string(summary)}",
    ]
    if image_data:
        frontmatter.extend([
            "image:",
            f"  src: {yaml_string(image_data['src'])}",
            f"  alt: {yaml_string(image_data['alt'])}",
            "  decorative: false",
            f"  width: {image_data['width']}",
            f"  height: {image_data['height']}",
        ])
    if documents:
        frontmatter.append("documents:")
        for document in documents:
            frontmatter.extend([
                f"  - label: {yaml_string(document['label'])}",
                f"    url: {yaml_string(document['url'])}",
                f"    type: {yaml_string(document['type'])}",
            ])
    else:
        frontmatter.append("documents: []")
    if expires_at:
        frontmatter.append(f"expiresAt: {expires_at.date().isoformat()}")
    frontmatter.append(f"archived: {'true' if archived else 'false'}")
    frontmatter.extend(["---", "", markdown, ""])

    output = ARTICLES_DIRECTORY / f"{filename_slug}.md"
    output.write_text("\n".join(frontmatter), encoding="utf-8", newline="\n")
    return {
        "source": url,
        "slug": slug,
        "file": output.relative_to(ROOT).as_posix(),
        "title": title,
        "published": published.isoformat(),
        "wpCategories": wp_categories,
        "category": category,
        "archived": archived,
        "expiresAt": expires_at.date().isoformat() if expires_at else None,
        "archiveReason": archive_reason,
        "mainImage": image_data,
        "documents": documents,
        "warnings": failures,
    }


def main() -> int:
    session = requests.Session()
    urls = parse_sitemap(session)
    article_urls = [url for url in urls if url.rstrip("/") != f"{OLD_ORIGIN}/actualites"]
    if len(urls) != 86 or len(article_urls) != 85:
        raise RuntimeError(f"Inventaire inattendu : {len(urls)} URL, {len(article_urls)} articles.")

    if ARTICLES_DIRECTORY.exists():
        shutil.rmtree(ARTICLES_DIRECTORY)
    if IMAGES_DIRECTORY.exists():
        shutil.rmtree(IMAGES_DIRECTORY)
    if DOCUMENTS_DIRECTORY.exists():
        shutil.rmtree(DOCUMENTS_DIRECTORY)
    ARTICLES_DIRECTORY.mkdir(parents=True)

    results: list[dict[str, object]] = []
    errors: list[dict[str, str]] = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as executor:
        futures = {executor.submit(import_post, url): url for url in article_urls}
        for completed, future in enumerate(concurrent.futures.as_completed(futures), start=1):
            url = futures[future]
            try:
                result = future.result()
                results.append(result)
                print(f"[{completed:02}/{len(article_urls)}] {Path(str(result['file'])).stem}")
            except Exception as error:
                errors.append({"source": url, "error": str(error)})
                print(f"[{completed:02}/{len(article_urls)}] ERREUR {url}: {error}", file=sys.stderr)

    results.sort(key=lambda item: str(item["published"]))
    report = {
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "source": SITEMAP_URL,
        "sitemapUrlCount": len(urls),
        "archiveUrl": f"{OLD_ORIGIN}/actualites/",
        "articleCount": len(article_urls),
        "importedCount": len(results),
        "errorCount": len(errors),
        "categoryMapping": {
            "actualites": "Fédération (catégorie générique ignorée si une catégorie précise existe)",
            "chasse": "Chasse",
            "environnement": "Environnement",
            "federation": "Fédération",
            "flash-infos": "Alertes",
            "recrutement": "Fédération",
            "non-classe": "Fédération",
        },
        "articles": results,
        "errors": errors,
    }
    REPORT_PATH.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n"
    )
    markdown_rows = "\n".join(
        f"| `/{item['slug']}/` | {item['title'].replace('|', '–')} | {item['category']} | "
        f"{'Archivé' if item['archived'] else 'Actif'} | "
        f"`/{Path(str(item['file'])).stem}/` |"
        for item in results
    )
    MARKDOWN_REPORT_PATH.write_text(
        f"""# Migration des actualités WordPress

Inventaire généré depuis [`post-sitemap.xml`]({SITEMAP_URL}) le {datetime.now(timezone.utc).date().isoformat()}.
Le sitemap contient **{len(urls)} URL** : l’archive `/actualites/` et **{len(article_urls)} articles**, tous importés.

## Catégories

| Catégorie WordPress | Catégorie cible |
| --- | --- |
| `actualites` | Fédération si aucune catégorie plus précise |
| `chasse` | Chasse |
| `environnement` | Environnement |
| `federation`, `recrutement`, `non-classe` | Fédération |
| `flash-infos` | Alertes |

En cas de catégories multiples, l’ordre de priorité est Alertes, Environnement, Chasse, Fédération.

## Archivage

Les articles antérieurs à 2025 sont archivés. Les alertes de plus de 120 jours, les recrutements,
inscriptions, événements et informations explicitement temporaires reçoivent également une date
d’expiration prudente. Les saisons mentionnées dans un titre expirent au 30 juin de leur seconde
année. Les textes restent accessibles à leur ancienne adresse ; l’archive avertit qu’ils doivent
être vérifiés avant réutilisation. Une information réglementaire n’est jamais supprimée.

## Matrice des 85 articles

| Ancienne URL | Titre importé | Catégorie | État | Destination |
| --- | --- | --- | --- | --- |
{markdown_rows}

## Exclusions techniques

- `/actualites/` est l’archive WordPress, pas un article : elle devient l’index paginé.
- Trois slugs comportant des emoji ont été normalisés en ASCII et disposent d’une redirection statique.
- Les ressources distantes inaccessibles ne sont pas inventées. Elles figurent dans le rapport JSON
  avec leur erreur ; leurs liens cassés ne sont pas exposés.
- Les images principales et images de contenu disponibles sont converties en WebP, limitées à
  1 400 px et servies localement. Les documents téléchargeables disponibles sont copiés localement.

Le rapport machine détaillé, incluant catégories WordPress, médias source, documents et avertissements,
est disponible dans [`migration-actualites.json`](migration-actualites.json).
""",
        encoding="utf-8",
        newline="\n",
    )
    print(f"{len(results)} articles importés, {len(errors)} erreurs.")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
