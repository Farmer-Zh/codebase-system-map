# Third-party notices

Codebase System Map is MIT-licensed. The generated standalone HTML documents
also contain a vendored copy of `@viz-js/viz`, whose distribution header names
Graphviz and Expat as software included in object-code form.

## Code-intelligence integration

### Codebase Memory

- Project: <https://github.com/DeusData/codebase-memory-mcp>
- Role: documented reference provider for repository indexing, architecture,
  structural search, execution-path tracing, and bounded source retrieval.
- License: MIT.
- Distribution: installed separately and accessed through its Agent Skill or
  MCP interface.

## Components bundled into generated HTML

### Viz.js 3.29.0

- Project: <https://github.com/mdaines/viz-js>
- Role: JavaScript API and WebAssembly runtime used to turn DOT diagrams into
  SVG in the reader's browser.
- License: MIT.
- Local license text: `codebase-system-map/assets/licenses/VIZ_JS_LICENSE.txt`.

### Graphviz

- Project: <https://graphviz.org/>
- Source: <https://gitlab.com/graphviz/graphviz>
- Role: graph layout and SVG generation compiled into the Viz.js WebAssembly
  distribution.
- License: Eclipse Public License 2.0.
- Local license text: `codebase-system-map/assets/licenses/GRAPHVIZ_LICENSE.txt`.

### Expat

- Project: <https://libexpat.github.io/>
- Source: <https://github.com/libexpat/libexpat>
- Role: XML parser included transitively in the Viz.js object-code
  distribution.
- License: MIT.
- Local license text: `codebase-system-map/assets/licenses/EXPAT_LICENSE.txt`.

## Project platform

- Node.js 18+ and its built-in modules run deterministic validation and
  delivery.
- The GitHub Pages site is implemented in plain HTML, CSS, and JavaScript.

This file is informational and does not replace the license texts shipped with
the relevant components.
