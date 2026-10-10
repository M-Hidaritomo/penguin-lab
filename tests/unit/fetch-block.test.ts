import { describe, expect, it } from 'vitest';

describe('fetch 遮断', () => {
  it('setup 後は fetch が例外になる', async () => {
    await expect(async () => fetch('https://example.com')).rejects.toThrow(/ネットワーク遮断/);
  });
});
