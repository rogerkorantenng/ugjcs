export function formatAuthors(names: string[]): string {
  if (names.length === 0) return "Unattributed";
  if (names.length <= 2) return names.join(" & ");
  return `${names[0]} et al.`;
}
