const JST_OFFSET_MS = 9 * 60 * 60 * 1000;

/** ISO 8601 を JST の「2026年10月10日」形式にする。Intl・実行環境のタイムゾーンには頼らない。 */
export function formatJaDate(iso: string): string {
  const t = new Date(iso).getTime();
  if (Number.isNaN(t)) return '';
  const d = new Date(t + JST_OFFSET_MS);
  return `${d.getUTCFullYear()}年${d.getUTCMonth() + 1}月${d.getUTCDate()}日`;
}
