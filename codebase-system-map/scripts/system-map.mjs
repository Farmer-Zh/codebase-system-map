#!/usr/bin/env node

import {
  closeSync,
  existsSync,
  fsyncSync,
  mkdirSync,
  openSync,
  readFileSync,
  realpathSync,
  renameSync,
  rmSync,
  statSync,
  writeFileSync,
} from "node:fs";
import { dirname, isAbsolute, relative, resolve, sep } from "node:path";
import { fileURLToPath } from "node:url";

const SCRIPT_DIR = dirname(fileURLToPath(import.meta.url));
const SKILL_DIR = resolve(SCRIPT_DIR, "..");
const SCHEMA_PATH = resolve(SKILL_DIR, "schemas", "system-map.schema.json");
const VIZ_PATH = resolve(SKILL_DIR, "assets", "viz.js");
const LICENSES_DIR = resolve(SKILL_DIR, "assets", "licenses");
const VIZ_LICENSE_PATH = resolve(LICENSES_DIR, "VIZ_JS_LICENSE.txt");
const GRAPHVIZ_LICENSE_PATH = resolve(LICENSES_DIR, "GRAPHVIZ_LICENSE.txt");
const EXPAT_LICENSE_PATH = resolve(LICENSES_DIR, "EXPAT_LICENSE.txt");
const VERSION = "0.2.0";
const ID_PATTERN = /^[a-z][a-z0-9-]*$/;
const NODE_KINDS = new Set(["entry", "stage", "decision", "worker", "llm", "tool", "store", "external", "artifact", "output"]);
const EDGE_TYPES = new Set(["flow", "read", "write", "return", "dispatch", "feedback"]);
const EVIDENCE_KINDS = new Set(["code", "documentation", "configuration", "prompt"]);
const AUDIENCES = new Set(["product", "technical", "mixed"]);
const DETAIL_LEVELS = new Set(["overview", "standard", "deep"]);
const PRESENTATION_FOCUS = new Set(["capabilities", "prompts", "runtime-flow", "state", "interfaces", "source-evidence"]);
const TOP_LEVEL_FIELDS = ["meta", "system", "modules", "nodes", "edges", "sources", "prompts"];
const GENERATED_SEGMENTS = new Set([".git", ".codebase-map", "build", "dist", "generated", "node_modules", "vendor"]);

function diagnostic(code, subject, evidence, supportedFixes, severity = "error") {
  return { code, severity, subject, evidence, supportedFixes };
}

function add(diags, code, subject, evidence, supportedFixes, severity = "error") {
  diags.push(diagnostic(code, subject, evidence, supportedFixes, severity));
}

function isObject(value) {
  return value !== null && typeof value === "object" && !Array.isArray(value);
}

function hasOwn(value, key) {
  return Object.prototype.hasOwnProperty.call(value, key);
}

function checkFields(diags, value, subject, required, allowed) {
  if (!isObject(value)) {
    add(diags, "TYPE_OBJECT_REQUIRED", subject, { actualType: Array.isArray(value) ? "array" : typeof value }, ["replace_with_object"]);
    return false;
  }
  for (const key of required) {
    if (!hasOwn(value, key)) {
      add(diags, "REQUIRED_FIELD_MISSING", `${subject}/${key}`, { required: true }, ["add_field"]);
    }
  }
  for (const key of Object.keys(value)) {
    if (!allowed.includes(key)) {
      add(diags, "UNKNOWN_FIELD", `${subject}/${key}`, { allowed }, ["remove_field", "rename_field"]);
    }
  }
  return true;
}

function checkString(diags, value, subject, { allowEmpty = false } = {}) {
  if (typeof value !== "string") {
    add(diags, "TYPE_STRING_REQUIRED", subject, { actualType: typeof value }, ["replace_value"]);
    return false;
  }
  if (!allowEmpty && value.trim().length === 0) {
    add(diags, "STRING_EMPTY", subject, { actual: value }, ["replace_value"]);
    return false;
  }
  return true;
}

function checkId(diags, value, subject) {
  if (!checkString(diags, value, subject)) return false;
  if (!ID_PATTERN.test(value)) {
    add(diags, "ID_FORMAT_INVALID", subject, { actual: value, pattern: ID_PATTERN.source }, ["rename_id", "update_references"]);
    return false;
  }
  return true;
}

function checkArray(diags, value, subject) {
  if (!Array.isArray(value)) {
    add(diags, "TYPE_ARRAY_REQUIRED", subject, { actualType: typeof value }, ["replace_with_array"]);
    return false;
  }
  return true;
}

function checkStringArray(diags, value, subject, { ids = false, nonEmpty = false } = {}) {
  if (!checkArray(diags, value, subject)) return false;
  if (nonEmpty && value.length === 0) add(diags, "ARRAY_EMPTY", subject, { minimumItems: 1 }, ["add_item"]);
  const seen = new Set();
  value.forEach((item, index) => {
    const ok = ids ? checkId(diags, item, `${subject}/${index}`) : checkString(diags, item, `${subject}/${index}`);
    if (ok && seen.has(item)) add(diags, "ARRAY_DUPLICATE", `${subject}/${index}`, { value: item }, ["remove_item"]);
    seen.add(item);
  });
  return true;
}

