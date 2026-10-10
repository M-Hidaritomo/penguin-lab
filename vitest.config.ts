import { getViteConfig } from 'astro/config';

export default getViteConfig({
  test: {
    include: ['tests/unit/**/*.test.ts', 'tests/components/**/*.test.ts'],
    setupFiles: ['tests/setup.ts'],
  },
} as never);
