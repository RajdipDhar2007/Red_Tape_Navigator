/** Date shown in the interface language, with the month spelled out so 11/12 can never be read two ways. */
export function formatDate(iso: string, locale: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "";
  try {
    return d.toLocaleDateString(`${locale}-IN`, { day: "numeric", month: "short", year: "numeric" });
  } catch {
    return d.toLocaleDateString("en-IN", { day: "numeric", month: "short", year: "numeric" });
  }
}