function validateShape(map, diags) {
  if (!checkFields(diags, map, "", TOP_LEVEL_FIELDS, TOP_LEVEL_FIELDS)) return;

  if (checkFields(diags, map.meta, "/meta", ["schema_version", "repository", "analyzed_revision", "language"], ["schema_version", "repository", "analyzed_revision", "language", "presentation"])) {
    checkString(diags, map.meta.schema_version, "/meta/schema_version");
    if (typeof map.meta.schema_version === "string" && map.meta.schema_version !== "2.0") {
      add(diags, "SCHEMA_VERSION_UNSUPPORTED", "/meta/schema_version", { actual: map.meta.schema_version, supported: ["2.0"] }, ["replace_value"]);
    }
    checkString(diags, map.meta.repository, "/meta/repository");
    checkString(diags, map.meta.analyzed_revision, "/meta/analyzed_revision");
    checkString(diags, map.meta.language, "/meta/language");
    if (hasOwn(map.meta, "presentation") && checkFields(diags, map.meta.presentation, "/meta/presentation", ["audience", "detail_level", "focus"], ["audience", "detail_level", "focus", "reader_goal", "priorities", "deemphasize"])) {
      if (checkString(diags, map.meta.presentation.audience, "/meta/presentation/audience") && !AUDIENCES.has(map.meta.presentation.audience)) {
        add(diags, "PRESENTATION_AUDIENCE_INVALID", "/meta/presentation/audience", { actual: map.meta.presentation.audience, allowed: [...AUDIENCES] }, ["replace_value"]);
      }
      if (checkString(diags, map.meta.presentation.detail_level, "/meta/presentation/detail_level") && !DETAIL_LEVELS.has(map.meta.presentation.detail_level)) {
        add(diags, "PRESENTATION_DETAIL_INVALID", "/meta/presentation/detail_level", { actual: map.meta.presentation.detail_level, allowed: [...DETAIL_LEVELS] }, ["replace_value"]);
      }
      if (checkStringArray(diags, map.meta.presentation.focus, "/meta/presentation/focus")) {
        map.meta.presentation.focus.forEach((value, index) => {
          if (typeof value === "string" && !PRESENTATION_FOCUS.has(value)) {
            add(diags, "PRESENTATION_FOCUS_INVALID", `/meta/presentation/focus/${index}`, { actual: value, allowed: [...PRESENTATION_FOCUS] }, ["replace_value", "remove_item"]);
          }
        });
      }
      if (hasOwn(map.meta.presentation, "reader_goal")) checkString(diags, map.meta.presentation.reader_goal, "/meta/presentation/reader_goal");
      if (hasOwn(map.meta.presentation, "priorities")) checkStringArray(diags, map.meta.presentation.priorities, "/meta/presentation/priorities");
      if (hasOwn(map.meta.presentation, "deemphasize")) checkStringArray(diags, map.meta.presentation.deemphasize, "/meta/presentation/deemphasize");
    }
  }

  if (checkFields(diags, map.system, "/system", ["name", "summary"], ["name", "summary"])) {
    checkString(diags, map.system.name, "/system/name");
    checkString(diags, map.system.summary, "/system/summary");
  }

  if (checkArray(diags, map.modules, "/modules")) {
    if (map.modules.length < 1 || map.modules.length > 8) {
      add(diags, "MODULE_COUNT_OUT_OF_RANGE", "/modules", { actual: map.modules.length, minimum: 1, maximum: 8 }, ["add_module", "merge_modules", "remove_module"]);
    }
    map.modules.forEach((item, index) => {
      const at = `/modules/${index}`;
      if (!checkFields(diags, item, at, ["id", "name", "responsibility", "source_refs"], ["id", "name", "responsibility", "source_refs"])) return;
      checkId(diags, item.id, `${at}/id`);
      checkString(diags, item.name, `${at}/name`);
      checkString(diags, item.responsibility, `${at}/responsibility`);
      checkStringArray(diags, item.source_refs, `${at}/source_refs`, { ids: true, nonEmpty: true });
    });
  }

  if (checkArray(diags, map.nodes, "/nodes")) {
    if (map.nodes.length < 2 || map.nodes.length > 30) {
      add(diags, "NODE_COUNT_OUT_OF_RANGE", "/nodes", { actual: map.nodes.length, minimum: 2, maximum: 30 }, ["add_node", "merge_nodes", "remove_node"]);
    }
    map.nodes.forEach((item, index) => {
      const at = `/nodes/${index}`;
      const fields = ["id", "module_id", "kind", "name", "purpose", "inputs", "outputs", "source_refs", "prompt_refs"];
      if (!checkFields(diags, item, at, fields, fields)) return;
      checkId(diags, item.id, `${at}/id`);
      checkId(diags, item.module_id, `${at}/module_id`);
      if (checkString(diags, item.kind, `${at}/kind`) && !NODE_KINDS.has(item.kind)) {
        add(diags, "NODE_KIND_INVALID", `${at}/kind`, { actual: item.kind, allowed: [...NODE_KINDS] }, ["replace_value"]);
      }
      checkString(diags, item.name, `${at}/name`);
      checkString(diags, item.purpose, `${at}/purpose`);
      checkStringArray(diags, item.inputs, `${at}/inputs`);
      checkStringArray(diags, item.outputs, `${at}/outputs`);
      checkStringArray(diags, item.source_refs, `${at}/source_refs`, { ids: true, nonEmpty: true });
      checkStringArray(diags, item.prompt_refs, `${at}/prompt_refs`, { ids: true });
    });
  }

  if (checkArray(diags, map.edges, "/edges")) {
    if (map.edges.length === 0) add(diags, "ARRAY_EMPTY", "/edges", { minimumItems: 1 }, ["add_edge"]);
    map.edges.forEach((item, index) => {
      const at = `/edges/${index}`;
      const fields = ["from", "to", "type", "label", "primary", "source_refs"];
      if (!checkFields(diags, item, at, fields, fields)) return;
      checkId(diags, item.from, `${at}/from`);
      checkId(diags, item.to, `${at}/to`);
      if (checkString(diags, item.type, `${at}/type`) && !EDGE_TYPES.has(item.type)) {
        add(diags, "EDGE_TYPE_INVALID", `${at}/type`, { actual: item.type, allowed: [...EDGE_TYPES] }, ["replace_value"]);
      }
      checkString(diags, item.label, `${at}/label`, { allowEmpty: true });
      if (typeof item.primary !== "boolean") add(diags, "TYPE_BOOLEAN_REQUIRED", `${at}/primary`, { actualType: typeof item.primary }, ["replace_value"]);
      checkStringArray(diags, item.source_refs, `${at}/source_refs`, { ids: true, nonEmpty: true });
    });
  }

  if (checkArray(diags, map.sources, "/sources")) {
    if (map.sources.length === 0) add(diags, "ARRAY_EMPTY", "/sources", { minimumItems: 1 }, ["add_source"]);
    map.sources.forEach((item, index) => {
      const at = `/sources/${index}`;
      const fields = ["id", "path", "start_line", "end_line", "evidence_kind"];
      if (!checkFields(diags, item, at, fields, fields)) return;
      checkId(diags, item.id, `${at}/id`);
      checkString(diags, item.path, `${at}/path`);
      for (const lineField of ["start_line", "end_line"]) {
        if (!Number.isInteger(item[lineField]) || item[lineField] < 1) {
          add(diags, "SOURCE_LINE_INVALID", `${at}/${lineField}`, { actual: item[lineField], minimum: 1 }, ["replace_value"]);
        }
      }
      if (checkString(diags, item.evidence_kind, `${at}/evidence_kind`) && !EVIDENCE_KINDS.has(item.evidence_kind)) {
        add(diags, "EVIDENCE_KIND_INVALID", `${at}/evidence_kind`, { actual: item.evidence_kind, allowed: [...EVIDENCE_KINDS] }, ["replace_value"]);
      }
    });
  }

  if (checkArray(diags, map.prompts, "/prompts")) {
    map.prompts.forEach((item, index) => {
      const at = `/prompts/${index}`;
      const fields = ["id", "source_ref", "title", "excerpt"];
      if (!checkFields(diags, item, at, fields, fields)) return;
      checkId(diags, item.id, `${at}/id`);
      checkId(diags, item.source_ref, `${at}/source_ref`);
      checkString(diags, item.title, `${at}/title`);
      checkString(diags, item.excerpt, `${at}/excerpt`);
    });
  }
}

function items(value) {
  return Array.isArray(value) ? value.filter(isObject) : [];
}

function uniqueIndex(diags, collection, base) {
  const result = new Map();
  collection.forEach((item, index) => {
    if (typeof item.id !== "string") return;
    if (result.has(item.id)) {
      add(diags, "ID_DUPLICATE", `${base}/${index}/id`, { id: item.id, firstSubject: `${base}/${result.get(item.id).index}/id` }, ["rename_id", "update_references"]);
    } else {
      result.set(item.id, { ...item, index });
    }
  });
  return result;
}

function validateReferences(map, diags) {
  const modules = items(map.modules);
  const nodes = items(map.nodes);
  const sources = items(map.sources);
  const prompts = items(map.prompts);
  const moduleById = uniqueIndex(diags, modules, "/modules");
  const nodeById = uniqueIndex(diags, nodes, "/nodes");
  const sourceById = uniqueIndex(diags, sources, "/sources");
  const promptById = uniqueIndex(diags, prompts, "/prompts");

  const checkRefs = (refs, known, subject, kind) => {
    if (!Array.isArray(refs)) return;
    refs.forEach((ref, index) => {
      if (typeof ref === "string" && !known.has(ref)) {
        add(diags, `${kind}_REFERENCE_MISSING`, `${subject}/${index}`, { reference: ref }, ["replace_reference", `add_${kind.toLowerCase()}`]);
      }
    });
  };

  modules.forEach((module, index) => checkRefs(module.source_refs, sourceById, `/modules/${index}/source_refs`, "SOURCE"));
  nodes.forEach((node, index) => {
    if (typeof node.module_id === "string" && !moduleById.has(node.module_id)) {
      add(diags, "MODULE_REFERENCE_MISSING", `/nodes/${index}/module_id`, { reference: node.module_id }, ["replace_reference", "add_module"]);
    }
    checkRefs(node.source_refs, sourceById, `/nodes/${index}/source_refs`, "SOURCE");
    checkRefs(node.prompt_refs, promptById, `/nodes/${index}/prompt_refs`, "PROMPT");
    if (Array.isArray(node.prompt_refs) && node.prompt_refs.length > 0 && node.kind !== "llm") {
      add(diags, "PROMPT_ATTACHED_TO_NON_LLM", `/nodes/${index}/prompt_refs`, { nodeId: node.id, kind: node.kind }, ["remove_prompt_reference", "replace_node_kind"]);
    }
  });
  items(map.edges).forEach((edge, index) => {
    for (const endpoint of ["from", "to"]) {
      if (typeof edge[endpoint] === "string" && !nodeById.has(edge[endpoint])) {
        add(diags, "NODE_REFERENCE_MISSING", `/edges/${index}/${endpoint}`, { reference: edge[endpoint] }, ["replace_reference", "add_node"]);
      }
    }
    checkRefs(edge.source_refs, sourceById, `/edges/${index}/source_refs`, "SOURCE");
    if (edge.from === edge.to) add(diags, "EDGE_SELF_REFERENCE", `/edges/${index}`, { nodeId: edge.from }, ["remove_edge", "replace_endpoint"]);
  });
  prompts.forEach((prompt, index) => {
    if (typeof prompt.source_ref === "string" && !sourceById.has(prompt.source_ref)) {
      add(diags, "SOURCE_REFERENCE_MISSING", `/prompts/${index}/source_ref`, { reference: prompt.source_ref }, ["replace_reference", "add_source"]);
    } else if (sourceById.get(prompt.source_ref)?.evidence_kind !== "prompt") {
      add(diags, "PROMPT_SOURCE_KIND_INVALID", `/prompts/${index}/source_ref`, { sourceRef: prompt.source_ref, actualKind: sourceById.get(prompt.source_ref)?.evidence_kind }, ["replace_reference", "replace_evidence_kind"]);
    }
  });

  const usedPrompts = new Set(nodes.flatMap((node) => Array.isArray(node.prompt_refs) ? node.prompt_refs : []));
  prompts.forEach((prompt, index) => {
    if (typeof prompt.id === "string" && !usedPrompts.has(prompt.id)) {
      add(diags, "PROMPT_UNREFERENCED", `/prompts/${index}`, { promptId: prompt.id }, ["attach_prompt", "remove_prompt"], "warning");
    }
  });
  const usedModules = new Set(nodes.map((node) => node.module_id));
  modules.forEach((module, index) => {
    if (typeof module.id === "string" && !usedModules.has(module.id)) {
      add(diags, "MODULE_WITHOUT_NODES", `/modules/${index}`, { moduleId: module.id }, ["add_node", "remove_module", "merge_modules"]);
    }
  });
}

