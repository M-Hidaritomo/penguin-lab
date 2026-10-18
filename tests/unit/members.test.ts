import { existsSync, statSync } from 'node:fs';
import path from 'node:path';
import { describe, expect, it } from 'vitest';
import { members } from '../../src/data/members';
import { products } from '../../src/data/products';

describe('members', () => {
  it('10人が組織図順にそろう', () => {
    expect(members.map((m) => m.id)).toEqual([
      'konko', 'poko', 'hime', 'kerota', 'moko', 'mike', 'penta', 'piyo', 'holo', 'kumaji',
    ]);
    expect(members.map((m) => m.name)).toEqual([
      'コンコ', 'ポコ', 'ヒメ', 'ケロタ', 'モコ', 'ミケ', 'ペンタ', 'ピヨ', 'ホロ', 'クマジ',
    ]);
  });
  it('id・名前に重複がなく、全項目が空でない', () => {
    expect(new Set(members.map((m) => m.id)).size).toBe(10);
    expect(new Set(members.map((m) => m.name)).size).toBe(10);
    for (const m of members) {
      for (const v of Object.values(m)) expect(v.trim()).not.toBe('');
    }
  });
  it('画像が実在し 200KB 以下', () => {
    for (const m of members) {
      const p = path.join(process.cwd(), 'public', m.image);
      expect(existsSync(p), p).toBe(true);
      expect(statSync(p).size).toBeLessThanOrEqual(200 * 1024);
    }
  });
  it('口調・モデル名を含まない', () => {
    const text = JSON.stringify(members);
    for (const w of ['じゃ', 'ケロ！', 'メェ', 'にゃ', 'ぴよ！', 'ホー', 'Sonnet', 'Opus']) {
      expect(text).not.toContain(w);
    }
  });
});

describe('products', () => {
  it('現時点は空配列', () => {
    expect(products).toHaveLength(0);
  });
});
