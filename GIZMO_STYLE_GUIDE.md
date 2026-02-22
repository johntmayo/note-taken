# Geocoder Tool Style Guide

- **Overall vibe:** stripped-back civic utility — brutalist print aesthetic, no decorative flourishes. Feels like a well-designed government form: structured, trustworthy, no-nonsense.
- **Shape language:** zero border-radius throughout. Everything is square. This is the defining formal decision.

## Colors

- **Backgrounds**
  - `#FDFBF7` paper — page background
  - `#FFFFFF` card — the main container surface
  - `#F0F4F8` cool-paper — instruction/callout panel background
- **Text**
  - `#1F2937` ink — primary text and all borders
  - `#4B5563` ink-secondary — helper text, captions
  - `#314059` navy — headings (h1, h3) and table headers
- **Accents**
  - `#F59E0B` gold — primary action button fill
  - `#BC5838` clay — secondary/download button fill (white text on clay)
- **Status fills (paired with matching borders)**
  - `#FEF3C7` / `#F59E0B` — processing state
  - `#ECFDF5` / `#283618` — success/complete state
  - `#FEF2F2` / `#BC5838` — error state
- **Borders**
  - `#1F2937` strong border — container, buttons, table
  - `#E5E7EB` light border — input fields, table cell dividers, section divider hr

## Typography

- **Display/UI font:** `Chivo` (700–900) — headings, labels, button text, table headers. All uppercase labels use `letter-spacing: 0.05em`.
- **Body/content font:** `Merriweather` (400–700) — body copy, instructions, input values, table data, status messages.
- **Label style:** Chivo 700, `font-size: 13px`, `text-transform: uppercase`, `letter-spacing: 0.05em`. Labels sit above their inputs with no decorative elements.

## Layout

- Single centered column, `max-width: 900px`, `margin: 50px auto`, `padding: 20px`.
- One primary card container fills the column: `padding: 32px`, 2px solid border, hard shadow.
- Sections are separated by a thin `border-top: 2px solid #E5E7EB` hr — no extra margin drama.

## Shadows & Interaction

- **Resting shadow:** `4px 4px 0 #1F2937` on buttons; `6px 6px 0 #1F2937` on the main container.
- **Hover:** `transform: translate(-2px, -2px)` + shadow grows to `6px 6px 0` on buttons — simulates physical press-lift. Transition is fast: `0.1s ease`.
- **Disabled:** shadow and transform removed; fill becomes `#E5E7EB`, text becomes `#4B5563`, cursor is `not-allowed`.
- **Focus (inputs):** border color shifts from `#E5E7EB` to `#314059` navy. No glow or ring — just the border swap.

## Component Patterns

- **Callout/instructions block:** `border-left: 4px solid #314059` on a `#F0F4F8` background, `padding: 16px`. No rounded corners.
- **Status bar:** full-width block, 2px solid border matching the state color, flat background tint. Hidden (`display: none`) until triggered; shown via class swap (`processing`, `complete`, `error`).
- **Table:** `border-collapse: collapse`, 2px outer border in ink, 1px inner cell borders in light border. Header row is navy fill with white Chivo text. Even rows stripe with paper background.
- **Preview/code areas:** paper background, 2px light border, Merriweather 12px.

## Rules to Keep

- Never use `border-radius` — not even `2px`. Squareness is load-bearing.
- Use only the two fonts: Chivo for structure, Merriweather for reading. No mixing within a single element type.
- Gold is the one primary CTA. Clay is for download/export/secondary actions. Do not use either as a decorative color.
- Status states are conveyed by background + border color pairs only — no icons required (emoji checkmarks in status text are fine, icons in the UI are not).
- Keep the offset shadow on the container. It is the single piece of "designed-ness" in an otherwise utilitarian layout — do not flatten it.