function validateEvidence(map, repoPath, diags) {
  let repoReal;
  try {
    repoReal = realpathSync(repoPath);
    if (!statSync(repoReal).isDirectory()) throw new Error("not a directory");
  } catch (error) {
    add(diags, "REPOSITORY_UNREADABLE", "/repository", { path: repoPath, message: error.message }, ["replace_repository_path"]);
    return;
  }
  items(map.sources).forEach((source, index) => {
    const subject = `/sources/${index}`;
    if (typeof source.path !== "string" || source.path.length === 0) return;
    const portablePath = source.path.replaceAll("\\", "/");
    const segments = portablePath.split("/").filter(Boolean);
    if (isAbsolute(source.path) || /^[a-zA-Z]:\//.test(portablePath) || segments.includes("..")) {
      add(diags, "SOURCE_PATH_NOT_RELATIVE", `${subject}/path`, { path: source.path }, ["replace_with_repository_relative_path"]);
      return;
    }
    const forbidden = segments.find((segment) => GENERATED_SEGMENTS.has(segment.toLowerCase()));
    if (forbidden) {
      add(diags, "SOURCE_PATH_DISALLOWED", `${subject}/path`, { path: source.path, segment: forbidden }, ["replace_source", "remove_source"]);
      return;
    }
    const candidate = resolve(repoReal, ...segments);
    if (!existsSync(candidate)) {
      add(diags, "SOURCE_FILE_MISSING", `${subject}/path`, { path: source.path }, ["replace_source_path", "remove_source"]);
      return;
    }
    let sourceReal;
    try {
      sourceReal = realpathSync(candidate);
      if (!statSync(sourceReal).isFile()) throw new Error("not a file");
    } catch (error) {
      add(diags, "SOURCE_FILE_UNREADABLE", `${subject}/path`, { path: source.path, message: error.message }, ["replace_source_path", "remove_source"]);
      return;
    }
    const fromRepo = relative(repoReal, sourceReal);
    if (fromRepo === ".." || fromRepo.startsWith(`..${sep}`) || isAbsolute(fromRepo)) {
      add(diags, "SOURCE_PATH_OUTSIDE_REPOSITORY", `${subject}/path`, { path: source.path, resolvedPath: sourceReal }, ["replace_source_path", "remove_source"]);
      return;
    }
    let contents;
    try {
      contents = readFileSync(sourceReal, "utf8");
    } catch (error) {
      add(diags, "SOURCE_FILE_UNREADABLE", `${subject}/path`, { path: source.path, message: error.message }, ["replace_source_path", "remove_source"]);
      return;
    }
    const lineCount = contents.length === 0 ? 0 : contents.split(/\r\n|\r|\n/).length;
    if (Number.isInteger(source.start_line) && Number.isInteger(source.end_line)) {
      if (source.start_line > source.end_line) {
        add(diags, "SOURCE_LINE_RANGE_REVERSED", subject, { startLine: source.start_line, endLine: source.end_line }, ["replace_line_range"]);
      } else if (source.end_line > lineCount) {
        add(diags, "SOURCE_LINE_OUT_OF_RANGE", subject, { startLine: source.start_line, endLine: source.end_line, fileLines: lineCount }, ["replace_line_range", "replace_source_path"]);
      }
    }
  });
}

function reachable(startIds, adjacency) {
  const seen = new Set(startIds);
  const queue = [...startIds];
  while (queue.length) {
    const current = queue.shift();
    for (const next of adjacency.get(current) ?? []) {
      if (!seen.has(next)) {
        seen.add(next);
        queue.push(next);
      }
    }
  }
  return seen;
}

function validateTopology(map, diags) {
  const nodes = items(map.nodes).filter((node) => typeof node.id === "string");
  const known = new Set(nodes.map((node) => node.id));
  const edges = items(map.edges).filter((edge) => known.has(edge.from) && known.has(edge.to) && edge.from !== edge.to);
  const entries = nodes.filter((node) => node.kind === "entry");
  const outputs = nodes.filter((node) => node.kind === "output");
  if (entries.length === 0) add(diags, "ENTRY_NODE_MISSING", "/nodes", { entryCount: 0 }, ["add_entry_node", "replace_node_kind"]);
  if (outputs.length === 0) add(diags, "OUTPUT_NODE_MISSING", "/nodes", { outputCount: 0 }, ["add_output_node", "replace_node_kind"]);

  const degree = new Map(nodes.map((node) => [node.id, 0]));
  edges.forEach((edge) => {
    degree.set(edge.from, degree.get(edge.from) + 1);
    degree.set(edge.to, degree.get(edge.to) + 1);
  });
  nodes.forEach((node, index) => {
    if (degree.get(node.id) === 0) add(diags, "NODE_ORPHAN", `/nodes/${index}`, { nodeId: node.id }, ["add_edge", "remove_node"]);
  });

  const primaryEdges = edges.filter((edge) => edge.primary === true);
  if (primaryEdges.length === 0) {
    add(diags, "PRIMARY_PATH_MISSING", "/edges", { primaryEdgeCount: 0 }, ["mark_primary_edges"]);
    return;
  }
  const forward = new Map();
  const reverse = new Map();
  for (const edge of primaryEdges) {
    if (!forward.has(edge.from)) forward.set(edge.from, []);
    if (!reverse.has(edge.to)) reverse.set(edge.to, []);
    forward.get(edge.from).push(edge.to);
    reverse.get(edge.to).push(edge.from);
  }
  const fromEntry = reachable(entries.map((node) => node.id), forward);
  const toOutput = reachable(outputs.map((node) => node.id), reverse);
  const reachableOutputs = outputs.filter((node) => fromEntry.has(node.id));
  if (entries.length && outputs.length && reachableOutputs.length === 0) {
    add(diags, "PRIMARY_PATH_DISCONNECTED", "/edges", { entries: entries.map((node) => node.id), outputs: outputs.map((node) => node.id) }, ["mark_primary_edges", "add_edge"]);
  }
  const primaryNodes = new Set(primaryEdges.flatMap((edge) => [edge.from, edge.to]));
  for (const nodeId of primaryNodes) {
    if (!fromEntry.has(nodeId) || !toOutput.has(nodeId)) {
      add(diags, "PRIMARY_NODE_OFF_PATH", `/nodes/${nodes.findIndex((node) => node.id === nodeId)}`, { nodeId, reachableFromEntry: fromEntry.has(nodeId), canReachOutput: toOutput.has(nodeId) }, ["unmark_primary_edge", "add_primary_edge"]);
    }
  }
}

function validateMap(map, repoPath) {
  const diagnostics = [];
  validateShape(map, diagnostics);
  if (!isObject(map)) return diagnostics;
  validateReferences(map, diagnostics);
  validateEvidence(map, repoPath, diagnostics);
  validateTopology(map, diagnostics);
  const unique = [];
  const seen = new Set();
  for (const item of diagnostics) {
    const key = `${item.code}\u0000${item.subject}\u0000${JSON.stringify(item.evidence)}`;
    if (!seen.has(key)) {
      seen.add(key);
      unique.push(item);
    }
  }
  unique.sort((a, b) => a.subject.localeCompare(b.subject) || a.code.localeCompare(b.code));
  return unique;
}

