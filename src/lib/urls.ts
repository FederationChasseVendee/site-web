const externalPattern = /^https?:\/\//;

export function isExternalUrl(url: string): boolean {
  return externalPattern.test(url);
}

export function resolveUrl(url: string, base: string): string {
  if (/^(https?:|mailto:|tel:)/.test(url)) return url;
  return `${base}${url.replace(/^\/+/, "")}`.replace(/\/{2,}/g, "/");
}
