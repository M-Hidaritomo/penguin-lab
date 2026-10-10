import { mkdtemp, readFile, writeFile } from 'node:fs/promises';
import { readFileSync } from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { describe, expect, it, vi } from 'vitest';
import {
  NoteFeedError,
  createFileCache,
  loadNoteFeed,
  parseNoteRss,
  resolveRssUrl,
  type NoteArticle,
  type NoteCache,
  type NoteCacheStore,
} from '../../src/lib/note-feed';

const fx = (name: string) => readFileSync(path.join(process.cwd(), 'tests/fixtures', name), 'utf8');

const okFetch = (body: string) =>
  vi.fn(async () => new Response(body, { status: 200 })) as unknown as typeof fetch;

const cachedArticles: NoteArticle[] = [
  { title: '前回の記事', url: 'https://note.com/test/n/old', publishedAt: '2026-09-30T00:00:00.000Z' },
];

function memoryCache(initial: NoteCache | null) {
  const write = vi.fn(async (_c: NoteCache) => {});
  const store: NoteCacheStore = { read: async () => initial, write };
  return { store, write };
}

const base = { noteUrl: 'https://note.com/test', log: () => {} };

describe('resolveRssUrl', () => {
  it('設定から決める', () => {
    expect(resolveRssUrl('https://note.com/a/')).toBe('https://note.com/a/rss');
    expect(resolveRssUrl('https://note.com/a', 'https://example.com/feed')).toBe('https://example.com/feed');
    expect(resolveRssUrl('')).toBeNull();
    expect(resolveRssUrl('http://note.com/a')).toBeNull();
    expect(resolveRssUrl('javascript:alert(1)')).toBeNull();
  });
});

describe('parseNoteRss', () => {
  it('7件順不同 → 新しい順5件', () => {
    const a = parseNoteRss(fx('rss-valid.xml'));
    expect(a.map((x) => x.title)).toEqual(['記事G', '記事F', '記事E', '記事D', '記事C']);
    expect(a[0]).toEqual({
      title: '記事G',
      url: 'https://note.com/test/n/記事G',
      publishedAt: '2026-10-07T03:00:00.000Z',
    });
  });
  it('2件・0件は正常', () => {
    expect(parseNoteRss(fx('rss-few.xml'))).toHaveLength(2);
    expect(parseNoteRss(fx('rss-empty-channel.xml'))).toEqual([]);
  });
  it('壊れたRSS・使える記事なしは parse エラー', () => {
    for (const f of ['rss-broken.xml', 'rss-no-usable-items.xml']) {
      try {
        parseNoteRss(fx(f));
        expect.unreachable();
      } catch (e) {
        expect(e).toBeInstanceOf(NoteFeedError);
        expect((e as NoteFeedError).kind).toBe('parse');
      }
    }
  });
  it('危険なリンクは捨て、本文は含まれない', () => {
    const a = parseNoteRss(fx('rss-mixed.xml'));
    expect(a).toHaveLength(1);
    expect(JSON.stringify(a)).not.toContain('javascript:');
    expect(JSON.stringify(a)).not.toContain('本文');
  });
});

