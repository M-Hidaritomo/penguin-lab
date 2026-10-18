import { describe, expect, it } from 'vitest';
import Footer from '../../src/components/Footer.astro';
import Members from '../../src/components/Members.astro';
import NoteSection from '../../src/components/NoteSection.astro';
import Products from '../../src/components/Products.astro';
import { members } from '../../src/data/members';
import type { NoteFeedResult } from '../../src/lib/note-feed';
import { render } from './render';

const articles = (n: number) =>
  Array.from({ length: n }, (_, i) => ({
    title: `記事${i + 1}`,
    url: `https://note.com/test/n/${i + 1}`,
    publishedAt: `2026-10-0${9 - i}T15:30:00.000Z`,
  }));
const count = (html: string, s: string) => html.split(s).length - 1;

describe('Products', () => {
  const WIP = '1本目のサービスを開発中です。公開したらここでお知らせします';
  it('空 → 開発中カード1枚', async () => {
    const html = await render(Products, { products: [] });
    expect(count(html, WIP)).toBe(1);
    expect(html).toContain('products-wip');
  });
  it('1件以上 → サービスカードのみ', async () => {
    const html = await render(Products, {
      products: [{ name: 'テストサービス', summary: '面倒を解決します。', url: 'https://example.com/', status: '公開中' }],
    });
    expect(html).not.toContain(WIP);
    expect(html).toContain('テストサービス');
    expect(html).toContain('公開中');
    expect(html).toContain('href="https://example.com/"');
    expect(html).toContain('rel="noopener noreferrer"');
  });
  it('不正な url はリンクを出さない', async () => {
    const html = await render(Products, {
      products: [{ name: 'X', summary: 's', url: 'javascript:alert(1)' }],
    });
    expect(html).not.toContain('javascript:');
    expect(html).not.toContain('見る →');
  });
});

describe('Members', () => {
  it('10枚・組織図順・alt あり', async () => {
    const html = await render(Members, { members });
    expect(count(html, '<li class="member-card"')).toBe(10);
    const pos = members.map((m) => html.indexOf(`alt="${m.name}（${m.motif}）のイラスト"`));
    expect(pos.every((p) => p >= 0)).toBe(true);
    expect([...pos].sort((x, y) => x - y)).toEqual(pos);
    for (const m of members) expect(html).toContain(`alt="${m.name}（${m.motif}）のイラスト"`);
    expect(html).toContain('ぺんぎんラボの社員は、代表と一緒に働くAIのキャラクターです。');
  });
});

describe('NoteSection', () => {
  const noteUrl = 'https://note.com/test';
  const run = (feed: NoteFeedResult, url = noteUrl) => render(NoteSection, { feed, noteUrl: url });

  it('5件', async () => {
    const html = await run({ state: 'fresh', articles: articles(5) });
    expect(count(html, 'class="article"')).toBe(5);
    expect(html).toContain('2026年10月10日');
    expect(html).toContain('noteで読む →');
    expect(count(html, 'target="_blank"')).toBe(6);
    expect(count(html, 'rel="noopener noreferrer"')).toBe(6);
  });
  it('準備中（ボタン・リンクなし）', async () => {
    const html = await run({ state: 'unconfigured' }, '');
    expect(html).toContain('準備中です。noteでの発信を始めたら、ここに新着を表示します。');
    expect(html).not.toContain('<a ');
  });
  it('noteで読むのみ', async () => {
    for (const feed of [{ state: 'link-only', reason: 'x' }, { state: 'fresh', articles: [] }] as NoteFeedResult[]) {
      const html = await run(feed);
      expect(html).toContain('noteで読む →');
      expect(html).not.toContain('class="article"');
    }
  });
  it('1〜4件・キャッシュ表示', async () => {
    const html = await run({ state: 'cached', articles: articles(2), reason: 'x' });
    expect(count(html, 'class="article"')).toBe(2);
    expect(html).toContain('noteで読む →');
  });
});

describe('Footer', () => {
  it('両方空でも「準備中」', async () => {
    const html = await render(Footer, { xUrl: '', noteUrl: '', year: 2026 });
    expect(html).toContain('X（準備中）');
    expect(html).not.toContain('sns__icon');
    expect(html).toContain('note（準備中）');
    expect(html).not.toContain('<a ');
    expect(html).toContain('© 2026 ぺんぎんラボ');
  });
  it('設定時はリンク', async () => {
    const html = await render(Footer, { xUrl: 'https://x.com/a', noteUrl: 'https://note.com/a' });
    expect(html).toContain('href="https://x.com/a"');
    expect(html).not.toContain('sns__icon');
    expect(html).toContain('href="https://note.com/a"');
    expect(html).not.toContain('準備中');
    expect(html).toContain('rel="noopener noreferrer"');
  });
});