function h(value) {
  return String(value ?? "").replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;").replaceAll('"', "&quot;").replaceAll("'", "&#39;");
}

function dot(value) {
  return String(value ?? "").replaceAll("\\", "\\\\").replaceAll('"', '\\"').replaceAll("\n", "\\n");
}

function wrapLabel(value, width = 22) {
  const text = String(value ?? "").trim();
  if (text.length <= width) return text;
  const words = text.includes(" ") ? text.split(/\s+/) : [...text];
  const separator = text.includes(" ") ? " " : "";
  const lines = [];
  let line = "";
  for (const word of words) {
    const candidate = line ? `${line}${separator}${word}` : word;
    if (candidate.length > width && line) {
      lines.push(line);
      line = word;
    } else line = candidate;
  }
  if (line) lines.push(line);
  return lines.join("\n");
}

function sourceText(refs, sourceById) {
  return (refs ?? []).map((ref) => sourceById.get(ref)).filter(Boolean).map((source) => `${source.path}:${source.start_line}-${source.end_line}`);
}

function moduleRelations(map, moduleByNode) {
  const relations = new Map();
  for (const edge of map.edges) {
    const from = moduleByNode.get(edge.from);
    const to = moduleByNode.get(edge.to);
    if (!from || !to || from === to) continue;
    const key = `${from}\u0000${to}`;
    const current = relations.get(key) ?? { from, to, primary: false, labels: new Set() };
    current.primary ||= edge.primary;
    if (edge.label) current.labels.add(edge.label);
    relations.set(key, current);
  }
  return [...relations.values()];
}

function systemDot(map) {
  const moduleByNode = new Map(map.nodes.map((node) => [node.id, node.module_id]));
  const lines = [
    "digraph G {",
    'graph [rankdir=LR, bgcolor="transparent", pad="0.35", nodesep="0.55", ranksep="0.9", splines=polyline];',
    'node [shape=box, style="rounded,filled", fontname="Arial", fontsize=15, color="#91a4c7", fillcolor="#f4f7ff", fontcolor="#172033", penwidth=1.25, margin="0.22,0.16"];',
    'edge [color="#365fba", penwidth=1.8, arrowsize=0.75, fontname="Arial", fontsize=10, fontcolor="#52627c"];',
  ];
  for (const module of map.modules) {
    lines.push(`"${dot(module.id)}" [label="${dot(wrapLabel(module.name))}", tooltip="${dot(module.responsibility)}", URL="#module-${dot(module.id)}", target="_top"];`);
  }
  for (const relation of moduleRelations(map, moduleByNode)) {
    const label = [...relation.labels].slice(0, 2).join(" / ");
    const attrs = [label ? `label="${dot(wrapLabel(label, 18))}"` : "", relation.primary ? "weight=8" : 'style="dashed",color="#a7b0c0",constraint=false,penwidth=1.1'].filter(Boolean).join(",");
    lines.push(`"${dot(relation.from)}" -> "${dot(relation.to)}" [${attrs}];`);
  }
  lines.push("}");
  return lines.join("\n");
}

function moduleDot(map, module) {
  const moduleById = new Map(map.modules.map((item) => [item.id, item]));
  const nodeById = new Map(map.nodes.map((node) => [node.id, node]));
  const ownNodes = map.nodes.filter((node) => node.module_id === module.id);
  const ownIds = new Set(ownNodes.map((node) => node.id));
  const incoming = new Map();
  const outgoing = new Map();
  const internal = [];
  for (const edge of map.edges) {
    const fromOwn = ownIds.has(edge.from);
    const toOwn = ownIds.has(edge.to);
    if (fromOwn && toOwn) internal.push(edge);
    else if (!fromOwn && toOwn) {
      const externalModule = nodeById.get(edge.from)?.module_id;
      if (externalModule) incoming.set(externalModule, [...(incoming.get(externalModule) ?? []), edge]);
    } else if (fromOwn && !toOwn) {
      const externalModule = nodeById.get(edge.to)?.module_id;
      if (externalModule) outgoing.set(externalModule, [...(outgoing.get(externalModule) ?? []), edge]);
    }
  }
  const complex = internal.some((edge) => edge.type === "feedback") || ownNodes.some((node) => internal.filter((edge) => edge.from === node.id).length > 1);
  const colors = { entry: "#dbeafe", stage: "#f8fafc", decision: "#ffedd5", worker: "#dcfce7", llm: "#ede9fe", tool: "#dcfce7", store: "#fef3c7", external: "#e2e8f0", artifact: "#e0f2fe", output: "#ffe4e6" };
  const lines = [
    "digraph G {",
    `graph [rankdir=${complex ? "TB" : "LR"}, bgcolor="transparent", pad="0.3", nodesep="0.48", ranksep="0.78", splines=polyline];`,
    'node [shape=box, style="rounded,filled", fontname="Arial", fontsize=12, color="#9aa8bc", fontcolor="#172033", penwidth=1.15, margin="0.17,0.12"];',
    'edge [color="#667b9e", fontname="Arial", fontsize=9, fontcolor="#596780", arrowsize=0.7];',
  ];
  for (const [externalId] of incoming) {
    const label = moduleById.get(externalId)?.name ?? externalId;
    lines.push(`"in-${dot(externalId)}" [label="${dot(wrapLabel(label))}\ninput", shape=box, style="rounded,dashed,filled", fillcolor="#f2f4f7", color="#98a2b3", URL="#module-${dot(externalId)}", target="_top"];`);
  }
  for (const node of ownNodes) {
    const promptMark = node.prompt_refs.length ? " · Prompt" : "";
    lines.push(`"${dot(node.id)}" [label="${dot(wrapLabel(node.name))}\n${dot(node.kind + promptMark)}", tooltip="${dot(node.purpose)}", fillcolor="${colors[node.kind] ?? colors.stage}", URL="#node-${dot(node.id)}", target="_top"];`);
  }
  for (const [externalId] of outgoing) {
    const label = moduleById.get(externalId)?.name ?? externalId;
    lines.push(`"out-${dot(externalId)}" [label="${dot(wrapLabel(label))}\noutput", shape=box, style="rounded,dashed,filled", fillcolor="#f2f4f7", color="#98a2b3", URL="#module-${dot(externalId)}", target="_top"];`);
  }
  for (const edge of internal) {
    const attrs = [edge.label ? `label="${dot(wrapLabel(edge.label, 16))}"` : "", edge.primary ? "penwidth=1.8,color=\"#365fba\"" : 'style="dashed",color="#a7b0c0"'].filter(Boolean).join(",");
    lines.push(`"${dot(edge.from)}" -> "${dot(edge.to)}" [${attrs}];`);
  }
  for (const [externalId, edges] of incoming) for (const edge of edges) {
    lines.push(`"in-${dot(externalId)}" -> "${dot(edge.to)}" [${edge.label ? `label="${dot(wrapLabel(edge.label, 16))}"` : ""}];`);
  }
  for (const [externalId, edges] of outgoing) for (const edge of edges) {
    lines.push(`"${dot(edge.from)}" -> "out-${dot(externalId)}" [${edge.label ? `label="${dot(wrapLabel(edge.label, 16))}"` : ""}];`);
  }
  lines.push("}");
  return lines.join("\n");
}

