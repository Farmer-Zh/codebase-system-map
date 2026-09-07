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
