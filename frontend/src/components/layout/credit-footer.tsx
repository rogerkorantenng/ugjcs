/** The one-line builder credit closing every signed-in workspace. The public pages carry
 * the same line inside `SiteFooter`; the dashboards have no full footer, so this small
 * strip is theirs. */
export function CreditFooter() {
  return (
    <footer className="border-t border-rule">
      <p className="mx-auto max-w-4xl px-4 py-4 text-center text-xs text-ink/45">
        Built by Roger Koranteng Obeng · 22424140 · Advanced Software Engineering final project
      </p>
    </footer>
  );
}