function copyFor(language) {
  const zh = String(language).toLowerCase().startsWith("zh");
  return zh ? {
    htmlLang: "zh-CN", label: "代码库系统图", overview: "系统总览", architecture: "产品运行架构", modules: "模块",
    primary: "主路径", secondary: "辅助关系", moduleEvidence: "模块证据", input: "输入", output: "输出", evidence: "源码证据",
    prompts: "实际 Prompt", noPrompt: "该节点没有直接关联的 Prompt 证据。", diagramHelp: "实线表示主路径；虚线表示读取、回写、异步或反馈关系。点击图中元素可下钻。",
    externalHelp: "虚线节点是模块边界外的接口。", render: "正在绘图…", renderError: "图形渲染失败：", generated: "基于可追溯源码证据生成",
    promptSpotlight: "关键 Prompt", technicalDetail: "查看技术管线", audience: { product: "产品视图", technical: "技术视图", mixed: "综合视图" }, detail: { overview: "概览", standard: "标准", deep: "深入" },
  } : {
    htmlLang: "en", label: "CODEBASE SYSTEM MAP", overview: "System overview", architecture: "Product runtime architecture", modules: "Modules",
    primary: "Primary path", secondary: "Supporting relation", moduleEvidence: "Module evidence", input: "Input", output: "Output", evidence: "Source evidence",
    prompts: "Actual prompt", noPrompt: "No prompt evidence is directly associated with this node.", diagramHelp: "Solid lines show the primary path. Dashed lines show reads, writes, async work, or feedback. Select an element to drill down.",
    externalHelp: "Dashed nodes are interfaces outside this module.", render: "Drawing…", renderError: "Diagram rendering failed: ", generated: "Generated from traceable source evidence",
    promptSpotlight: "Key prompts", technicalDetail: "View technical pipeline", audience: { product: "Product view", technical: "Technical view", mixed: "Mixed view" }, detail: { overview: "Overview", standard: "Standard", deep: "Deep" },
  };
}

function presentationFor(map) {
  const raw = isObject(map.meta.presentation) ? map.meta.presentation : {};
  const audience = AUDIENCES.has(raw.audience) ? raw.audience : "mixed";
  const detailLevel = DETAIL_LEVELS.has(raw.detail_level) ? raw.detail_level : "standard";
  const defaults = {
    product: ["capabilities", "prompts"],
    technical: ["runtime-flow", "state", "interfaces", "source-evidence"],
    mixed: ["capabilities", "runtime-flow", "prompts"],
  };
  const requestedFocus = Array.isArray(raw.focus) ? raw.focus.filter((value) => PRESENTATION_FOCUS.has(value)) : [];
  return { audience, detailLevel, focus: new Set(requestedFocus.length ? requestedFocus : defaults[audience]) };
}

