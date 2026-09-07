import assert from "node:assert/strict";
import { execFileSync, spawnSync } from "node:child_process";
import {
  mkdtempSync,
  readFileSync,
  readdirSync,
  writeFileSync,
} from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import test from "node:test";

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const CLI = join(ROOT, "codebase-system-map", "scripts", "system-map.mjs");
const FIXTURE = join(ROOT, "codebase-system-map", "scripts", "fixtures", "valid-system-map.json");
const REPO = join(ROOT, "codebase-system-map", "scripts", "fixtures", "repo");

function run(args) {
  return spawnSync(process.execPath, [CLI, ...args], {
    cwd: ROOT,
    encoding: "utf8",
  });
}

function writeCandidate(directory, name, transform) {
  const map = JSON.parse(readFileSync(FIXTURE, "utf8"));
  transform(map);
  const candidate = join(directory, name);
  writeFileSync(candidate, JSON.stringify(map, null, 2), { mode: 0o600 });
  return candidate;
}

test("doctor and the bundled fixture pass", () => {
  const doctor = run(["doctor"]);
  assert.equal(doctor.status, 0, doctor.stderr + doctor.stdout);

  const validation = run(["validate", FIXTURE, "--repo", REPO, "--json"]);
  assert.equal(validation.status, 0, validation.stderr + validation.stdout);
  assert.deepEqual(JSON.parse(validation.stdout).summary, { errors: 0, warnings: 0 });
});

test("a small repository may use one evidence-backed module", () => {
  const directory = mkdtempSync(join(tmpdir(), "codebase-map-small-"));
  const candidate = writeCandidate(directory, "one-module.json", (map) => {
    map.modules = [{
      id: "system",
      name: "Complete flow",
      responsibility: "Turn a request into a checked offline document.",
      source_refs: map.sources.map((source) => source.id),
    }];
    map.nodes.forEach((node) => {
      node.module_id = "system";
    });
  });

  const validation = run(["validate", candidate, "--repo", REPO, "--json"]);
  assert.equal(validation.status, 0, validation.stderr + validation.stdout);
});

test("explicit decision, worker, and external node kinds are accepted", () => {
  const directory = mkdtempSync(join(tmpdir(), "codebase-map-kinds-"));
  for (const kind of ["decision", "worker", "external"]) {
    const candidate = writeCandidate(directory, kind + ".json", (map) => {
      map.nodes.find((node) => node.id === "check-model").kind = kind;
    });
    const validation = run(["validate", candidate, "--repo", REPO, "--json"]);
    assert.equal(validation.status, 0, kind + ": " + validation.stderr + validation.stdout);
  }
});

test("presentation profiles change the document reading path", () => {
  const directory = mkdtempSync(join(tmpdir(), "codebase-map-profile-"));
  const productCandidate = writeCandidate(directory, "product-overview.json", (map) => {
    map.meta.presentation = {
      audience: "product",
      detail_level: "overview",
      focus: ["capabilities", "prompts"],
      reader_goal: "Compare module responsibilities and prompt effects.",
      priorities: ["prompt effects", "reader-visible outcomes"],
      deemphasize: ["ordinary implementation plumbing"],
    };
  });
  const productOutput = join(directory, "product.html");
  const product = run(["deliver", productCandidate, productOutput, "--repo", REPO, "--json"]);
  assert.equal(product.status, 0, product.stderr + product.stdout);
  const productHtml = readFileSync(productOutput, "utf8");
  assert.match(productHtml, /class="audience-product detail-overview"/);
  assert.match(productHtml, /Compare module responsibilities and prompt effects\./);
  assert.match(productHtml, /class="prompt-spotlight"/);
  assert.doesNotMatch(productHtml, /class="node-list"/);
  assert.doesNotMatch(productHtml, /data-diagram="module:/);

  const technicalCandidate = writeCandidate(directory, "technical-deep.json", (map) => {
    map.meta.presentation = {
      audience: "technical",
      detail_level: "deep",
      focus: ["runtime-flow", "state", "interfaces", "source-evidence"],
    };
  });
  const technicalOutput = join(directory, "technical.html");
  const technical = run(["deliver", technicalCandidate, technicalOutput, "--repo", REPO, "--json"]);
  assert.equal(technical.status, 0, technical.stderr + technical.stdout);
  const technicalHtml = readFileSync(technicalOutput, "utf8");
  assert.match(technicalHtml, /class="audience-technical detail-deep"/);
  assert.match(technicalHtml, /<details class="node"[^>]+ open>/);
  assert.match(technicalHtml, /data-diagram="module:intake"/);
  assert.doesNotMatch(technicalHtml, /class="prompt-spotlight"/);
});

test("invalid presentation values return stable diagnostics", () => {
  const directory = mkdtempSync(join(tmpdir(), "codebase-map-profile-invalid-"));
  const candidate = writeCandidate(directory, "invalid-profile.json", (map) => {
    map.meta.presentation.audience = "stakeholder";
    map.meta.presentation.priorities = [42];
  });
  const validation = run(["validate", candidate, "--repo", REPO, "--json"]);
  assert.equal(validation.status, 1);
  const result = JSON.parse(validation.stdout);
  assert.ok(result.diagnostics.some((item) => item.code === "PRESENTATION_AUDIENCE_INVALID"));
  assert.ok(result.diagnostics.some((item) => item.code === "TYPE_STRING_REQUIRED" && item.subject === "/meta/presentation/priorities/0"));
});

test("delivery is standalone and a failed retry preserves last-good", () => {
  const directory = mkdtempSync(join(tmpdir(), "codebase-map-delivery-"));
  const output = join(directory, "system-map.html");

  const delivered = run(["deliver", FIXTURE, output, "--repo", REPO, "--json"]);
  assert.equal(delivered.status, 0, delivered.stderr + delivered.stdout);

  const before = execFileSync(process.execPath, [
    "-e",
    "const f=require('fs');const c=require('crypto');process.stdout.write(c.createHash('sha256').update(f.readFileSync(process.argv[1])).digest('hex'))",
    output,
  ], { encoding: "utf8" });
  const html = readFileSync(output, "utf8");
  assert.match(html, /<!doctype html>/i);
  assert.match(html, /behavior:'instant'/);
  assert.doesNotMatch(html, /(?:src|href)="https?:\/\//i);

  const failed = run([
    "deliver",
    FIXTURE,
    output,
    "--repo",
    join(directory, "missing-repository"),
    "--json",
  ]);
  assert.equal(failed.status, 1);
  const after = execFileSync(process.execPath, [
    "-e",
    "const f=require('fs');const c=require('crypto');process.stdout.write(c.createHash('sha256').update(f.readFileSync(process.argv[1])).digest('hex'))",
    output,
  ], { encoding: "utf8" });
  assert.equal(after, before);
  assert.deepEqual(readdirSync(directory).sort(), ["system-map.html"]);
});
