import { existsSync } from 'node:fs';
import { mkdir, readFile, writeFile } from 'node:fs/promises';
import path from 'node:path';
import { XMLParser, XMLValidator } from 'fast-xml-parser';
import { isSafeHttpUrl } from './url';

export type NoteArticle = { title: string; url: string; publishedAt: string };
export type NoteCache = { fetchedAt: string | null; articles: NoteArticle[] };

export type NoteFeedResult =
  | { state: 'unconfigured' }
  | { state: 'fresh'; articles: NoteArticle[] }
  | { state: 'cached'; articles: NoteArticle[]; reason: string }
  | { state: 'link-only'; reason: string };

export interface NoteCacheStore {
  read(): Promise<NoteCache | null>;
  write(cache: NoteCache): Promise<void>;
}

export class NoteFeedError extends Error {
  constructor(
    public readonly kind: 'network' | 'timeout' | 'http' | 'parse',
    message: string,
  ) {
    super(message);
    this.name = 'NoteFeedError';
  }
}

const MAX_BYTES = 2 * 1024 * 1024;

function isHttps(value: string | undefined): value is string {
  return !!value && isSafeHttpUrl(value) && value.startsWith('https://');
}

export function resolveRssUrl(noteUrl: string, noteRssUrl?: string): string | null {
  if (isHttps(noteRssUrl)) return noteRssUrl;
  if (isHttps(noteUrl)) return `${noteUrl.replace(/\/+$/, '')}/rss`;
  return null;
}

function isAbort(e: unknown): boolean {
  const name = (e as { name?: string } | null)?.name;
  return name === 'TimeoutError' || name === 'AbortError';
}

function shortMessage(e: unknown): string {
  return String((e as { message?: unknown } | null)?.message ?? e).slice(0, 100);
}

export async function fetchRss(
  url: string,
  opts: { fetchImpl: typeof fetch; timeoutMs: number },
): Promise<string> {
  const signal = AbortSignal.timeout(opts.timeoutMs);
  let res: Response;
  try {
    res = await opts.fetchImpl(url, { signal });
  } catch (e) {
    if (isAbort(e)) throw new NoteFeedError('timeout', `${opts.timeoutMs}ms 以内に応答がありません`);
    throw new NoteFeedError('network', shortMessage(e));
  }
  if (!res.ok) throw new NoteFeedError('http', `HTTP ${res.status}`);
  let text: string;
  try {
    text = await res.text();
  } catch (e) {
    if (isAbort(e)) throw new NoteFeedError('timeout', `${opts.timeoutMs}ms 以内に本文を受け取れません`);
    throw new NoteFeedError('network', shortMessage(e));
  }
  if (Buffer.byteLength(text, 'utf8') > MAX_BYTES) {
    throw new NoteFeedError('http', '応答が大きすぎます（2MB超）');
  }
  return text;
}

function textOf(v: unknown): string {
  if (typeof v === 'string') return v.trim();
  if (typeof v === 'number') return String(v);
  if (v && typeof v === 'object' && '#text' in v) return textOf((v as Record<string, unknown>)['#text']);
  return '';
}

export function parseNoteRss(xml: string, limit = 5): NoteArticle[] {
  if (XMLValidator.validate(xml) !== true) {
    throw new NoteFeedError('parse', 'XMLとして読めません');
  }
  let doc: any;
  try {
    doc = new XMLParser({
      ignoreAttributes: true,
      processEntities: true,
      isArray: (name) => name === 'item',
    }).parse(xml);
  } catch {
    throw new NoteFeedError('parse', 'XMLの解析に失敗しました');
  }
  const channel = doc?.rss?.channel;
  if (!channel || typeof channel !== 'object') {
    throw new NoteFeedError('parse', 'rss/channel がありません');
  }
  const items: unknown[] = Array.isArray(channel.item) ? channel.item : [];
  if (items.length === 0) return [];

  const articles: NoteArticle[] = [];
  for (const item of items as Record<string, unknown>[]) {
    const title = textOf(item?.title);
    const url = textOf(item?.link);
    const date = new Date(textOf(item?.pubDate));
    if (!title || !isSafeHttpUrl(url) || Number.isNaN(date.getTime())) continue;
    articles.push({ title, url, publishedAt: date.toISOString() });
  }
  if (articles.length === 0) {
    throw new NoteFeedError('parse', '記事を取り出せません');
  }
  articles.sort((a, b) => b.publishedAt.localeCompare(a.publishedAt));
  return articles.slice(0, limit);
}

export type LoadNoteFeedOptions = {
  noteUrl: string;
  noteRssUrl?: string;
  cache: NoteCacheStore;
  fetchImpl?: typeof fetch;
  timeoutMs?: number;
  limit?: number;
  offline?: boolean;
  log?: (line: string) => void;
  now?: () => Date;
};

/** 例外を投げない（ビルドを止めない）。 */
export async function loadNoteFeed(opts: LoadNoteFeedOptions): Promise<NoteFeedResult> {
  const limit = opts.limit ?? 5;
  const log = opts.log ?? ((line: string) => console.warn(line));
  const rssUrl = resolveRssUrl(opts.noteUrl, opts.noteRssUrl);
  if (!rssUrl) return { state: 'unconfigured' };

  const fallback = async (kind: string, detail: string): Promise<NoteFeedResult> => {
    const reason = `${kind}: ${detail}`;
    log(`[note-feed] ${reason}。前回のキャッシュを使います`);
    let cached: NoteCache | null = null;
    try {
      cached = await opts.cache.read();
    } catch {
      cached = null;
    }
    if (cached && cached.articles.length > 0) {
      return { state: 'cached', articles: cached.articles.slice(0, limit), reason };
    }
    return { state: 'link-only', reason };
  };

  if (opts.offline) return fallback('offline', '取得せずキャッシュだけ使います');

  let articles: NoteArticle[];
  try {
    const xml = await fetchRss(rssUrl, {
      fetchImpl: opts.fetchImpl ?? globalThis.fetch,
      timeoutMs: opts.timeoutMs ?? 10_000,
    });
    articles = parseNoteRss(xml, limit);
  } catch (e) {
    if (e instanceof NoteFeedError) return fallback(e.kind, e.message.slice(0, 100));
    return fallback('network', shortMessage(e));
  }
  try {
    await opts.cache.write({ fetchedAt: (opts.now ?? (() => new Date()))().toISOString(), articles });
  } catch {
    // キャッシュの保存失敗は表示に影響させない
  }
  return { state: 'fresh', articles };
}

function isValidCache(v: any): v is NoteCache {
  return (
    !!v &&
    typeof v === 'object' &&
    (v.fetchedAt === null || typeof v.fetchedAt === 'string') &&
    Array.isArray(v.articles) &&
    v.articles.every(
      (a: any) =>
        a && typeof a.title === 'string' && typeof a.url === 'string' && typeof a.publishedAt === 'string',
    )
  );
}

export function createFileCache(file: string): NoteCacheStore {
  return {
    async read() {
      try {
        const parsed = JSON.parse(await readFile(file, 'utf8'));
        return isValidCache(parsed) ? parsed : null;
      } catch {
        return null;
      }
    },
    async write(cache) {
      try {
        const next = `${JSON.stringify(cache, null, 2)}\n`;
        if (existsSync(file) && (await readFile(file, 'utf8')) === next) return;
        await mkdir(path.dirname(file), { recursive: true });
        await writeFile(file, next, 'utf8');
      } catch (e) {
        console.warn(`[note-feed] キャッシュを書けませんでした: ${shortMessage(e)}`);
      }
    },
  };
}