function renderHtml(map, vizBytes) {
  const c = copyFor(map.meta.language);
  const presentation = presentationFor(map);
  const showEvidence = presentation.audience === "technical" || presentation.detailLevel === "deep" || presentation.focus.has("source-evidence");
  const showPromptSpotlight = presentation.focus.has("prompts");
  const showModuleDetail = presentation.detailLevel !== "overview";
  const sourceById = new Map(map.sources.map((source) => [source.id, source]));
  const promptById = new Map(map.prompts.map((prompt) => [prompt.id, prompt]));
  const diagrams = { system: systemDot(map) };
  const modulesHtml = [];
  for (const [moduleIndexNumber, module] of map.modules.entries()) {
    const moduleNodes = map.nodes.filter((node) => node.module_id === module.id);
    if (showModuleDetail) diagrams[`module:${module.id}`] = moduleDot(map, module);
    const promptRecords = [];
    const seenPrompts = new Set();
    for (const node of moduleNodes) {
      for (const promptRef of node.prompt_refs) {
        const prompt = promptById.get(promptRef);
        if (prompt && !seenPrompts.has(prompt.id)) {
          promptRecords.push({ prompt, node });
          seenPrompts.add(prompt.id);
        }
      }
    }
    const promptSpotlightHtml = showPromptSpotlight && promptRecords.length ? `<section class="prompt-spotlight"><h3>${c.promptSpotlight}</h3><div class="prompt-grid">${promptRecords.map(({ prompt, node }) => {
      const source = sourceById.get(prompt.source_ref);
      const sourceHtml = showEvidence && source ? `<div class="source">${h(`${source.path}:${source.start_line}-${source.end_line}`)}</div>` : "";
      return `<article class="prompt-card"><span>${h(node.name)}</span><h4>${h(prompt.title)}</h4><p>${h(prompt.excerpt)}</p>${sourceHtml}</article>`;
    }).join("")}</div></section>` : "";
    const nodesHtml = showModuleDetail ? moduleNodes.map((node) => {
      const refs = sourceText(node.source_refs, sourceById);
      const prompts = node.prompt_refs.map((ref) => promptById.get(ref)).filter(Boolean);
      const promptHtml = prompts.length ? prompts.map((prompt) => {
        const source = sourceById.get(prompt.source_ref);
        const sourceHtml = showEvidence ? `<div class="source">${h(source ? `${source.path}:${source.start_line}-${source.end_line}` : prompt.source_ref)}</div>` : "";
        return `<section class="prompt"><h5>${h(prompt.title)}</h5>${sourceHtml}<pre>${h(prompt.excerpt)}</pre></section>`;
      }).join("") : `<p class="muted small">${c.noPrompt}</p>`;
      const evidenceHtml = showEvidence ? `<section><h5>${c.evidence}</h5>${chips(refs, "code")}</section>` : "";
      const openAttribute = presentation.detailLevel === "deep" ? " open" : "";
      return `<details class="node" id="node-${h(node.id)}"${openAttribute}><summary><span class="kind kind-${h(node.kind)}">${h(node.kind)}</span><span><strong>${h(node.name)}</strong><small>${h(node.purpose)}</small></span><span class="node-chevron" aria-hidden="true">›</span></summary><div class="node-body"><div class="io"><section><h5>${c.input}</h5>${chips(node.inputs)}</section><section><h5>${c.output}</h5>${chips(node.outputs)}</section></div>${evidenceHtml}${promptHtml}</div></details>`;
    }).join("") : "";
    const moduleNumber = String(moduleIndexNumber + 1).padStart(2, "0");
    const tone = (moduleIndexNumber % 6) + 1;
    const evidenceHtml = showEvidence ? `<div class="evidence"><span>${c.moduleEvidence}</span>${chips(sourceText(module.source_refs, sourceById), "code")}</div>` : "";
    const directDiagram = showModuleDetail ? `<div class="technical-diagram"><p class="diagram-note">${c.externalHelp}</p><div class="diagram module-diagram" data-diagram="module:${h(module.id)}"><span class="muted">${c.render}</span></div></div>` : "";
    const diagramHtml = presentation.audience === "product" && directDiagram ? `<details class="technical-layer"><summary>${c.technicalDetail}<span aria-hidden="true">›</span></summary>${directDiagram}</details>` : directDiagram;
    const nodeListHtml = nodesHtml ? `<div class="node-list">${nodesHtml}</div>` : "";
    const moduleBody = presentation.audience === "product" ? promptSpotlightHtml + nodeListHtml + diagramHtml : diagramHtml + promptSpotlightHtml + nodeListHtml;
    modulesHtml.push(`<article class="module tone-${tone}" id="module-${h(module.id)}"><header class="module-head"><div class="module-title"><span class="module-number">${moduleNumber}</span><div><span class="kicker">${c.modules}</span><h2>${h(module.name)}</h2><p>${h(module.responsibility)}</p></div></div>${evidenceHtml}</header>${moduleBody}</article>`);
  }
  const navigation = map.modules.map((module) => `<a href="#module-${h(module.id)}">${h(module.name)}</a>`).join("");
  const moduleIndex = map.modules.map((module, index) => `<a class="module-link tone-${(index % 6) + 1}" href="#module-${h(module.id)}"><span class="module-link-number">${String(index + 1).padStart(2, "0")}</span><strong>${h(module.name)}</strong><span>${h(module.responsibility)}</span></a>`).join("");
  const systemDiagram = `<div class="system-figure"><div class="legend"><span><i class="line"></i>${c.primary}</span><span><i class="line secondary"></i>${c.secondary}</span></div><div class="diagram system-diagram" data-diagram="system"><span class="muted">${c.render}</span></div></div>`;
  const overviewBody = presentation.audience === "product" ? `<div class="module-index">${moduleIndex}</div>${systemDiagram}` : `${systemDiagram}<div class="module-index">${moduleIndex}</div>`;
  const profileLabel = `${c.audience[presentation.audience]} · ${c.detail[presentation.detailLevel]}`;
  const safeMap = JSON.stringify(map).replaceAll("<", "\\u003c");
  const safeDiagrams = JSON.stringify(diagrams).replaceAll("<", "\\u003c");
  const vizBase64 = vizBytes.toString("base64");
  return `<!doctype html>
<html lang="${c.htmlLang}"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="color-scheme" content="light"><meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; script-src 'unsafe-inline' 'wasm-unsafe-eval' data:; img-src data:"><title>${h(map.system.name)} · System Map</title>
<style>
:root{--ink:#1a1a1a;--charcoal:#37352f;--muted:#5d5b54;--steel:#787671;--line:#e5e3df;--line-strong:#c8c4be;--paper:#f6f5f4;--soft:#fafaf9;--card:#fff;--brand:#5645d4;--brand-pressed:#4534b3;--link:#0075de;--navy:#0a1530;--deep:#070f24;--peach:#ffe8d4;--rose:#fde0ec;--mint:#d9f3e1;--lavender:#e6e0f5;--sky:#dcecfa;--yellow:#fef7d6;--shadow:0 22px 64px rgba(7,15,36,.18)}
*{box-sizing:border-box}html{scroll-behavior:smooth;scroll-padding-top:72px}body{margin:0;background:var(--paper);color:var(--charcoal);font:16px/1.55 "Notion Sans","Segoe UI","Microsoft YaHei",system-ui,sans-serif;-webkit-font-smoothing:antialiased}.hero{position:relative;isolation:isolate;display:grid;place-items:center;min-height:420px;overflow:hidden;background:linear-gradient(145deg,var(--deep),var(--navy) 72%);color:#fff;padding:72px 32px 86px;border:0;text-align:center}.hero:after{content:"";position:absolute;inset:auto 12% -190px;height:260px;background:radial-gradient(ellipse,rgba(86,69,212,.38),transparent 68%);filter:blur(12px);z-index:-1}.hero-inner{position:relative;z-index:2;max-width:900px;margin:auto}.hero .kicker{color:#c9c1ff}.kicker{display:inline-block;color:var(--brand);font-size:11px;font-weight:750;letter-spacing:.12em;text-transform:uppercase}.hero h1{max-width:850px;margin:14px auto 18px;font-size:clamp(42px,6.5vw,72px);font-weight:760;line-height:1.02;letter-spacing:-.045em}.hero p{max-width:720px;margin:auto;color:#d9deea;font-size:clamp(16px,2vw,19px);line-height:1.6}.hero-notes{position:absolute;inset:0;pointer-events:none;z-index:1}.hero-note{position:absolute;width:54px;height:40px;border-radius:4px;opacity:.92;box-shadow:0 8px 24px rgba(0,0,0,.16);transform:rotate(var(--rotate))}.hero-note:after{content:"";position:absolute;left:9px;right:9px;top:12px;height:2px;background:rgba(55,53,47,.24);box-shadow:0 7px rgba(55,53,47,.18),0 14px rgba(55,53,47,.12)}.hero-note:nth-child(1){left:8%;top:24%;background:var(--yellow);--rotate:-7deg}.hero-note:nth-child(2){right:9%;top:18%;background:var(--rose);--rotate:8deg}.hero-note:nth-child(3){left:14%;bottom:18%;background:var(--mint);--rotate:4deg}.hero-note:nth-child(4){right:14%;bottom:16%;background:var(--sky);--rotate:-5deg}.hero-wire{position:absolute;width:110px;border-top:1px dashed rgba(255,255,255,.24);transform:rotate(var(--rotate))}.hero-wire:nth-child(5){left:13%;top:46%;--rotate:21deg}.hero-wire:nth-child(6){right:13%;top:48%;--rotate:-19deg}.hero-actions{display:flex;justify-content:center;align-items:center;gap:14px;margin-top:28px}.hero-cta{display:inline-flex;align-items:center;gap:9px;min-height:44px;padding:10px 16px;border-radius:8px;background:var(--brand);color:#fff;text-decoration:none;font-weight:700;box-shadow:0 8px 26px rgba(86,69,212,.32);transition:background-color .16s ease,transform .16s ease}.hero-cta:hover,.hero-cta:focus-visible{background:var(--brand-pressed);transform:translateY(-1px);outline:2px solid #fff;outline-offset:3px}.hero-count{color:#aeb7cc;font-size:13px}.meta{display:flex;justify-content:center;flex-wrap:wrap;gap:8px;margin-top:22px}.meta span{font:12px/1.4 Consolas,monospace;color:#dce2ef;border:1px solid rgba(255,255,255,.2);border-radius:6px;padding:5px 8px;background:rgba(255,255,255,.04)}.sticky{position:sticky;top:0;z-index:20;background:rgba(255,255,255,.94);border-bottom:1px solid var(--line);backdrop-filter:blur(14px)}nav{max-width:1200px;margin:auto;padding:9px 24px;display:flex;gap:3px;overflow:auto;scrollbar-width:thin}nav a{position:relative;white-space:nowrap;color:var(--muted);text-decoration:none;padding:8px 10px;border-radius:7px;font-size:14px;transition:color .16s ease,background-color .16s ease}nav a:hover,nav a:focus-visible{color:var(--charcoal);background:var(--soft);outline:none}nav a[aria-current="location"]{color:var(--brand);background:#f0edff;font-weight:700}main{max-width:1200px;margin:auto;padding:42px 24px 88px}.card,.module{background:var(--card);border:1px solid var(--line);border-radius:12px}.card{padding:32px;margin-bottom:34px}.card#overview{position:relative;box-shadow:var(--shadow);border-color:rgba(200,196,190,.72)}.card#overview:before{content:"";display:block;height:34px;margin:-32px -32px 28px;border-bottom:1px solid var(--line);border-radius:12px 12px 0 0;background:linear-gradient(90deg,#ff6b65 16px,transparent 16px 29px,#f4bd4f 29px 45px,transparent 45px 58px,#62c554 58px 74px,transparent 74px);background-repeat:no-repeat;background-position:16px 12px;background-size:74px 10px}.card h2,.module h2{margin:6px 0 9px;color:var(--ink);font-size:clamp(25px,3vw,32px);font-weight:740;line-height:1.2;letter-spacing:-.025em}.card p,.module p{color:var(--muted)}.legend{display:flex;gap:20px;flex-wrap:wrap;margin:16px 0;color:var(--steel);font-size:13px}.legend span{display:flex;align-items:center;gap:8px}.line{width:28px;border-top:2px solid var(--brand)}.line.secondary{border-top:2px dashed #9c9992}.diagram{background:var(--soft);border:1px solid var(--line);border-radius:9px;padding:24px;overflow:auto;min-height:160px}.diagram svg{display:block;width:auto;max-width:none;height:auto;margin:auto}.system-diagram{background:#fff}.system-diagram svg{max-width:100%;min-width:min(760px,100%)}.module-index{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px;margin-top:18px}.module-link{--tone:var(--lavender);position:relative;display:grid;grid-template-columns:auto 1fr;gap:4px 11px;min-height:118px;padding:16px;border:1px solid transparent;border-radius:10px;text-decoration:none;color:var(--ink);background:var(--tone);transition:transform .16s ease,border-color .16s ease}.module-link:hover,.module-link:focus-visible{transform:translateY(-2px);border-color:var(--line-strong);outline:none}.module-link-number{grid-row:1/3;color:rgba(55,53,47,.55);font:700 11px/1.5 Consolas,monospace}.module-link strong{align-self:end;font-size:15px;line-height:1.35}.module-link>span:last-child{color:var(--muted);font-size:13px;line-height:1.42}.tone-1{--tone:var(--peach)}.tone-2{--tone:var(--rose)}.tone-3{--tone:var(--mint)}.tone-4{--tone:var(--lavender)}.tone-5{--tone:var(--sky)}.tone-6{--tone:var(--yellow)}.module{position:relative;padding:32px;margin:30px 0;overflow:hidden;scroll-margin-top:74px;box-shadow:none}.module:before{content:"";position:absolute;inset:0 auto 0 0;width:5px;background:var(--tone)}.module-head{display:flex;justify-content:space-between;gap:32px;align-items:flex-start}.module-title{display:flex;gap:15px;max-width:740px}.module-number{display:grid;place-items:center;flex:0 0 42px;height:42px;border-radius:8px;background:var(--tone);color:var(--charcoal);font:750 12px/1 Consolas,monospace}.module-title .kicker{margin-top:1px}.module-head>div:first-child{max-width:760px}.module-head p{margin:0}.evidence{max-width:390px;text-align:right}.evidence>span{display:block;color:var(--steel);font-size:10px;font-weight:800;text-transform:uppercase;letter-spacing:.1em;margin-bottom:6px}.diagram-note{font-size:12px;margin:18px 0 8px}.module-diagram{background:#fff}.node-list{display:grid;gap:8px;margin-top:20px}.node{border:1px solid var(--line);border-radius:9px;background:#fff;scroll-margin-top:80px;transition:border-color .16s ease,background-color .16s ease}.node:hover{border-color:var(--line-strong)}.node[open]{border-color:#bcb4f0;background:#fdfcff;box-shadow:none}summary{cursor:pointer;list-style:none;display:grid;grid-template-columns:auto 1fr auto;gap:12px;align-items:center;min-height:58px;padding:13px 15px}summary::-webkit-details-marker{display:none}summary strong{display:block;color:var(--charcoal);font-size:15px}summary small{display:block;color:var(--muted);font-size:13px;font-weight:400;margin-top:2px}.node-chevron{color:var(--steel);font-size:22px;line-height:1;transition:transform .16s ease}.node[open] .node-chevron{transform:rotate(90deg);color:var(--brand)}.kind{font-size:10px;font-weight:800;text-transform:uppercase;padding:4px 7px;border-radius:6px;color:#3159af;background:#eaf0ff}.kind-llm{color:#7041a5;background:#f1eafe}.kind-tool{color:#14745a;background:#dcf8e9}.kind-store{color:#8a6100;background:#fff3cb}.kind-artifact{color:#086d9e;background:#dff3fd}.kind-output{color:#b4234c;background:#ffe7ee}.node-body{border-top:1px solid var(--line);padding:18px}.node-body>section{margin-top:16px}.io{display:grid;grid-template-columns:1fr 1fr;gap:18px}h5{font-size:11px;text-transform:uppercase;letter-spacing:.08em;color:var(--steel);margin:0 0 8px}.chip{display:inline-block;padding:4px 8px;margin:2px 4px 2px 0;border-radius:6px;background:#f1f0ee;color:var(--charcoal);font-size:12px}.chip.code{font-family:Consolas,monospace}.source{font:12px/1.5 Consolas,monospace;color:var(--link);margin-bottom:7px}.prompt{border-top:1px solid var(--line);padding-top:16px;margin-top:18px}.prompt pre{white-space:pre-wrap;overflow-wrap:anywhere;max-height:420px;overflow:auto;background:var(--deep);color:#e8ebf3;border-radius:8px;padding:17px;font:12px/1.65 Consolas,monospace}.muted{color:#9b9993}.small{font-size:13px}.footer{color:var(--steel);font-size:12px;text-align:center;margin-top:36px}
.system-figure{margin-top:20px}.audience-product .module-index+.system-figure{margin-top:28px}.prompt-spotlight{margin-top:24px;padding-top:22px;border-top:1px solid var(--line)}.prompt-spotlight h3{margin:0 0 12px;color:var(--ink);font-size:17px}.prompt-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px}.prompt-card{min-width:0;padding:15px;border:1px solid #d9d3f6;border-radius:9px;background:#faf8ff}.prompt-card>span{color:var(--brand);font-size:11px;font-weight:750}.prompt-card h4{margin:4px 0 7px;color:var(--ink);font-size:14px}.prompt-card p{display:-webkit-box;overflow:hidden;margin:0;color:var(--charcoal);font-size:13px;line-height:1.55;-webkit-box-orient:vertical;-webkit-line-clamp:5}.detail-deep .prompt-card p{display:block;overflow:visible}.prompt-card .source{margin-top:9px;margin-bottom:0}.technical-layer{margin-top:22px;border-top:1px solid var(--line)}.technical-layer>summary{display:flex;justify-content:space-between;min-height:44px;padding:13px 2px 0;color:var(--link);font-size:13px;font-weight:700}.technical-layer>summary span{font-size:20px;transition:transform .16s ease}.technical-layer[open]>summary span{transform:rotate(90deg)}.technical-layer>.technical-diagram{padding-top:2px}.detail-overview .module{padding-bottom:26px}.detail-overview .module-head{align-items:center}
@media(max-width:1024px){.module-index{grid-template-columns:repeat(2,minmax(0,1fr))}.hero-note:nth-child(3),.hero-note:nth-child(4),.hero-wire{display:none}.module-head{display:block}.evidence{text-align:left;max-width:none;margin-top:18px}}
@media(max-width:760px){.prompt-grid{grid-template-columns:1fr}}
@media(max-width:760px){html{scroll-padding-top:64px}.hero{min-height:360px;padding:56px 20px 64px}.hero h1{font-size:clamp(38px,12vw,56px)}.hero-note{transform:scale(.78) rotate(var(--rotate));opacity:.7}.hero-actions{flex-direction:column;gap:9px}.sticky nav{padding-inline:12px}main{padding:26px 14px 64px}.card,.module{padding:20px}.card#overview:before{margin:-20px -20px 20px}.module-index{grid-template-columns:1fr}.module-link{min-height:96px}.module-title{gap:11px}.module-number{flex-basis:38px;height:38px}.io{grid-template-columns:1fr}.system-diagram svg{min-width:700px}.diagram{padding:16px}.meta span{max-width:100%;overflow:hidden;text-overflow:ellipsis}}
@media(max-width:480px){.hero-note{display:none}.hero p{font-size:15px}.meta{display:none}.card h2,.module h2{font-size:25px}.module{border-radius:10px}summary{grid-template-columns:1fr auto}.kind{grid-column:1/3;justify-self:start}.node-chevron{grid-column:2;grid-row:2}.module-title{align-items:flex-start}}
@media(prefers-reduced-motion:reduce){html{scroll-behavior:auto}.hero-cta,.module-link,.node,.node-chevron{transition:none}}
@media print{.hero{min-height:0;text-align:left}.hero-inner{margin:0}.hero h1,.hero p{margin-left:0}.hero-notes,.hero-actions{display:none}.card#overview{box-shadow:none}.card#overview:before{display:none}.module-index{grid-template-columns:repeat(2,1fr)}nav{display:none}}
</style></head><body class="audience-${presentation.audience} detail-${presentation.detailLevel}" data-audience="${presentation.audience}" data-detail="${presentation.detailLevel}"><header class="hero"><div class="hero-notes" aria-hidden="true"><i class="hero-note"></i><i class="hero-note"></i><i class="hero-note"></i><i class="hero-note"></i><i class="hero-wire"></i><i class="hero-wire"></i></div><div class="hero-inner"><span class="kicker">${c.label}</span><h1>${h(map.system.name)}</h1><p>${h(map.system.summary)}</p><div class="hero-actions"><a class="hero-cta" href="#overview">${c.overview}<span aria-hidden="true">↓</span></a><span class="hero-count">${map.modules.length} ${c.modules}</span></div><div class="meta"><span>${h(profileLabel)}</span><span>${h(map.meta.repository)}</span><span>${h(map.meta.analyzed_revision)}</span><span>${h(map.meta.language)}</span></div></div></header><div class="sticky"><nav aria-label="${h(c.modules)}"><a href="#overview" aria-current="location">${c.overview}</a>${navigation}</nav></div><main><section class="card" id="overview"><span class="kicker">${c.overview}</span><h2>${c.architecture}</h2><p>${c.diagramHelp}</p>${overviewBody}</section>${modulesHtml.join("")}<p class="footer">${c.generated} · IR ${h(map.meta.schema_version)}</p></main><noscript>${c.renderError}JavaScript disabled</noscript>
<script type="application/json" id="system-map-data">${safeMap}</script><script type="application/json" id="diagram-data">${safeDiagrams}</script><script type="module">
const reposition=()=>{const id=decodeURIComponent(location.hash.slice(1));if(!id)return;const target=document.getElementById(id);if(target?.tagName==='DETAILS')target.open=true;target?.scrollIntoView({block:'start',behavior:'instant'});};
const navLinks=[...document.querySelectorAll('nav a[href^="#"]')];
const setActive=(id)=>{for(const link of navLinks){if(link.getAttribute('href')==='#'+id)link.setAttribute('aria-current','location');else link.removeAttribute('aria-current');}};
for(const link of navLinks)link.addEventListener('click',()=>setActive(link.getAttribute('href').slice(1)));
if('IntersectionObserver' in window){const observer=new IntersectionObserver((entries)=>{const visible=entries.filter((entry)=>entry.isIntersecting).sort((a,b)=>b.intersectionRatio-a.intersectionRatio)[0];if(visible)setActive(visible.target.id);},{rootMargin:'-18% 0px -68% 0px',threshold:[0,.1,.5]});for(const section of document.querySelectorAll('#overview,article.module'))observer.observe(section);}
try{const vizModule=await import("data:text/javascript;base64,${vizBase64}");const viz=await vizModule.instance();const sources=JSON.parse(document.getElementById("diagram-data").textContent);for(const target of document.querySelectorAll("[data-diagram]")){target.innerHTML=viz.renderString(sources[target.dataset.diagram],{format:"svg",engine:"dot"});}reposition();setTimeout(reposition,250);addEventListener("hashchange",reposition);}catch(error){for(const target of document.querySelectorAll("[data-diagram]")){target.innerHTML='<span class="muted">${c.renderError}'+String(error)+'</span>';}}
</script></body></html>`;
}

