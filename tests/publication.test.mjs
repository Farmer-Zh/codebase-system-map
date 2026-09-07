import assert from 'node:assert/strict';
import { existsSync, readFileSync } from 'node:fs';
import { dirname, extname, resolve } from 'node:path';
import test from 'node:test';
import { fileURLToPath } from 'node:url';

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const pageFiles = [
  resolve(root, 'docs/index.html'),
  resolve(root, 'docs/zh/index.html'),
];
const showcaseFiles = [
  resolve(root, 'docs/showcases/full-stack-fastapi-template.html'),
  resolve(root, 'docs/showcases/huey.html'),
  resolve(root, 'docs/showcases/openai-agents-python.html'),
];

function localReferences(html) {
  return [...html.matchAll(/\b(?:href|src)=["']([^"']+)["']/gi)]
    .map((match) => match[1])
    .filter((reference) => !/^(?:[a-z]+:|#|\/\/)/i.test(reference));
}

test('GitHub Pages local assets and links resolve', () => {
  for (const file of pageFiles) {
    const html = readFileSync(file, 'utf8');
    for (const reference of localReferences(html)) {
      const pathOnly = decodeURIComponent(reference.split(/[?#]/, 1)[0]);
      assert.ok(existsSync(resolve(dirname(file), pathOnly)), `${file}: missing ${reference}`);
    }
  }
});

test('both landing pages disclose bundled open-source components', () => {
  for (const file of pageFiles) {
    const html = readFileSync(file, 'utf8');
    for (const component of ['Codebase Memory', 'Viz.js 3.29.0', 'Graphviz', 'Expat']) {
      assert.match(html, new RegExp(component.replace('.', '\\.')));
    }
    assert.match(html, /canonical/);
    assert.match(html, /application\/ld\+json/);
  }
});

test('landing-page reading path is explicit and never auto-plays', () => {
  for (const file of pageFiles) {
    const html = readFileSync(file, 'utf8');
    assert.match(html, /data-reading-path/);
    assert.equal([...html.matchAll(/data-reading-step=/g)].length, 3);
    assert.equal([...html.matchAll(/data-reading-panel=/g)].length, 3);
    assert.doesNotMatch(html, /workflow\.gif/i);
  }

  const script = readFileSync(resolve(root, 'docs/assets/site.js'), 'utf8');
  assert.match(script, /data-reading-step/);
  assert.doesNotMatch(script, /setInterval\s*\(/);
});

test('public links use the current GitHub account', () => {
  const files = [
    ...pageFiles,
    resolve(root, 'README.md'),
    resolve(root, 'README.zh-CN.md'),
    resolve(root, 'docs/robots.txt'),
    resolve(root, 'docs/sitemap.xml'),
    resolve(root, 'codebase-system-map/schemas/system-map.schema.json'),
  ];
  for (const file of files) {
    const text = readFileSync(file, 'utf8');
    assert.doesNotMatch(text, /Farmer-Zh|farmer-zh\.github\.io/i);
    assert.match(text, /farmerzh47/i);
  }
});

test('published showcases remain standalone HTML documents', () => {
  for (const file of showcaseFiles) {
    const html = readFileSync(file, 'utf8');
    assert.equal(extname(file), '.html');
    assert.match(html, /id="system-map-data"/);
    assert.match(html, /id="diagram-data"/);
    assert.doesNotMatch(html, /<script\s+[^>]*src=/i);
    assert.doesNotMatch(html, /<link\s+[^>]*href=/i);
  }
});

test('README files and third-party notices match shipped licenses', () => {
  const files = [
    'codebase-system-map/assets/licenses/VIZ_JS_LICENSE.txt',
    'codebase-system-map/assets/licenses/GRAPHVIZ_LICENSE.txt',
    'codebase-system-map/assets/licenses/EXPAT_LICENSE.txt',
    'THIRD_PARTY_NOTICES.md',
  ];
  files.forEach((file) => assert.ok(existsSync(resolve(root, file)), `missing ${file}`));

  for (const readme of ['README.md', 'README.zh-CN.md']) {
    const text = readFileSync(resolve(root, readme), 'utf8');
    ['Codebase Memory', 'Viz.js 3.29.0', 'Graphviz', 'Expat', 'THIRD_PARTY_NOTICES.md']
      .forEach((term) => assert.match(text, new RegExp(term.replace('.', '\\.'))));
  }
});
