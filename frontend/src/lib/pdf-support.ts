/**
 * Whether this browser is likely to render a PDF inline inside an `<iframe>`. Mobile
 * browsers — iOS Safari and the in-app webviews built on it especially — very often refuse
 * to, silently showing an empty grey rectangle rather than an error the code can catch.
 * There is no DOM event for "the PDF plugin failed to render"; this is a feature test, not
 * a certainty, so `<PdfViewer>` still backs it up with a load timer.
 */
export function supportsInlinePdf(nav: Pick<Navigator, "userAgent"> & { pdfViewerEnabled?: boolean } = navigator): boolean {
  if (typeof nav.pdfViewerEnabled === "boolean") {
    // Chrome, Edge and Firefox expose this directly — the definitive answer when present.
    return nav.pdfViewerEnabled;
  }
  // No API on iOS Safari/WebKit-based browsers. Treat any iOS-family user agent (including
  // iPadOS, which since iOS 13 reports as "Macintosh" but is touch-only) as unsupported.
  const ua = nav.userAgent ?? "";
  const isIOS = /iPad|iPhone|iPod/.test(ua) || (/Macintosh/.test(ua) && "maxTouchPoints" in navigator && navigator.maxTouchPoints > 1);
  return !isIOS;
}