function chips(values, className = "") {
  if (!values?.length) return '<span class="muted">—</span>';
  return values.map((value) => `<span class="chip ${className}">${h(value)}</span>`).join("");
}

function parseArgs(argv) {
  const [command, ...rest] = argv;
  const positional = [];
  let repo = null;
  let json = false;
  for (let index = 0; index < rest.length; index += 1) {
    const arg = rest[index];
    if (arg === "--json") json = true;
    else if (arg === "--repo") {
      repo = rest[index + 1] ?? null;
      index += 1;
    } else if (arg.startsWith("--")) throw new Error(`Unknown option: ${arg}`);
    else positional.push(arg);
  }
  return { command, positional, repo, json };
}

function report(result, asJson) {
  if (asJson) {
    const printable = { ...result };
    delete printable.map;
    process.stdout.write(`${JSON.stringify(printable, null, 2)}\n`);
    return;
  }
  process.stdout.write(`${result.ok ? "OK" : "FAILED"}: ${result.command}\n`);
  if (result.output) process.stdout.write(`Output: ${result.output}\n`);
  if (result.checks) for (const check of result.checks) process.stdout.write(`- ${check.ok ? "OK" : "FAIL"} ${check.name}: ${check.detail}\n`);
  for (const item of result.diagnostics ?? []) process.stdout.write(`- [${item.severity}] ${item.code} ${item.subject}: ${JSON.stringify(item.evidence)}\n`);
}

