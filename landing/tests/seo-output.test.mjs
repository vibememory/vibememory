import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';

const read = (path, encoding = 'utf8') => readFileSync(new URL(`../${path}`, import.meta.url), encoding);

test('public landing emits complete search and social metadata', () => {
  const html = read('dist/index.html');
  assert.match(html, /<title>Vibe Memory — AI 에이전트를 위한 공유 기억 레이어<\/title>/);
  assert.match(html, /<meta name="description" content="[^"]+"/);
  assert.match(html, /<link rel="canonical" href="https:\/\/vibememory\.io"/);
  assert.match(html, /<meta property="og:type" content="website"/);
  assert.match(html, /<meta property="og:image" content="https:\/\/vibememory\.io\/assets\/og-vibe-memory-v2\.png"/);
  assert.match(html, /<meta name="twitter:card" content="summary_large_image"/);
  assert.match(html, /<link rel="manifest" href="\/site\.webmanifest"/);
  assert.match(html, /type="application\/ld\+json"/);
  assert.match(html, /"@type":"SoftwareApplication"/);
  assert.match(html, /"@type":"WebSite"/);
  assert.match(html, /"codeRepository":"https:\/\/github\.com\/vibememory\/vibememory"/);
  assert.doesNotMatch(html, /hreflang=/);
  assert.doesNotMatch(html, /href="\/guide\.html/);
});

test('guide has its own canonical, metadata, and article schema', () => {
  const html = read('dist/guide.html');
  assert.match(html, /<title>AI 에이전트 연결 가이드 \| Vibe Memory<\/title>/);
  assert.match(html, /<link rel="canonical" href="https:\/\/vibememory\.io\/guide"/);
  assert.match(html, /<meta property="og:type" content="article"/);
  assert.match(html, /"@type":"TechArticle"/);
  assert.match(html, /"dateModified":"2026-10-30"/);
});

test('private product routes are explicitly excluded from indexing', () => {
  for (const page of ['admin', 'capture', 'connect', 'console', 'login']) {
    const html = read(`dist/${page}.html`);
    assert.match(html, /<meta name="robots" content="noindex, nofollow, noarchive"/);
    assert.doesNotMatch(html, /<link rel="canonical"/);
    assert.doesNotMatch(html, /property="og:/);
  }
});

test('crawl discovery files expose only canonical public pages', () => {
  const robots = read('dist/robots.txt');
  const sitemap = read('dist/sitemap.xml');
  const llms = read('dist/llms.txt');
  const manifest = JSON.parse(read('dist/site.webmanifest'));

  assert.match(robots, /Disallow: \/v1\//);
  assert.match(robots, /Sitemap: https:\/\/vibememory\.io\/sitemap\.xml/);
  assert.match(sitemap, /<loc>https:\/\/vibememory\.io\/<\/loc>/);
  assert.match(sitemap, /<loc>https:\/\/vibememory\.io\/guide<\/loc>/);
  assert.doesNotMatch(sitemap, /\/console/);
  assert.match(llms, /Vibe Memory does not call an LLM/);
  assert.equal(manifest.name, 'Vibe Memory');
  assert.equal(manifest.start_url, '/');
});

test('social image is a valid 1200 by 630 PNG', () => {
  const image = read('dist/assets/og-vibe-memory-v2.png', null);
  assert.equal(image.subarray(1, 4).toString('ascii'), 'PNG');
  assert.equal(image.readUInt32BE(16), 1200);
  assert.equal(image.readUInt32BE(20), 630);
});

test('Cloudflare runs canonical redirects before static asset routing', () => {
  const config = JSON.parse(read('wrangler.jsonc'));
  const worker = read('src/worker.js');
  assert.equal(config.assets.run_worker_first, true);
  assert.match(worker, /url\.hostname === 'www\.vibememory\.io'/);
  assert.match(worker, /\['\/guide\.html', '\/guide'\]/);
  assert.match(worker, /\['\/index\.html', '\/'\]/);
});
