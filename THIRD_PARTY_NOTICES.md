# Third-party notices

Codebase System Map is MIT-licensed. The generated standalone HTML documents
also contain a vendored copy of `@viz-js/viz`, whose distribution header names
Graphviz and Expat as software included in object-code form.

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

## Not runtime dependencies

- Node.js 18+ is the execution platform for deterministic validation and
  delivery; only built-in modules are used.
- The GitHub Pages site is plain HTML, CSS, and JavaScript and loads no UI
  framework, remote font, CDN asset, or analytics library.
- Huey, Full Stack FastAPI Template, and OpenAI Agents SDK are public source
  repositories analyzed for the showcases. Their code is not bundled as a
  dependency.
- “Notion-inspired” describes a visual direction only. This project is not
  affiliated with Notion and does not use Notion code or assets.

This file is informational and does not replace the license texts shipped with
the relevant components.