function loadCandidate(path) {
  const absolute = resolve(path);
  let text;
  try {
    text = readFileSync(absolute, "utf8");
  } catch (error) {
    return { absolute, error: diagnostic("CANDIDATE_UNREADABLE", "/candidate", { path: absolute, message: error.message }, ["replace_candidate_path"]) };
  }
  try {
    return { absolute, value: JSON.parse(text) };
  } catch (error) {
    return { absolute, error: diagnostic("JSON_PARSE_FAILED", "/candidate", { path: absolute, message: error.message }, ["repair_json_syntax"]) };
  }
}

function doctor() {
  const checks = [];
  const major = Number.parseInt(process.versions.node.split(".")[0], 10);
  checks.push({ name: "node", ok: major >= 18, detail: process.version });
  for (const [name, path] of [
    ["schema", SCHEMA_PATH],
    ["viz", VIZ_PATH],
    ["viz-license", VIZ_LICENSE_PATH],
    ["graphviz-license", GRAPHVIZ_LICENSE_PATH],
    ["expat-license", EXPAT_LICENSE_PATH],
  ]) {
    try {
      const stat = statSync(path);
      checks.push({ name, ok: stat.isFile() && stat.size > 0, detail: `${path} (${stat.size} bytes)` });
    } catch (error) {
      checks.push({ name, ok: false, detail: `${path}: ${error.message}` });
    }
  }
  try {
    JSON.parse(readFileSync(SCHEMA_PATH, "utf8"));
    checks.push({ name: "schema-json", ok: true, detail: "valid JSON" });
  } catch (error) {
    checks.push({ name: "schema-json", ok: false, detail: error.message });
  }
  const diagnostics = checks.filter((check) => !check.ok).map((check) => diagnostic("DOCTOR_CHECK_FAILED", `/checks/${check.name}`, { detail: check.detail }, ["repair_installation"]));
  return { ok: diagnostics.length === 0, command: "doctor", version: VERSION, checks, diagnostics };
}

function validateCommand(candidatePath, repoPath) {
  const loaded = loadCandidate(candidatePath);
  const resolvedRepo = resolve(repoPath);
  const diagnostics = loaded.error ? [loaded.error] : validateMap(loaded.value, resolvedRepo);
  const errors = diagnostics.filter((item) => item.severity === "error").length;
  const warnings = diagnostics.length - errors;
  return { ok: errors === 0, command: "validate", candidate: loaded.absolute, repository: resolvedRepo, summary: { errors, warnings }, diagnostics, map: loaded.value };
}

function deliverCommand(candidatePath, outputPath, repoPath) {
  const validation = validateCommand(candidatePath, repoPath);
  const absoluteOutput = resolve(outputPath);
  if (!validation.ok) return { ...validation, command: "deliver", output: absoluteOutput, delivered: false };
  if (absoluteOutput === validation.candidate) {
    const item = diagnostic("OUTPUT_COLLIDES_WITH_CANDIDATE", "/output", { path: absoluteOutput }, ["choose_different_output"]);
    return { ...validation, ok: false, command: "deliver", output: absoluteOutput, delivered: false, summary: { errors: 1, warnings: validation.summary.warnings }, diagnostics: [...validation.diagnostics, item] };
  }
  let html;
  try {
    const vizBytes = readFileSync(VIZ_PATH);
    if (vizBytes.length === 0) throw new Error("Viz.js asset is empty");
    html = renderHtml(validation.map, vizBytes);
    if (!html.startsWith("<!doctype html>") || !html.includes('id="system-map-data"')) throw new Error("Renderer produced an incomplete document");
  } catch (error) {
    const item = diagnostic("HTML_RENDER_FAILED", "/output", { path: absoluteOutput, message: error.message }, ["repair_renderer", "repair_installation"]);
    return { ...validation, ok: false, command: "deliver", output: absoluteOutput, delivered: false, summary: { errors: 1, warnings: validation.summary.warnings }, diagnostics: [...validation.diagnostics, item] };
  }
  const outputDirectory = dirname(absoluteOutput);
  const temporary = resolve(outputDirectory, `.${process.pid}-${Date.now()}-${Math.random().toString(16).slice(2)}.system-map.tmp`);
  let fd;
  try {
    mkdirSync(outputDirectory, { recursive: true });
    fd = openSync(temporary, "wx", 0o600);
    writeFileSync(fd, html, "utf8");
    fsyncSync(fd);
    closeSync(fd);
    fd = undefined;
    renameSync(temporary, absoluteOutput);
  } catch (error) {
    if (fd !== undefined) {
      try { closeSync(fd); } catch {}
    }
    try { rmSync(temporary, { force: true }); } catch {}
    const item = diagnostic("OUTPUT_REPLACE_FAILED", "/output", { path: absoluteOutput, message: error.message }, ["close_output_file", "choose_writable_output", "retry_delivery"]);
    return { ...validation, ok: false, command: "deliver", output: absoluteOutput, delivered: false, summary: { errors: 1, warnings: validation.summary.warnings }, diagnostics: [...validation.diagnostics, item] };
  }
  return { ...validation, command: "deliver", output: absoluteOutput, delivered: true, bytes: Buffer.byteLength(html), map: undefined };
}

function usage() {
  return "Usage:\n  node scripts/system-map.mjs doctor [--json]\n  node scripts/system-map.mjs validate <candidate.json> --repo <path> [--json]\n  node scripts/system-map.mjs deliver <candidate.json> <output.html> --repo <path> [--json]\n";
}

let exitCode = 0;
try {
  const args = parseArgs(process.argv.slice(2));
  let result;
  if (args.command === "doctor" && args.positional.length === 0 && !args.repo) result = doctor();
  else if (args.command === "validate" && args.positional.length === 1 && args.repo) result = validateCommand(args.positional[0], args.repo);
  else if (args.command === "deliver" && args.positional.length === 2 && args.repo) result = deliverCommand(args.positional[0], args.positional[1], args.repo);
  else {
    process.stderr.write(usage());
    process.exitCode = 2;
    result = null;
  }
  if (result) {
    report(result, args.json);
    if (!result.ok) exitCode = 1;
  }
} catch (error) {
  const asJson = process.argv.includes("--json");
  const result = { ok: false, command: "cli", summary: { errors: 1, warnings: 0 }, diagnostics: [diagnostic("CLI_ARGUMENT_INVALID", "/arguments", { message: error.message }, ["fix_command_arguments"])] };
  report(result, asJson);
  exitCode = 2;
}
process.exitCode = exitCode || process.exitCode;
