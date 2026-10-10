import { defineConfig } from 'astro/config';

export default defineConfig({
  site: process.env.SITE_ORIGIN || 'http://localhost:4321',
  base: process.env.BASE_PATH || '/',
  trailingSlash: 'ignore',
});
