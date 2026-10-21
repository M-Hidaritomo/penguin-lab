import { existsSync, readFileSync, readdirSync, statSync } from 'node:fs';
import path from 'node:path';
import { describe, expect, it } from 'vitest';
import { forbiddenWords, toneWords } from './forbidden-words';

const root = process.cwd();
const dist = path.join(root, 'dist');
const rawBase = process.env.BASE_PATH || '/';
const base = rawBase.endsWith('/') ? rawBase : `${rawBase}/`;

function walk(dir: string): string[] {
  return readdirSync(dir).flatMap((name) => {
    const p = path.join(dir, name);
    return statSync(p).isDirectory() ? walk(p) : [p];
  });
}
const TEXT = /\.(html|css|js|json|svg|txt|xml|webmanifest|map)$/i;
const read = (p: string) => readFileSync(p, 'utf8');

describe('dist（npm run build の後に実行）', () => {
  it('index.html が存在する', () => {
    expect(existsSync(path.join(dist, 'index.html'))).toBe(true);
  });

  it('logo.png と favicon.svg が dist にある', () => {
    expect(existsSync(path.join(dist, 'logo.png'))).toBe(true);
    expect(existsSync(path.join(dist, 'favicon.svg'))).toBe(true);
  });

  const html = () => read(path.join(dist, 'index.html'));

  it('7セクションが仕様の順に並ぶ', () => {
    const h = html();
    const ids = ['site-header', 'hero', 'about', 'products', 'members', 'notes', 'site-footer'];
    const pos = ids.map((id) => h.indexOf(`id="${id}"`));
    expect(pos.every((p) => p >= 0)).toBe(true);
    expect([...pos].sort((a, b) => a - b)).toEqual(pos);
  });

  it('禁止語・口調が dist とソースの全テキストに含まれない', () => {
    const files = [
      ...walk(dist),
      ...walk(path.join(root, 'src')),
      ...walk(path.join(root, 'public')),
      ...walk(path.join(root, 'scripts')),
      path.join(root, 'README.md'),
    ].filter((f) => TEXT.test(f) || /\.(astro|ts|py|md|yml)$/.test(f));
    const hits: string[] = [];
    for (const f of files) {
      if (!existsSync(f)) continue;
      const text = read(f).toLowerCase();
      for (const w of forbiddenWords) if (text.includes(w.toLowerCase())) hits.push(`${f}: ${w.length}文字の禁止語`);
      for (const w of toneWords) if (text.includes(w)) hits.push(`${f}: ${w}`);
    }
    expect(hits).toEqual([]);
  });

  it('社名が「ぺんぎんラボ」で、旧表記「ペンギンラボ」が残っていない', () => {
    const files = [
      ...walk(dist).filter((f) => TEXT.test(f)),
      ...walk(path.join(root, 'src')),
      path.join(root, 'README.md'),
    ];
    for (const f of files) expect(read(f), f).not.toContain('ペンギンラボ');
    const h = html();
    expect(h).toMatch(/<title>ぺんぎんラボ/);
    expect(h).toMatch(/<img[^>]*alt="ぺんぎんラボ"/);
    expect(h).toContain('© ' + new Date().getFullYear() + ' ぺんぎんラボ');
    expect(h).toContain('10人のチーム');
  });

  it('title・description・OGP がある（og:image は絶対URL）', () => {
    const h = html();
    expect(h).toMatch(/<title>[^<]+<\/title>/);
    for (const key of ['name="description"', 'property="og:title"', 'property="og:description"']) {
      expect(h).toMatch(new RegExp(`<meta ${key} content="[^"]+"`));
    }
    expect(h).toMatch(/<meta property="og:image" content="https?:\/\/[^"]+\/ogp\.png"/);
    expect(h).toContain('name="twitter:card" content="summary_large_image"');
  });

  it('すべての img に空でない alt がある', () => {
    const imgs = html().match(/<img\b[^>]*>/g) ?? [];
    expect(imgs.length).toBeGreaterThanOrEqual(10);
    for (const tag of imgs) expect(tag).toMatch(/\balt="[^"]+"/);
  });

  it('/ で始まる src・href・CSS の url() が base で始まり、参照先が実在する', () => {
    const refs: string[] = [];
    const h = html();
    for (const m of h.matchAll(/\b(?:src|href)="(\/[^"]*)"/g)) refs.push(m[1]);
    for (const f of walk(dist).filter((f) => f.endsWith('.css'))) {
      for (const m of read(f).matchAll(/url\(\s*["']?(\/[^"')]+)/g)) refs.push(m[1]);
    }
    expect(refs.length).toBeGreaterThan(0);
    for (const ref of refs) {
      expect(ref.startsWith(base), ref).toBe(true);
      const rel = decodeURIComponent(ref.slice(base.length).split(/[?#]/)[0]);
      const target = path.join(dist, rel);
      const ok = rel === '' || rel.endsWith('/') ? existsSync(path.join(target, 'index.html')) : existsSync(target);
      expect(ok, ref).toBe(true);
    }
  });

  it('外部スクリプト・計測タグがない', () => {
    const h = html();
    expect(h).not.toMatch(/<script\b[^>]*\bsrc="https?:/i);
    expect(h).not.toMatch(/googletagmanager|google-analytics|gtag\(|plausible|clarity\.ms|hotjar/i);
    expect(h).not.toMatch(/<script\b/i); // クライアント側 JS を出さない方針
  });

  it('OGP 画像が 1200x630・300KB 以下', () => {
    const p = path.join(dist, 'ogp.png');
    expect(existsSync(p)).toBe(true);
    expect(statSync(p).size).toBeLessThanOrEqual(300 * 1024);
    const buf = readFileSync(p);
    expect(buf.readUInt32BE(16)).toBe(1200);
    expect(buf.readUInt32BE(20)).toBe(630);
  });
});
