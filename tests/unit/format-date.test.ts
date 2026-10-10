import { describe, expect, it } from 'vitest';
import { formatJaDate } from '../../src/lib/format-date';

describe('formatJaDate', () => {
  it('JST に直して日本語形式にする', () => {
    expect(formatJaDate('2026-10-09T15:30:00Z')).toBe('2026年10月10日');
    expect(formatJaDate('2026-10-09T14:59:59Z')).toBe('2026年10月9日');
  });
  it('不正な値は空文字', () => {
    expect(formatJaDate('xxx')).toBe('');
  });
});
