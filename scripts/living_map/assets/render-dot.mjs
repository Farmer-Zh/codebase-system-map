import { readFile, writeFile } from "node:fs/promises";
// Viz.js is bundled beside this adapter so an installed wheel does not depend
// on a repository-local node_modules directory.
import { instance } from "./viz.js";

const [, , inputPath, outputPath] = process.argv;
if (!inputPath || !outputPath) {
  throw new Error("Usage: node render-dot.mjs <input.json> <output.json>");
}

const diagrams = JSON.parse(await readFile(inputPath, "utf8"));
const viz = await instance();
const rendered = {};

for (const [id, dot] of Object.entries(diagrams)) {
  rendered[id] = viz.renderString(dot, { format: "svg", engine: "dot" });
}

await writeFile(outputPath, JSON.stringify(rendered), "utf8");
