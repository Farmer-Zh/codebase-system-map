---
name: Codebase System Map — Notion-inspired
source: https://github.com/VoltAgent/awesome-design-md/tree/main/design-md/notion
status: adopted
---

# Design direction

The generated HTML is an audience-shaped architecture document, not a fixed
engineering dashboard. It uses the Notion design analysis selected through
awesome-design-skill as a visual system, while preserving offline delivery,
source evidence, graph readability, and print support.

This is an independent visual adaptation. It is not an official Notion design
system and does not ship Notion assets or remote fonts.

## Product principles

1. Content comes first. Decoration must clarify hierarchy or orientation.
2. The system overview behaves like a workspace mockup emerging from a dark
   hero band.
3. Modules read as calm document sections, not dense dashboard widgets.
4. Pastel colors distinguish responsibilities; purple is reserved for the
   primary navigation action and active state.
5. Information priority follows the selected audience; prompts and source
   evidence are not permanently assigned the same visual weight.

## Presentation profiles

- Product views place module responsibilities and prompt-bearing behavior
  before implementation topology. Module pipelines use progressive disclosure.
- Technical views place runtime topology, state, interfaces, and source
  evidence before prompt spotlights.
- Mixed views balance both reading paths.
- Overview detail omits module diagrams and node lists from the primary
  document. Standard detail keeps nodes collapsed. Deep detail expands them.

## Tokens

### Color

- Primary: #5645d4
- Primary pressed: #4534b3
- Link blue: #0075de
- Hero navy: #0a1530
- Hero navy deep: #070f24
- Canvas: #ffffff
- Surface: #f6f5f4
- Surface soft: #fafaf9
- Hairline: #e5e3df
- Hairline strong: #c8c4be
- Ink: #1a1a1a
- Charcoal: #37352f
- Secondary text: #5d5b54
- Tertiary text: #787671
- Lavender: #e6e0f5
- Peach: #ffe8d4
- Rose: #fde0ec
- Mint: #d9f3e1
- Sky: #dcecfa
- Yellow: #fef7d6

### Typography

Use the offline system stack:

Notion Sans, -apple-system, BlinkMacSystemFont, Segoe UI, Microsoft YaHei,
Helvetica, Arial, sans-serif.

- Hero: 40–72px, weight 600, line-height 1.05
- Section heading: 28–36px, weight 600
- Card heading: 18–22px, weight 600
- Body: 16px, weight 400, line-height 1.55
- Supporting text: 14px, line-height 1.5
- Caption: 11–13px, weight 500–600

### Geometry and spacing

- Base spacing unit: 4px; common steps: 8, 12, 16, 24, 32, 48, 64
- Controls: 8px radius
- Cards: 12px radius
- Large overview surface: 16px radius
- Badges only: full pill radius
- Maximum content width: 1280px with 32px desktop gutters
- Default cards use borders, not heavy shadows
- The system overview alone may use a deep diffuse mockup shadow

## Component mapping

### Hero band

Use deep navy, centered content, a single purple rectangular action, and a few
small pastel note shapes connected by restrained wire lines. Do not use a
repeating decorative pattern.

### System overview

Treat the overview as the workspace mockup card: white canvas, strong but
diffuse elevation, and generous padding. Product views place the semantic
module index before the graph; technical views place the graph first.

### Module index

Use a responsive pastel feature-card grid. Every card carries a two-digit
sequence number, module name, and one-sentence responsibility.

### Module document

Use a white, flat document card with one pastel accent. Technical graphs remain
full width. Product views place them in a clearly labelled disclosure control.
Show heading evidence only when the profile requests technical or source depth.

### Node accordion

Use sober rectangular geometry, a visible chevron, 44px minimum target height,
and a 150–200ms transition. Expanded state uses a purple border but no heavy
shadow.

### Prompt and evidence

Source paths use blue links or neutral code chips. Prompt spotlights use a soft
lavender document surface; exact node-level excerpts use the deep navy code
surface. Purple must not be used for ordinary body text.

## Interaction

- Highlight the current overview or module in the sticky navigation.
- Preserve URL fragments for direct module and node links.
- Use 160ms ease-out transitions for cards, chevrons, and navigation.
- Respect prefers-reduced-motion.
- Do not add autoplay, parallax, floating particles, or decorative animation.

## Responsive behavior

- Below 1024px: reduce hero type and overview spacing.
- Below 760px: use one-column module cards and input/output sections.
- Navigation remains horizontally scrollable with 44px touch targets.
- Diagrams may scroll horizontally rather than becoming unreadably small.
- Print removes navigation and decoration, expands node details, and preserves
  page-break boundaries.

## Quality gate

- One standalone HTML file; no CDN, external fonts, images, or server.
- System and module diagrams remain readable at 1280px and 390px widths.
- Text contrast remains accessible on every pastel surface.
- All keyboard focus states are visible.
- Decorative shapes are hidden from assistive technology.
- The result must feel calmer and easier to scan than the previous interface,
  not merely more colorful.
