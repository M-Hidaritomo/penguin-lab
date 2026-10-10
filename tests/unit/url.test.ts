import { describe, expect, it } from 'vitest';
import { isSafeHttpUrl, withBase } from '../../src/lib/url';

describe('withBase', () => {
  const bases: [string, string][] = [
    ['/', '/'],
    ['/repo', '/repo/'],
    ['/repo/', '/repo/'],
  ];
  for (const [base, prefix] of bases) {
    it(`base ${base}`, () => {
      expect(withBase('', base)).toBe(prefix);
      expect(withBase('members/a.webp', base)).toBe(`${prefix}members/a.webp`);
      expect(withBase('/members/a.webp', base)).toBe(`${prefix}members/a.webp`);
    });
  }
});

describe('isSafeHttpUrl', () => {
  it('https/http は true', () => {
    expect(isSafeHttpUrl('https://note.com/x')).toBe(true);
    expect(isSafeHttpUrl('http://example.com')).toBe(true);
  });
  it('それ以外は false', () => {
    expect(isSafeHttpUrl('javascript:alert(1)')).toBe(false);
    expect(isSafeHttpUrl('')).toBe(false);
    expect(isSafeHttpUrl('/relative')).toBe(false);
  });
});