describe('loadNoteFeed', () => {
  it('URL未設定 → unconfigured。fetch もキャッシュ書き込みもしない', async () => {
    const { store, write } = memoryCache(null);
    const fetchImpl = vi.fn() as unknown as typeof fetch;
    const r = await loadNoteFeed({ ...base, noteUrl: '', cache: store, fetchImpl });
    expect(r).toEqual({ state: 'unconfigured' });
    expect(fetchImpl).not.toHaveBeenCalled();
    expect(write).not.toHaveBeenCalled();
  });

  it('成功 → fresh、キャッシュに書く', async () => {
    const { store, write } = memoryCache(null);
    const r = await loadNoteFeed({
      ...base,
      cache: store,
      fetchImpl: okFetch(fx('rss-valid.xml')),
      now: () => new Date('2026-10-11T00:00:00Z'),
    });
    expect(r.state).toBe('fresh');
    if (r.state !== 'fresh') return;
    expect(r.articles).toHaveLength(5);
    expect(write).toHaveBeenCalledWith({ fetchedAt: '2026-10-11T00:00:00.000Z', articles: r.articles });
  });

  const failures: [string, typeof fetch][] = [
    ['通信エラー', (async () => { throw new TypeError('fetch failed'); }) as unknown as typeof fetch],
    ['HTTP 500', (async () => new Response('x', { status: 500 })) as unknown as typeof fetch],
    [
      'タイムアウト',
      ((_u: unknown, init?: RequestInit) =>
        new Promise((_res, rej) => {
          init?.signal?.addEventListener('abort', () => rej(init.signal!.reason));
        })) as unknown as typeof fetch,
    ],
  ];
  for (const [name, fetchImpl] of failures) {
    it(`${name} → cached、ログ1行、例外なし`, async () => {
      const { store, write } = memoryCache({ fetchedAt: 'x', articles: cachedArticles });
      const log = vi.fn();
      const r = await loadNoteFeed({ ...base, cache: store, fetchImpl, timeoutMs: 50, log });
      expect(r.state).toBe('cached');
      if (r.state === 'cached') expect(r.articles).toEqual(cachedArticles);
      expect(log).toHaveBeenCalledTimes(1);
      expect(write).not.toHaveBeenCalled();
    });
  }

  it('タイムアウトの理由は timeout', async () => {
    const { store } = memoryCache(null);
    const r = await loadNoteFeed({
      ...base,
      cache: store,
      timeoutMs: 30,
      fetchImpl: ((_u: unknown, init?: RequestInit) =>
        new Promise((_res, rej) => {
          init?.signal?.addEventListener('abort', () => rej(init.signal!.reason));
        })) as unknown as typeof fetch,
    });
    expect(r.state).toBe('link-only');
    if (r.state === 'link-only') expect(r.reason).toMatch(/^timeout/);
  });

  it('壊れたRSS → cached、キャッシュを上書きしない', async () => {
    const { store, write } = memoryCache({ fetchedAt: 'x', articles: cachedArticles });
    for (const f of ['rss-broken.xml', 'rss-no-usable-items.xml']) {
      const r = await loadNoteFeed({ ...base, cache: store, fetchImpl: okFetch(fx(f)) });
      expect(r.state).toBe('cached');
    }
    expect(write).not.toHaveBeenCalled();
  });

  it('失敗＋キャッシュ無し/空 → link-only', async () => {
    const failing = (async () => new Response('x', { status: 503 })) as unknown as typeof fetch;
    for (const initial of [null, { fetchedAt: null, articles: [] }]) {
      const { store } = memoryCache(initial);
      const r = await loadNoteFeed({ ...base, cache: store, fetchImpl: failing });
      expect(r.state).toBe('link-only');
    }
  });

  it('offline は取得せずキャッシュを使う', async () => {
    const { store, write } = memoryCache({ fetchedAt: 'x', articles: cachedArticles });
    const fetchImpl = vi.fn() as unknown as typeof fetch;
    const r = await loadNoteFeed({ ...base, cache: store, fetchImpl, offline: true });
    expect(r.state).toBe('cached');
    expect(fetchImpl).not.toHaveBeenCalled();
    expect(write).not.toHaveBeenCalled();
  });
});

describe('createFileCache', () => {
  it('読み書き・壊れたJSON・同内容は書かない', async () => {
    const dir = await mkdtemp(path.join(os.tmpdir(), 'note-cache-'));
    const file = path.join(dir, 'sub', 'cache.json');
    const store = createFileCache(file);
    expect(await store.read()).toBeNull();

    const data: NoteCache = { fetchedAt: '2026-10-11T00:00:00.000Z', articles: cachedArticles };
    await store.write(data);
    expect(await store.read()).toEqual(data);
    expect(JSON.parse(await readFile(file, 'utf8'))).toEqual(data);

    const { statSync, utimesSync } = await import('node:fs');
    utimesSync(file, new Date(2000, 0, 1), new Date(2000, 0, 1));
    const before = statSync(file).mtimeMs;
    await store.write(data);
    expect(statSync(file).mtimeMs).toBe(before);

    await writeFile(file, '{ broken', 'utf8');
    expect(await store.read()).toBeNull();
    await writeFile(file, '{"fetchedAt":null,"articles":[{"title":1}]}', 'utf8');
    expect(await store.read()).toBeNull();
  });
});
