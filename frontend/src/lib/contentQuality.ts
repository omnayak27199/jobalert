/** Detect scraped portal homepage text masquerading as notification content. */
export function isHomepageScrapeContent(content: string): boolean {
  const lower = content.toLowerCase();
  if (
    lower.includes("welcome to ") &&
    (lower.includes("javascript is disabled") || lower.includes("help desk"))
  ) {
    return true;
  }
  if (
    lower.includes("welcome to ") &&
    lower.includes("recruitment overview") &&
    content.length < 1200
  ) {
    return true;
  }
  if (lower.includes("skip to main content") && lower.includes("select your language")) {
    return true;
  }
  if (lower.includes("skip to main content") && lower.includes("download") && content.length < 4000) {
    return true;
  }
  return false;
}

/** Raw PDF bytes accidentally stored as text. */
export function isPdfBinaryContent(content: string): boolean {
  const sample = content.trimStart().slice(0, 16);
  return sample.startsWith("%PDF-") || sample.includes("\u0000");
}

export function shouldRenderFullContent(content: string | null | undefined): boolean {
  if (!content || content.trim().length < 50) return false;
  if (isHomepageScrapeContent(content)) return false;
  if (isPdfBinaryContent(content)) return false;
  return true;
}
