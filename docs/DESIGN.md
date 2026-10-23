# DeepTrace AI — Design Specification

| Field | Value |
|---|---|
| Document | `docs/DESIGN.md` |
| Version | 1.0.0 — draft for owner review |
| Owner | Iqra Nawaz |
| Date | 2026-10-23 |
| PRD baseline | `PRD.md` v1.1.0 |
| Design direction | **Chart Room** (approved) |
| Palette | **Deep Sea Abyss** (approved, unchanged) |
| Status | `planned` — nothing in this document has been implemented or verified in code |

> **How to read this document.** Requirement IDs (`FR-`, `NFR-`, `UX-`, `SEC-`, `ERR-`, `AC-`) come from `PRD.md` and are never redefined here. Every feature carries a milestone tag (M0–M4, V1, Future). A feature tagged for a later milestone **must not appear as available** in an earlier one (§2.5). Contrast ratios in §4 were computed on 2026-10-23 with the WCAG 2.x relative-luminance formula; they are design-time calculations and are **not** an accessibility-compliance claim (§13.10).

---

## Table of Contents

1. Purpose, Scope and PRD Traceability
2. Design Principles and Evidence Trust Model
3. Visual Identity and Design Tokens
4. Color Contrast and Approved Pairings
5. Typography, Spacing, Radius, Elevation and Motion
6. Application Shell and Responsive Layout
7. Navigation Structure and Routes
8. Detailed Screen Specifications
9. Research Workspace Interaction Model
10. Evidence and Citation Interaction Model
11. Reusable Component Library
12. Component Variants and State Matrix
13. Accessibility Requirements
14. Content and Microcopy Guidelines
15. Responsive Behavior and Breakpoints
16. Frontend Implementation Handoff
17. Design Acceptance Criteria
18. PRD Traceability Matrix
19. Open Questions and Deferred Decisions
20. Future Design Enhancements

---

## 1. Purpose, Scope and PRD Traceability

### 1.1 Purpose

This document is the visual and interaction contract for the DeepTrace AI browser interface. It fulfils the PRD's requirement that detailed tokens, typography and spacing live in `DESIGN.md` (UX-01, D-02) and gives frontend developers enough precision to build screens without guessing.

### 1.2 In scope

- Design tokens, typography, spacing, radius, elevation and motion.
- Application shell, navigation, routes and responsive behavior (360 px and up, UX-10).
- Ten screens plus the First-Run Setup Wizard and the Evidence Drawer.
- A reusable component library with states.
- Accessibility targets (NFR-A1–A5, UX-11), content/microcopy rules and acceptance criteria.

### 1.3 Out of scope

Production code, API contracts (`API.md`), data schema (`DATABASE.md`), prompts (`PROMPTS.md`), provider selection (`INTEGRATIONS.md`, OQ-01/OQ-02), final package versions and routing library (deferred to `ARCHITECTURE.md`, D-04). Native mobile apps are a PRD non-goal (§7.3); "mobile" in this document means a responsive browser layout.

### 1.4 Fixed inputs (not reopened)

The five brand colors, the supporting colors, the Chart Room direction, the Sounding Line, the three typefaces, the radii, Lucide icons and Radix primitives are approved and are reproduced here as-is. Derived values (hover/pressed states, tints) are flagged as **derived** in §3 and are the only new color values this document introduces.

### 1.5 Relationship to other documents

| Concern | Authoritative document |
|---|---|
| Product behavior and requirement IDs | `PRD.md` |
| Visual and interaction behavior | This document |
| Request/response shapes, claim structure | `API.md` (not yet written) |
| Prompt and output schemas | `PROMPTS.md` (not yet written) |

When this document and the PRD conflict, the PRD wins and this document must be corrected through the PRD change rule (§23 of the PRD).

---

## 2. Design Principles and Evidence Trust Model

### 2.1 Product stance

DeepTrace AI is **not a chatbot**. It is a document-first investigation workspace. The research answer is the primary object; everything else (plan, sources, activity, budget, evidence details) supports it and stays one interaction away.

### 2.2 Design principles

| # | Principle | Practical consequence |
|---|---|---|
| P1 | **Evidence before eloquence** | Every factual claim shows its citations or an explicit "Not established" marker. Prose is never styled to look more certain than its evidence. |
| P2 | **Checked is not true** | The UI separates what the software *checked* (reference exists, quote matches) from what an AI *judged* (semantic support). Neither is presented as proof of truth. |
| P3 | **Calm confidence** | No celebratory effects, neon glows, gradients, confetti or "success" theatre. Quiet surfaces, precise labels. |
| P4 | **One dominant thing** | On every screen exactly one region is visually dominant (the answer, the report, the list). Secondary content is collapsible. |
| P5 | **Honest states** | Paused, interrupted, failed, cancelled, budget-reached and partial results are designed as first-class states, never hidden behind a generic "Done" (UX-07, FR-11.3). |
| P6 | **Never promise what is not built** | Milestone-gated features are absent or explicitly marked "not available in this version" (§2.5). |
| P7 | **Never color alone** | Every status uses text plus an icon plus color (UX-05, NFR-A4). |
| P8 | **Local-first, not offline** | Copy says "stored on this computer"; it never says "private" or "offline" without qualification, because queries and fetches leave the device (PRD §1, SEC-03). |
| P9 | **Every error is actionable** | Each error states what failed, what was saved, and how to proceed (PRD §17). |
| P10 | **Restraint in motion** | Motion explains state change; it never decorates (§5.6). |

### 2.3 Evidence trust model

The interface has exactly **three evidence layers**, always shown in this order and visually separated.

| Layer | Nature | Who decides | Possible outcomes | Source requirement |
|---|---|---|---|---|
| **A. Automatic checks** | Deterministic, programmatic | Application code | Passed / Failed / Not applicable | FR-06.2, FR-06.3 |
| **B. Automated assessment** | Fallible AI judgment (M3) | A model, with stored method and model ID | Supported / Uncertain / Contested / Unsupported | FR-06.4 |
| **C. User review** | Human override (M3, Should) | The user | Corrected stance / excluded passage, original label preserved | FR-09.4 |

**Layer A checks (M1+):**

| Check | Pass copy | Fail copy |
|---|---|---|
| Reference exists | "Passage found in saved sources" | "Passage not found" |
| Belongs to this investigation | "Belongs to this investigation" | "Not part of this investigation" |
| Quotation matches stored passage | "Quotation matches saved text" (with note "after whitespace/Unicode normalization" when normalization was applied, FR-06.3) | "Quotation differs from saved text" |

A failed Layer A check results in the citation being suppressed and the claim marked as not established (ERR-11); the failed reference is never rendered as a working link.

**Layer B rules:**

- Always introduced by the kicker **"Automated assessment"** and the sentence "An AI model judged this. It may be wrong."
- Always shows the method and model ID (from FR-06.4 storage) in the Evidence Drawer.
- Never shown as a percentage, score, star rating or "confidence" (FR-06.7).
- A syntactically valid citation never implies Layer B support (FR-06.4).
- Not rendered at all before M3 (§2.5).

**Banned framing** (also in §14.4): "verified", "fact-checked", "guaranteed", "truth verified", "completely reliable", "high/medium/low confidence", "100% accurate".

### 2.4 Color semantics for evidence

| Meaning | Color token | Hex | Icon (Lucide) | Text label |
|---|---|---|---|---|
| Supported (automated, M3) | Light Aqua | `#AEEEEE` | `circle-check` | Supported |
| Uncertain (automated, M3) | Warning/Amber | `#FFC857` | `circle-help` | Uncertain |
| Contested (automated, M3) | Contested/Violet | `#C9A7FF` | `scale` | Contested |
| Unsupported (automated, M3) | Danger/Coral | `#FF8A8A` | `circle-slash` | Unsupported |
| Not established (M1 rule-based: no valid citation) | Danger/Coral, dashed outline | `#FF8A8A` | `circle-dashed` | Not established |
| Check passed (Layer A) | Success | `#4ADE9F` | `shield-check` | Passed |
| Check failed (Layer A) | Danger | `#FF8A8A` | `shield-alert` | Failed |

**Light Aqua has two jobs and they must not be confused:** (1) it is the *Supported* color, always accompanied by the word "Supported"; (2) it is the signature accent for the Sounding Line, highlighted excerpts and focus rings, where it signals **linkage and attention, not a verdict**. A Sounding Line next to a claim means "this claim is traceable to these passages". It does not mean "this claim is correct". The first-use help popover (§10.9) states this.

> Icon names are Lucide identifiers as of this writing. Frontend must confirm each exists in the pinned Lucide version and substitute the closest equivalent without changing meaning.

### 2.5 Milestone gating rules

| Capability | M1 | M2 | M3 | M4 |
|---|---|---|---|---|
| Layer A deterministic checks | Yes | Yes (adds PDF page) | Yes | Yes |
| "Not established" claim marker | Yes | Yes | Yes | Yes |
| Layer B labels (Supported/Uncertain/Contested/Unsupported) | **Hidden** | **Hidden** | Yes | Yes |
| Drawer note "Semantic assessment is not performed in this version" | Yes | Yes | Removed | Removed |
| PDF citations and page references | No | Yes | Yes | Yes |
| Documents screen | No | Yes | Yes (+ library Should) | Yes |
| Evidence Compare route | Not in nav | Not in nav | Yes (if Should promoted) | Yes |
| Plan editing / approval mode (FR-02b) | No | Partial (M2–M3) | Yes | Yes |
| Resume of interrupted runs (FR-L2/L3) | **No** | No | Yes | Yes |
| Source credibility signals (FR-10) | No | No | Yes (Should) | Yes |
| Cancel run (FR-11.4) | Yes | Yes | Yes | Yes |

Rules:

1. **No dead controls.** A control that depends on an unbuilt feature is not rendered. It is not shown disabled either, unless a disabled state with an explanation teaches the user something true (for example "Resume is not available in this version" on an Interrupted investigation).
2. Settings screens never list planned features as toggles.
3. When a feature is promoted or shipped, its removal of the "not available" note is part of that milestone's definition of done.

---

## 3. Visual Identity and Design Tokens

### 3.1 Brand palette — Deep Sea Abyss (mandatory, unchanged)

| Token | Name | Hex | Role |
|---|---|---|---|
| `--dt-deep-navy` | Deep Navy | `#001F3F` | Main application background |
| `--dt-ocean-navy` | Ocean Navy | `#003366` | Sidebar, cards, panels, drawers |
| `--dt-ocean-blue` | Ocean Blue | `#005B96` | Selected navigation, supporting surfaces |
| `--dt-electric-blue` | Electric Blue | `#007BFF` | Interactive accents, progress indicators (non-text) |
| `--dt-light-aqua` | Light Aqua | `#AEEEEE` | Evidence highlights, Sounding Line, focus ring, "Supported" |

### 3.2 Approved supporting colors

| Token | Hex | Role |
|---|---|---|
| `--dt-text-primary` | `#F2F6FA` | Primary text |
| `--dt-text-secondary` | `#A9BBD0` | Secondary text |
| `--dt-text-muted` | `#8FA6C0` | Muted text, timestamps, helper text |
| `--dt-surface-sunken` | `#00152B` | Inputs, code/passages wells, deepest layer |
| `--dt-surface-raised` | `#0A3D70` | Hover surfaces, popovers, menus |
| `--dt-border-subtle` | `#1B4B7C` | Decorative dividers only |
| `--dt-border-strong` | `#6F93BD` | Input boundaries, interactive component outlines |
| `--dt-button-primary` | `#0066D9` | Primary button fill |
| `--dt-button-primary-hover` | `#005BC4` | Primary button hover |
| `--dt-button-primary-pressed` | `#0050AD` | Primary button pressed |
| `--dt-link` | `#5AA9FF` | Text links |
| `--dt-success` | `#4ADE9F` | Check passed, completed |
| `--dt-warning` | `#FFC857` | Uncertain, caution banners |
| `--dt-danger` | `#FF8A8A` | Failed, not established, destructive |
| `--dt-contested` | `#C9A7FF` | Contested evidence |

Primary text on the primary button is `#FFFFFF` (5.38:1; see §4). The button uses `#0066D9` rather than Electric Blue because white on `#007BFF` would not meet 4.5:1.

### 3.3 Derived values (introduced by this document)

Derived values are computed from approved colors, introduce no new hue, and exist only to specify states and tints that the approved list does not cover. The owner may veto any of them without affecting the brand palette.

| Token | Value | Derivation | Used for |
|---|---|---|---|
| `--dt-button-primary-text` | `#FFFFFF` | Pure white | Text on primary button |
| `--dt-danger-hover` | `#FF7373` | Danger lightness shift | Destructive button hover |
| `--dt-danger-pressed` | `#FF5C5C` | Danger lightness shift | Destructive button pressed |
| `--dt-scrim` | `rgba(0, 21, 43, 0.72)` | Sunken at 72% | Modal/drawer backdrop |
| `--dt-tint-aqua` | `#AEEEEE` at 14% | Status tint | Supported chip background |
| `--dt-tint-warning` | `#FFC857` at 14% | Status tint | Uncertain chip background |
| `--dt-tint-contested` | `#C9A7FF` at 14% | Status tint | Contested chip background |
| `--dt-tint-danger` | `#FF8A8A` at 14% | Status tint | Unsupported / error background |
| `--dt-tint-electric` | `#007BFF` at 18% | Status tint | Running / Planning badge background |
| `--dt-tint-success` | `#4ADE9F` at 14% | Status tint | Passed / completed background |
| `--dt-highlight` | `#AEEEEE` at 22% | Passage highlight | Highlighted excerpt background |
| `--dt-sounding-rest` | `#AEEEEE` at 35% | Sounding Line | Resting line |
| `--dt-sounding-active` | `#AEEEEE` at 100% | Sounding Line | Active/hover/focus line |

Tints are specified as alpha over the surface they sit on, so the same token works over Deep Navy and Ocean Navy. Computed contrast for each is in §4.4.

### 3.4 Semantic tokens

Components consume **semantic** tokens, never raw palette tokens. This keeps a later light theme (V1) a token swap.

| Semantic token | Maps to |
|---|---|
| `--bg-app` | Deep Navy |
| `--bg-surface` | Ocean Navy |
| `--bg-sunken` | Surface Sunken |
| `--bg-raised` | Surface Raised |
| `--bg-selected` | Ocean Blue |
| `--bg-scrim` | Scrim |
| `--text-default` | Text Primary |
| `--text-secondary` | Text Secondary |
| `--text-muted` | Text Muted |
| `--text-link` | Link |
| `--text-on-primary` | `#FFFFFF` |
| `--border-decor` | Border Subtle |
| `--border-control` | Border Strong |
| `--accent-interactive` | Electric Blue |
| `--accent-evidence` | Light Aqua |
| `--focus-ring` | Light Aqua |
| `--status-success / warning / danger / contested` | respective colors |

### 3.5 Surface hierarchy

| Level | Token | Used for |
|---|---|---|
| L0 — Sunken | `--bg-sunken` `#00152B` | Text inputs, passage wells, code blocks, skeleton base |
| L1 — App | `--bg-app` `#001F3F` | Page background, reading canvas |
| L2 — Surface | `--bg-surface` `#003366` | Sidebar, cards, panels, drawer, modal |
| L3 — Raised | `--bg-raised` `#0A3D70` | Hover state of L2 rows, menus, popovers, tooltips |
| Selected | `--bg-selected` `#005B96` | Selected nav item, selected row (with indicator) |

Adjacent surface steps are low-contrast by design (1.15–1.76:1, §4.3). **Surfaces are therefore never the only boundary for an interactive control**; controls carry a Strong border (§4.3).

### 3.6 Signature element — the Sounding Line

A 2 px vertical Light Aqua rule that physically links a claim, its citation chips and the evidence passage.

| Property | Value |
|---|---|
| Width | 2 px, `border-radius: 1px` |
| Position | Left gutter of a claim block (8 px gap to text); left edge of the highlighted passage in the Evidence Drawer |
| Rest (claim has ≥ 1 valid citation) | `--dt-sounding-rest` (aqua 35%) |
| Hover / focus-within on claim, or its chip is active | `--dt-sounding-active` (aqua 100%) |
| Active claim (its drawer is open) | Aqua 100% on both the claim and the passage in the drawer, plus `--dt-highlight` background on the cited excerpt |
| Claim with no valid citation | **No aqua line.** A 2 px **dashed** `--status-danger` line plus the "Not established" label |
| Animation | None required. Optional 120 ms opacity transition on state change; none under reduced motion (§5.6) |
| Forbidden | Glow, blur, gradient, pulse, travelling-dot animation, thickness over 2 px |

On wide desktop with the drawer docked, the claim and passage are visually aligned by identical line treatment, not by a drawn connector. A drawn connector is an optional later enhancement (§20).

---

## 4. Color Contrast and Approved Pairings

### 4.1 Method and thresholds

Ratios use the WCAG 2.x formula `(L1 + 0.05) / (L2 + 0.05)` with sRGB relative luminance. Thresholds follow NFR-A2: normal text ≥ 4.5:1; large text (≥ 24 px, or ≥ 18.66 px bold) and meaningful non-text component boundaries/graphics ≥ 3:1. Values are rounded to two decimals. These are design-time calculations; automated and manual verification is required under AC-17 (§13.10).

### 4.2 Text on surfaces

| Foreground | Deep Navy `#001F3F` | Ocean Navy `#003366` | Ocean Blue `#005B96` | Sunken `#00152B` | Raised `#0A3D70` |
|---|---|---|---|---|---|
| Text Primary `#F2F6FA` | 15.25 ✅ | 11.61 ✅ | 6.58 ✅ | 16.93 ✅ | 10.10 ✅ |
| Text Secondary `#A9BBD0` | 8.44 ✅ | 6.43 ✅ | **3.65 ❌** | 9.37 ✅ | 5.59 ✅ |
| Text Muted `#8FA6C0` | 6.61 ✅ | 5.03 ✅ | **2.85 ❌** | 7.34 ✅ | **4.38 ❌** |
| Link `#5AA9FF` | 6.75 ✅ | 5.14 ✅ | **2.91 ❌** | 7.49 ✅ | **4.47 ❌** |
| Light Aqua `#AEEEEE` | 12.83 ✅ | 9.77 ✅ | 5.54 ✅ | 14.24 ✅ | 8.50 ✅ |
| Success `#4ADE9F` | 9.65 ✅ | 7.35 ✅ | **4.17 ❌** | 10.72 ✅ | 6.39 ✅ |
| Warning `#FFC857` | 10.77 ✅ | 8.20 ✅ | 4.65 ✅ | 11.95 ✅ | 7.13 ✅ |
| Danger `#FF8A8A` | 7.30 ✅ | 5.56 ✅ | **3.15 ❌** | 8.10 ✅ | 4.83 ✅ |
| Contested `#C9A7FF` | 8.25 ✅ | 6.28 ✅ | **3.56 ❌** | 9.15 ✅ | 5.46 ✅ |
| Electric Blue `#007BFF` (as text) | 4.16 ❌ | 3.17 ❌ | 1.80 ❌ | 4.62 ✅ | 2.76 ❌ |

### 4.3 Mandatory usage rules derived from §4.2

| # | Rule |
|---|---|
| C1 | **Selected navigation (Ocean Blue)** contains Text Primary (6.58) and white icons only. No Secondary, Muted, Link, Success, Danger or Contested text may sit on Ocean Blue. |
| C2 | **Muted text and Link text are never placed on Raised** (4.38 and 4.47 fall just short). On hovered rows/menus (Raised) secondary text uses Text Secondary (5.59) and links use Light Aqua (8.50) or underline in Text Primary. |
| C3 | **Electric Blue is never used for text.** It is used for non-text indicators: progress fill, active phase marker, switch "on" track, selected-row marker. It meets 3:1 on Deep Navy (4.16), Sunken (4.62) and Ocean Navy (3.17) but **not** on Raised (2.76) or Ocean Blue (1.80); do not place it there. |
| C4 | **Border Subtle (`#1B4B7C`) is decorative only** (1.41:1 on Ocean Navy, 1.85:1 on Deep Navy). It may draw dividers and card outlines but never the boundary of an input, checkbox, radio, switch, select or secondary button. |
| C5 | **Interactive control boundaries use Border Strong (`#6F93BD`):** 3.95 on Ocean Navy, 5.19 on Deep Navy, 5.76 on Sunken, 3.44 on Raised. All ≥ 3:1. |
| C6 | **Surface steps are not boundaries.** Deep→Ocean Navy is 1.31:1; Ocean Navy→Raised is 1.15:1; Ocean Navy→Ocean Blue is 1.76:1. Never rely on surface color alone to delimit an interactive element. |
| C7 | **Text inside tinted chips, banners and highlights uses Text Primary or the status color itself** (see §4.4). Muted text is never placed on a tint. Secondary text on tints is allowed only where §4.4 shows ≥ 4.5. |
| C8 | Status colors on Ocean Blue are forbidden (see C1). Status chips sit on Deep Navy, Ocean Navy or Sunken only. |

### 4.4 Tints and highlights

Tints are the status color at 14% over the surface (highlight: aqua at 22%).

| Tint over Ocean Navy | Resulting bg | Status-color text | Primary text | Secondary text |
|---|---|---|---|---|
| Aqua (Supported) | `#184D79` | 6.84 ✅ | 8.14 ✅ | 4.50 (borderline — do not use) |
| Warning (Uncertain) | `#244864` | 6.24 ✅ | 8.85 ✅ | 4.90 ✅ |
| Contested | `#1C437B` | 4.89 ✅ | 9.04 ✅ | 5.01 ✅ |
| Danger (Unsupported / error) | `#243F6B` | 4.63 ✅ | 9.68 ✅ | 5.36 ✅ |
| Success (Passed) | `#0A4B6E` | 5.45 ✅ | 8.62 ✅ | — |
| Highlight (aqua 22%) | `#265C84` | — | 6.56 ✅ | — |
| Electric Blue 18% (Running / Planning) | `#004082` | (marker is non-text) | 9.41 ✅ | — |

| Tint over Deep Navy | Resulting bg | Status-color text | Primary text |
|---|---|---|---|
| Aqua | `#183C58` | 8.91 ✅ | 10.59 ✅ |
| Warning | `#243742` | 8.03 ✅ | 11.37 ✅ |
| Contested | `#1C325A` | 6.32 ✅ | 11.70 ✅ |
| Danger | `#242E4A` | 5.91 ✅ | 12.36 ✅ |
| Success | `#0A3A4C` | 7.11 ✅ | 11.23 ✅ |
| Highlight over Sunken (aqua 18%) | `#1F3C4E` | — | 10.66 ✅ |
| Electric Blue 18% | `#003062` | (marker is non-text) | 12.09 ✅ |

- **Highlighted excerpt text is Text Primary**, never dark text: Deep Navy text on the highlight is only 2.32:1.
- Muted on the aqua tint is 3.53 and Muted on the danger tint is 4.20: both fail, hence rule C7.

### 4.5 Buttons

| Button | Fill | Text | Ratio | Notes |
|---|---|---|---|---|
| Primary default | `#0066D9` | `#FFFFFF` | 5.38 ✅ | |
| Primary hover | `#005BC4` | `#FFFFFF` | 6.38 ✅ | |
| Primary pressed | `#0050AD` | `#FFFFFF` | 7.63 ✅ | |
| Primary (alt text) | `#0066D9` | `#F2F6FA` | 4.96 ✅ | Acceptable but white is specified |
| Destructive default | `#FF8A8A` | `#001F3F` | 7.30 ✅ | Dark text on coral |
| Destructive hover | `#FF7373` | `#001F3F` | 6.27 ✅ | Derived |
| Destructive pressed | `#FF5C5C` | `#001F3F` | 5.47 ✅ | Derived; white on `#FF5C5C` would be 3.03 ❌ |
| Secondary | transparent | `#F2F6FA` | ≥ 10 ✅ | Border Strong boundary |
| Ghost / link-style | transparent | `#5AA9FF` | 5.14 on Ocean Navy ✅ | Underline on hover |

Primary button fill vs Ocean Navy is 2.34:1 and vs Deep Navy 3.08:1. A filled button with a text label is identifiable without relying on its boundary (WCAG 1.4.11 does not require a boundary where the label identifies the control), but the Primary button carries a 1 px `#F2F6FA` at 24% inner border to reinforce the edge on Ocean Navy. This inner border is cosmetic and not relied on for compliance.

### 4.6 Focus indicator

| Property | Value |
|---|---|
| Style | `outline: 2px solid #AEEEEE; outline-offset: 2px` |
| Contrast vs adjacent surfaces | Deep Navy 12.83, Ocean Navy 9.77, Sunken 14.24, Raised 8.50, Ocean Blue 5.54 — all ≥ 3:1 |
| Placement | The 2 px offset gap means the ring is measured against the **surrounding surface**, not the control's own fill. This matters for coral destructive buttons (ring on coral would be 1.76:1) and Primary buttons (4.17). Never use an inset-only ring on those controls. |
| Clipped containers | Where `overflow: hidden` would clip an outer ring, use `outline-offset: -2px` and add a 1 px Deep Navy inner stroke; never on destructive buttons (restructure the container instead). |
| Forbidden | `outline: none` without an equal replacement; focus visible only on hover; rings lighter than 3:1 against surroundings |

### 4.7 Forbidden pairings (quick reference)

| Forbidden | Reason | Use instead |
|---|---|---|
| Muted / Link on Raised | 4.38 / 4.47 | Secondary / Light Aqua |
| Secondary, Muted, Link, status text on Ocean Blue | 3.65 / 2.85 / 2.91 / ≤ 4.17 | Text Primary |
| Electric Blue as text | 4.16 / 3.17 | Link `#5AA9FF` |
| Border Subtle as control boundary | 1.41 | Border Strong |
| Dark text on highlight | 2.32 | Text Primary |
| White text on destructive coral | < 3 | Deep Navy text |
| Aqua-only meaning (no label) | NFR-A4 | Aqua + text + icon |

---

## 5. Typography, Spacing, Radius, Elevation and Motion

### 5.1 Typefaces (self-hosted)

| Role | Family | Weights | Notes |
|---|---|---|---|
| Interface, labels, navigation, tables, forms | **IBM Plex Sans** | 400, 500, 600 | UI default |
| Research answers, reports, passage text | **Source Serif 4** | 400, 600; italic 400 | Variable font preferred; italic needed for emphasis and quoted terms |
| Passage IDs, URLs, hashes, model IDs, counters | **IBM Plex Mono** | 400, 500 | Technical text only |

Delivery rules (frontend must follow; no code supplied here):

1. Self-host `woff2` files from the application's own origin; **no third-party font CDN** (consistent with SEC-02 and local-first positioning).
2. Subset to Latin plus Latin Extended initially; non-Latin scripts fall back to system fonts (ERR-16).
3. `font-display: swap` for UI fonts; preload IBM Plex Sans 400/500 only.
4. Fallback stacks: Sans → `system-ui, "Segoe UI", sans-serif` (Windows-first, NFR-C1); Serif → `Georgia, "Times New Roman", serif`; Mono → `ui-monospace, "Cascadia Mono", Consolas, monospace`.
5. All three families are open-licensed (SIL OFL); include license files in the font directory. Confirm at implementation.

### 5.2 Type scale

Sizes in px at 100% browser zoom; implement in `rem` (1 rem = 16 px) so user font-size preferences and 200% zoom work.

**Interface scale (IBM Plex Sans):**

| Token | Size / line-height | Weight | Use |
|---|---|---|---|
| `ui-caption` | 12 / 16 | 500 | Badges, chip text, table meta |
| `ui-label` | 13 / 20 | 500 | Form labels, tab labels, small buttons |
| `ui-body` | 14 / 20 | 400 | Default UI text, table cells |
| `ui-body-lg` | 16 / 24 | 400 | Descriptions, inputs on mobile (prevents iOS zoom), banners |
| `ui-h4` | 18 / 28 | 600 | Card titles, panel titles |
| `ui-h3` | 20 / 28 | 600 | Section titles |
| `ui-h2` | 24 / 32 | 600 | Page titles |
| `ui-h1` | 28 / 36 | 600 | Wizard / empty-state hero only |

**Reading scale (Source Serif 4):**

| Token | Size / line-height | Weight | Use |
|---|---|---|---|
| `read-body` | 18 / 30 (mobile 17 / 28) | 400 | Answer and report body |
| `read-lead` | 20 / 32 | 400 | Answer summary sentence |
| `read-h1` | 28 / 36 | 600 | Report title |
| `read-h2` | 22 / 30 | 600 | Report section headings |
| `read-h3` | 19 / 28 | 600 | Report sub-headings |
| `read-passage` | 16 / 26 | 400 | Source passage text in drawer, preserved verbatim |
| `read-quote` | 18 / 30 italic | 400 | Quotation inside answer (also wrapped in quotation marks) |

**Technical scale (IBM Plex Mono):**

| Token | Size / line-height | Weight | Use |
|---|---|---|---|
| `mono-xs` | 12 / 16 | 500 | Citation chip number, passage ID badges |
| `mono-sm` | 13 / 20 | 400 | URLs, model IDs, hashes |

Rules:

- Reading column measure: 60–75 characters; the answer column is capped at `max-width: 720px` (about 66 characters at 18 px).
- Body text is left-aligned, never justified; no letter-spacing changes except `0.02em` on uppercase captions.
- Uppercase is used only for `ui-caption` kickers (for example "AUTOMATED ASSESSMENT"), never for status words.
- Passage text (`read-passage`) is rendered exactly as stored; no smart-quote or whitespace "prettifying", so that quote-fidelity checks and what the user sees agree (FR-06.3).
- Numerals in tables and budget meters use tabular figures (`font-variant-numeric: tabular-nums`).

### 5.3 Spacing — 4 px scale

| Token | px | Typical use |
|---|---|---|
| `space-0` | 0 | |
| `space-1` | 4 | Icon–text gap, chip inner vertical |
| `space-2` | 8 | Tight stacks, chip gaps, Sounding Line gap |
| `space-3` | 12 | Form field internal padding (vertical) |
| `space-4` | 16 | Card padding (compact), mobile page margin |
| `space-5` | 20 | |
| `space-6` | 24 | Card padding (default), desktop page margin, section gap |
| `space-8` | 32 | Between major sections |
| `space-10` | 40 | |
| `space-12` | 48 | Empty-state vertical padding |
| `space-16` | 64 | Page top spacing for wizard/hero |

Only multiples of 4 are permitted. Tailwind's default spacing scale already equals this scale; no custom spacing tokens are needed beyond naming.

**Layout constants:**

| Constant | Value |
|---|---|
| Header height | 56 px (mobile), 64 px (tablet/desktop) |
| Investigation tab bar height | 44 px |
| Sidebar expanded | 240 px |
| Sidebar collapsed (icon rail) | 64 px |
| Secondary panel (docked) | 320 px |
| Evidence panel (docked) | 400 px |
| Evidence drawer (overlay, tablet/desktop) | `min(440px, 100vw - 48px)` |
| Answer column max width | 720 px |
| Page content max width | 1200 px, left-aligned within the main region |
| Page margin | 16 px (mobile), 24 px (≥ 768) |
| Minimum control height | 40 px desktop; 44 px for touch (below 768) |
| Minimum hit target | 24 × 24 px absolute floor (WCAG 2.5.8); 32 px preferred, 44 px on touch |

### 5.4 Border radius

| Element | Radius |
|---|---|
| Chips, badges, citation chips, tags | 4 px |
| Buttons, inputs, selects, textareas, tabs' focus shape | 6 px |
| Cards, panels, tables container, banners | 10 px |
| Drawers, modals, popovers, mobile sheet (top corners) | 14 px |
| Docked evidence panel | 0 (part of layout, left border only) |
| Mobile full-height evidence sheet | 0 when at full height; 14 px top corners while animating in |
| Avatars/progress markers | 50% (circle) |

### 5.5 Elevation

Elevation is communicated by **surface color and border**, not shadow.

| Layer | Treatment |
|---|---|
| Page, cards, sidebar | No shadow. Card: Ocean Navy fill, `1px solid --border-decor`. |
| Hover / menu / popover / tooltip | Raised fill, 1 px Border Subtle, shadow `0 4px 12px rgba(0, 10, 25, 0.40)` |
| Overlay drawer / modal | Ocean Navy fill, 1 px Border Strong, shadow `0 12px 32px rgba(0, 10, 25, 0.55)`, scrim behind |
| Docked drawer | No shadow; 1 px Border Subtle left border |
| Sticky header | No shadow; 1 px Border Subtle bottom border |

**Z-index scale:** content 0 · sticky header and tab bar 20 · docked evidence panel 20 · scrim 40 · overlay drawer / modal / mobile nav 50 · popover/tooltip 55 · toast 60.

### 5.6 Motion

| Token | Value | Use |
|---|---|---|
| `motion-fast` | 120 ms, `ease-out` | Hover, color, opacity, Sounding Line state |
| `motion-base` | 200 ms, `cubic-bezier(0.2, 0, 0, 1)` | Drawer slide, accordion, toast enter |
| `motion-slow` | 320 ms | Not used in MVP |

Allowed: opacity and color fades; 16 px drawer/sheet translate; accordion height; a single rotating spinner for an active phase.
Forbidden: bounce, parallax, shimmer on the answer, typewriter effect on claims, pulsing glows, auto-scrolling the user's reading position, motion that conveys meaning without a text alternative.

**Reduced motion (`prefers-reduced-motion: reduce`, NFR-A5, UX-11):**

| Normal behavior | Reduced-motion behavior |
|---|---|
| Drawer/sheet slides | Appears instantly (opacity only, ≤ 80 ms or none) |
| Accordion height animation | Instant |
| Active-phase spinner rotating | Static `loader` icon plus the words "In progress" |
| Skeleton shimmer | Static skeleton blocks, no animation |
| Progress meter fill transition | Instant width change |
| Toast slide | Instant |
| Sounding Line transition | Instant |

A reduced-motion user must lose **no information**; every animated state has a textual equivalent.

**Live update cadence.** Progress, source counts and budget values update at most once per second visually (UX-03) to avoid flicker; screen-reader announcements follow §13.6.

---

## 6. Application Shell and Responsive Layout

### 6.1 Shell anatomy

```
┌────────────┬──────────────────────────────────────────────────────────┐
│            │  Contextual header (breadcrumb · title · status · actions) │
│  Sidebar   ├──────────────────────────────────────────────────────────┤
│ (Ocean     │  Investigation tabs (Workspace · Sources · [Compare] · Report)
│  Navy)     ├───────────────────────────────┬──────────────┬───────────┤
│            │  Primary content workspace    │ Secondary    │ Evidence  │
│ Dashboard  │  (reading column ≤ 720 px)    │ panel (opt.) │ panel     │
│ Documents* │                               │ 320 px       │ (docked)  │
│ Settings   │                               │              │ 400 px    │
└────────────┴───────────────────────────────┴──────────────┴───────────┘
* Documents appears from M2.   Compare tab appears from M3 (if promoted).
```

| Region | Specification |
|---|---|
| **Sidebar** | Ocean Navy surface. Wordmark/tagline "Research you can trace." at top (tagline hidden in rail). Global navigation list. Collapse toggle at bottom. Collapsed state persisted locally. Selected item: Ocean Blue fill, Text Primary label, 3 px Light Aqua left indicator, `aria-current="page"`. Hover: Raised fill. |
| **Contextual header** | On global screens: page title + primary action. On investigation screens: breadcrumb (`Dashboard › Investigation title`), title (truncated with tooltip), status badge, run actions (Cancel while running). Sticky. |
| **Investigation tabs** | Rendered as a `<nav>` of links (see §7.3) directly below the header; sticky beneath it. Selected tab has a 2 px Light Aqua underline plus Text Primary label; unselected use Text Secondary. |
| **Primary content workspace** | Deep Navy canvas. The answer or report sits in a reading column capped at 720 px, left-aligned with a 24 px gutter (centered only on wide viewports ≥ 1600 px). |
| **Secondary information panel** | Optional; holds Plan, Sources, Activity, Budget (Radix Tabs). Docked on the right when space allows, an inline accordion otherwise (§6.3). |
| **Evidence drawer** | Opened by citation chips. Docked panel on wide desktop, overlay drawer on tablet and narrow desktop, full-height sheet on mobile (§6.3, §10). |
| **Toast region** | Bottom-right (desktop) / bottom-center (mobile), above content, `role="status"`; max 3 stacked. |
| **Banner region** | Between header/tabs and content; used for offline (ERR-15), storage warning (NFR-X1), budget reached, interrupted run. One banner per concern, dismissible only if non-critical. |

### 6.2 Landmarks

`header` (banner), `nav` (sidebar, labeled "Main"), `nav` (investigation tabs, labeled "Investigation"), `main` (one per page), `aside` (secondary panel, labeled "Investigation details"), `aside` (docked evidence panel, labeled "Evidence"), `footer` not used in-app. A "Skip to main content" link is the first focusable element and becomes visible on focus.

### 6.3 Layout by breakpoint

| Breakpoint | Range | Sidebar | Primary | Secondary panel | Evidence |
|---|---|---|---|---|---|
| **Mobile** | 360–767 px | Hidden; top bar with menu button opens navigation dialog | Single column, 16 px margins | Collapsible accordion sections under the tracker | Full-height sheet (modal) |
| **Tablet** | 768–1023 px | 64 px icon rail (labels in tooltips and `aria-label`) | Fluid reading column ≤ 720 px | Collapsible accordion sections, or right column only if width allows ≥ 560 px for primary | Overlay drawer (modal) |
| **Desktop** | 1024–1279 px | 240 px expanded (user may collapse to 64 px) | Fluid, ≥ 560 px | Inline accordion by default; docked 320 px column **only** when the sidebar is collapsed to the 64 px rail | Overlay drawer (modal) |
| **Wide desktop** | ≥ 1280 px | 240 px expanded | 560–760 px reading column | Docked 320 px column when evidence is closed | Docked 400 px panel; it **replaces** the docked secondary panel while open and the secondary panel returns on close |

Width arithmetic (to prove the design fits): at 1280 px with a 240 px sidebar and a 400 px docked evidence panel the primary region is 640 px (≥ 560 ✅). At 1024 px with a 240 px sidebar the primary region is 784 px; adding a 320 px secondary column would leave 464 px (< 560 ❌), hence the inline accordion rule. With the 64 px rail at 1024 px the primary region is 960 px, and a 320 px secondary column leaves 640 px ✅.

**No document-level horizontal overflow** at any width ≥ 360 px (UX-10). Tables, code, long URLs and Markdown tables scroll inside their own `overflow-x: auto` container, with `min-width: 0` on flex/grid children and `overflow-wrap: anywhere` on URLs and passage IDs.

### 6.4 Sidebar collapse behavior

- Toggle is a button with `aria-expanded` and an accessible name ("Collapse sidebar" / "Expand sidebar").
- Collapsed state persists per browser in local storage (a UI preference, not research data).
- Tablet defaults to collapsed; desktop defaults to expanded; the user's stored preference wins within the breakpoint's allowed states.
- Rail items show a Radix Tooltip on hover and keyboard focus; tooltips never contain the only copy of information.

### 6.5 Mobile navigation dialog

Menu button (44 × 44 px) in a 56 px top bar opens a Radix Dialog from the left: Ocean Navy panel, 85% width, max 320 px; contains the same navigation list, a "Close" button, focus trapped, `Esc` closes, focus returns to the menu button, background inert. Route change closes the dialog.

---

## 7. Navigation Structure and Routes

### 7.1 Global navigation

| Item | Icon | Route | Milestone | Notes |
|---|---|---|---|---|
| Dashboard | `layout-dashboard` | `/` | M1 (M0 shell) | Home |
| Documents | `files` | `/documents` | **M2** | Not rendered before M2 |
| Settings | `settings` | `/settings` | M0 shell, M1 functional | |

A primary **New investigation** button sits at the top of the sidebar content area (and in the Dashboard header), route `/new`. The wordmark links to `/`.

### 7.2 Investigation navigation

| Tab | Route | Milestone | Notes |
|---|---|---|---|
| Workspace | `/investigations/:id` | M1 | Default tab |
| Sources | `/investigations/:id/sources` | M1 | |
| Evidence Compare | `/investigations/:id/compare` | **M3 (Should)** | Only rendered if FR-09 is included; hidden for investigations with no stance data |
| Report | `/investigations/:id/report` | M1 | |

Research Plan is a **panel inside the Workspace**, not a route.

### 7.3 Tab semantics

Investigation tabs are **navigation links**, not ARIA `tablist` tabs, because each destination is a different URL: render `<nav aria-label="Investigation">` containing links with `aria-current="page"` on the active link. The in-page secondary panel (Plan / Sources / Activity / Budget) **is** a true tabs widget (Radix Tabs) with roving focus and arrow-key navigation.

### 7.4 Route table

| Route | Screen | Milestone | Notes |
|---|---|---|---|
| `/` | Dashboard | M1 | |
| `/new` | New Investigation | M1 | Redirects to workspace after creation |
| `/investigations/:id` | Research Workspace | M1 | Evidence drawer addressed by `?evidence=<passageId>` |
| `/investigations/:id/sources` | Sources Explorer | M1 | |
| `/investigations/:id/compare` | Evidence Comparison | M3 | |
| `/investigations/:id/report` | Report Viewer | M1 | `?version=<n>` selects a version |
| `/documents` | Document Library | M2 | |
| `/settings` | Settings | M1 | `#section` anchors per section |
| `/setup` | First-Run Setup Wizard | M1 (disclosure/credentials needed by M1 run) | Auto-redirect on first launch; reopenable from Settings |
| `*` | Not-found page | M1 | "This page doesn't exist" + link to Dashboard |

- The **Evidence Drawer is not a route**. Its open state is mirrored in the `evidence` query parameter so a refresh or a shared local link restores it; closing removes the parameter. If the passage cannot be resolved (for example removed), the drawer opens in its "Source removed / not found" state (§8.6).
- Routing library, route guards and URL helpers are deferred to `ARCHITECTURE.md` (D-04); this table is the contract the router must satisfy.
- **First-run guard:** if provider disclosure has not been acknowledged or no credentials exist, `/new` and "Start research" lead to `/setup` (UX-08). Browsing saved investigations is never blocked.
- **Unsaved input:** `/new` and Settings forms warn before navigating away with unsaved changes.
- Document `<title>` pattern: `{Page} — {Investigation title} — DeepTrace AI`; route changes move focus to the page `h1` and announce the new title through the polite live region.

---

## 8. Detailed Screen Specifications

Each screen lists: purpose, layout, components, actions, navigation, states (interaction, loading, error, empty), responsive behavior, accessibility, PRD IDs and milestone.

### 8.0 Shared definitions

#### 8.0.1 Investigation status badge

Badge = icon + text + tinted background (§4.4), 12 px caption, 4 px radius. Text is always shown (never icon-only, except in the 64 px rail where no badge appears).

| Status (PRD §11.2) | Badge text | Icon | Color | Available in |
|---|---|---|---|---|
| Draft | Draft | `file-pen` | Secondary text / no tint, Border Strong outline | M1 |
| Planning | Planning | `loader` (spins; static under reduced motion) | Electric Blue marker, Primary text | M1 |
| Awaiting approval | Ready to start (M1) / Awaiting approval (when FR-02b approval mode ships) | `hourglass` | Warning | M1 |
| Running | Running | `loader` | Electric Blue marker, Primary text | M1 |
| Completed | Completed | `circle-check` | Success | M1 |
| Paused | Paused | `circle-pause` | Warning | See §9.6 |
| Interrupted | Interrupted | `unplug` | Warning | M1 (state display) |
| Failed | Failed | `circle-x` | Danger | M1 |
| Cancelled | Cancelled | `ban` | Secondary text, Border Strong outline | M1 |
| Budget reached | Budget reached | `gauge` | Warning | M1 |
| Archived | Archived | `archive` | Muted text (on Deep Navy/Ocean Navy only) | M1 |

"Completed" means normal successful completion only; **no other status may use the word "Done", "Finished" or "Complete"** (FR-11.3, PRD §11.2). The Awaiting approval label in M1 reads "Ready to start" because M1 uses explicit Start confirmation (FR-02b.2); this label choice is flagged in §19 (DQ-04).

#### 8.0.2 Source status badge (FR-03.4, FR-W6)

| Status | Icon | Color | Meaning shown to user |
|---|---|---|---|
| fetched | `circle-check` | Success | Text saved |
| partial | `circle-dashed` | Warning | Only part of the page could be read (for example JavaScript-dependent, FR-W5) |
| blocked | `shield-off` | Danger | Site refused access; nothing saved |
| paywalled | `lock` | Danger | Behind a paywall; nothing saved; DeepTrace does not bypass access controls |
| failed | `circle-x` | Danger | Could not retrieve (DNS, timeout, error); reason shown |
| duplicate | `copy` | Secondary / outline | Same content as another source; link to the original |
| unsupported | `file-x` | Secondary / outline | Content type not supported |

#### 8.0.3 Extraction-quality badge (FR-04.4, FR-D4)

`good` (`circle-check`, Success), `degraded` (`triangle-alert`, Warning — "Tables, columns or footnotes may not be read exactly"), `unusable` (`circle-x`, Danger — "Text could not be reliably extracted"). Reason shown when available.

#### 8.0.4 Common state patterns

| State | Pattern |
|---|---|
| Loading (list/page) | Skeleton blocks matching final layout; `aria-busy="true"` on the region; no spinner-only screens. Skeleton appears only after 200 ms to avoid flashes; if data arrives sooner, none is shown. |
| Loading (action) | Button shows `loader` icon + "Working…" label, stays the same width, is `aria-disabled` (not removed from tab order) |
| Empty | Centered block in the region: 48 px icon (Secondary text), `ui-h3` title, one-sentence explanation, one primary action |
| Error (region) | Danger-tinted banner inside the region: icon, what failed, what was saved, next action (PRD §17). Retry button only where a retry is safe (ERR-01, ERR-02) |
| Error (field) | Message under field, `aria-describedby`, `aria-invalid="true"`, icon + text |
| Offline (ERR-15) | Persistent Warning banner "You're offline. You can browse saved investigations. Searching and AI steps need an internet connection." Network-dependent buttons are `aria-disabled` with that reason in their description. |
| Partial results | Banner + the content that exists; never hidden because part failed (FR-W10) |

---

### 8.1 Dashboard

| | |
|---|---|
| **Purpose** | Start research; list, reopen, and manage investigations; see status and history at a glance. |
| **Route / milestone** | `/` · M1 (filtering M3 Should) |
| **PRD IDs** | FR-01.2, FR-01.3, FR-01.5, FR-08.1, FR-08.2, FR-08.4, FR-11.3, UX-07, NFR-P1, NFR-X1, ERR-15, AC-01 |

**Layout (desktop):** page title "Investigations" + primary "New investigation" button (right). Optional banners (storage, offline). Below: filter bar (M3), then the investigation list as a **table** (≥ 768 px) or **cards** (< 768 px).

**Table columns (FR-08.1):** Title (link, 2-line clamp) · Status (badge) · Last updated (relative + absolute on hover/`title` and `<time datetime>`) · Sources (count) · Actions (menu). Row hover = Raised fill; row is not itself clickable except via the title link (avoids nested interactive conflicts), but the whole row's hit area extends via a stretched link pseudo-element on the title.

**Card layout (mobile):** title, status badge, "Updated 2 h ago · 7 sources", actions menu button.

**Actions per row:** Open (default), Rename, Archive/Unarchive, Delete (FR-01.3). **Resume** is not offered in M1 (FR-L2); Interrupted rows show badge + "Open to review saved evidence". Row actions live in a Radix DropdownMenu labeled "Actions for {title}".

**Delete:** Radix AlertDialog (§8.9a pattern below). Body: "This permanently removes this investigation's sources, passages, answers and reports from this computer. Backups, exports and provider-side copies outside DeepTrace aren't affected." Buttons: Cancel (default focus) / "Delete investigation" (destructive). After confirm: progress state; on partial failure show what could not be removed and why (FR-01.4, SEC-23). Never claim success until verified.

**Filtering (M3, Should, FR-08.4):** search-by-title input, status select, date range select; filter state reflected in the URL query; "Clear filters". Not rendered in M1.

**States**

| State | Behavior |
|---|---|
| Loading | 6 skeleton rows |
| Empty (no investigations) | Icon `search`, "No investigations yet", "Ask a question and DeepTrace will search, read and cite sources.", Primary "New investigation" |
| Empty (filtered, M3) | "No investigations match these filters" + "Clear filters" |
| Error (cannot load) | Danger banner: "Couldn't load your investigations. Nothing has been deleted. Reload the list." + Retry |
| Storage warning (NFR-X1) | Warning banner when an investigation exceeds the configured threshold (~500 MB): "'{title}' is using {size}. You can remove sources or delete it to free space." |
| Offline | Offline banner; list works |
| Interrupted rows | Badge "Interrupted"; tooltip text "The app closed while this was running. Saved evidence is kept." |

**Performance:** must stay responsive with 200 investigations (NFR-P1, proposed ≤ 1.5 s p90 on documented reference hardware). Render up to 200 rows without pagination; above that, paginate 50 per page (assumption, §19 DQ-12). Use `content-visibility: auto` on rows if profiling requires.

**Responsive:** table → cards below 768 px; page actions wrap; no horizontal overflow.
**Accessibility:** table uses real `<table>`, `<caption class="sr-only">Investigations</caption>`, sortable headers (M3) as buttons with `aria-sort`; row action menus keyboard-accessible; status always text+icon.

---

### 8.2 New Investigation

| | |
|---|---|
| **Purpose** | Capture the question and bound the run before any external call is made. |
| **Route / milestone** | `/new` · M1 |
| **PRD IDs** | FR-01.1, FR-02.2, FR-11.1, FR-11.5, SEC-03, UX-08, UX-09, ERR-03 |

**Layout:** single centered form card (max 720 px) on Deep Navy; page title "New investigation".

**Fields**

| Field | Control | Rules |
|---|---|---|
| Title | Text input | Required; max 120 characters (assumption, DQ-05); defaults to the first 60 characters of the question, editable |
| Research question | Textarea (min 4 rows, auto-grow to 12) | Required; **10–1,000 characters** (FR-01.1); live counter "{n} / 1,000" in `mono-sm`; counter is `aria-live="off"`, announced on error only; helper text "Ask something specific. Narrow questions get shorter plans." |
| Sources | M1: read-only line "Web search" with info icon; M2: checkbox "Include my documents" + document picker (links to `/documents`, up to ten PDFs per investigation, SEC-15) | PDF option absent in M1 |
| Run limits | Collapsed disclosure "Run limits" (Radix Collapsible) with the five FR-11.1 values (steps 25, searches 20, pages 15, tokens 400,000, time 20 min) as number inputs, each showing its **hard maximum** ("Max 50") and a "Reset to defaults" link | Values cannot exceed hard maximums; text says "These are ceilings, not targets." Hard-maximum values are set in configuration (DQ-06) |
| Plan approval | Switch "Review the plan before research starts" | **Not rendered in M1** (M1 always shows the plan with an explicit Start button, FR-02b.2); appears when FR-02b ships (default on) |

**Data-flow disclosure (always visible, above the submit button; SEC-03, FR-11.5):**
A bordered note: icon `send`, "What leaves this computer when you start" — lists the configured providers by role (for example "Search provider: your question's search queries"; "AI model provider: your question and selected source excerpts"), each with a link to Settings → Data disclosure. Cost line only if trustworthy pricing is configured ("Estimated cost: up to about $X — estimate"), otherwise "Cost estimate unavailable. Usage is limited by the run limits above." (FR-11.5).

**Actions:** primary **Create and plan** (creates the investigation → state `Planning` → navigates to workspace); secondary **Cancel** (to Dashboard; confirm if fields are dirty).

**Flow:** Create → workspace shows Planning → plan appears in the Plan panel with budgets (FR-02.2) → user clicks **Start research** (explicit confirmation) → Running. Nothing external except the planning model call occurs before Start; this is stated in the disclosure.

**States**

| State | Behavior |
|---|---|
| Validation error | Inline per field plus an error summary at the top (`role="alert"`) listing fields as links that focus the field; focus moves to the summary on failed submit |
| Missing credentials (ERR-03) | Warning banner "Connect an AI model and a search provider to start." with button to `/setup` or Settings; submit remains enabled to save a Draft, but "Create and plan" is `aria-disabled` with that reason |
| Submitting | Button loading state; fields read-only |
| Creation failed (ERR-14) | Danger banner: "Couldn't save the investigation. Nothing was started. Your text is still here." Form values preserved |
| Offline | Offline banner; "Create and plan" `aria-disabled` — user may save as Draft |

**Responsive:** full-width card at < 768 px, 16 px margins; inputs 16 px font to avoid mobile zoom; sticky bottom action bar on mobile (safe-area padding).
**Accessibility:** `<form>` with labelled controls; counter tied via `aria-describedby`; disclosure is real text, not an icon-only tooltip.

---

### 8.3 Research Workspace

The most important screen. Full interaction model in §9; this section is the screen contract.

| | |
|---|---|
| **Purpose** | Run, observe and read a bounded investigation; inspect evidence behind each claim. |
| **Route / milestone** | `/investigations/:id` · M1 (Resume, semantic labels, credibility signals later) |
| **PRD IDs** | FR-01.5, FR-02.2, FR-06.1–06.7, FR-11.1–11.5, FR-L1–L5, UX-03–07, UX-10, ERR-01–07, ERR-10–13, ERR-17, AC-03, AC-11 |

**Three information layers**

| Layer | Content | Visibility |
|---|---|---|
| 1 — Primary | Question; status badge; five-phase progress tracker; current-stage line; evidence-backed answer with citation chips; "Not established" claims; Limitations; budget summary | Always visible |
| 2 — Secondary | Research Plan; Retrieved Sources; Investigation Activity; Usage and Cost Budget | Collapsible panels / tabs |
| 3 — Evidence details | Evidence Drawer | Opened by citation |

**Vertical order of Layer 1 (top to bottom):**

1. **Question block** — "Research question" kicker, question text in `read-lead`, edit/rename affordance (title only; the question is immutable after creation in MVP — assumption, DQ-07).
2. **Status + tracker** — Status badge, phase tracker (§9.2), stage line (§9.3), run actions (Cancel).
3. **Budget summary strip** — compact one-line meters (§9.5), "Details" opens Budget tab.
4. **Notice region** — state banner when the run is not normally in progress or complete (§9.6).
5. **Answer** — Summary lead, Findings as claim blocks (§9.4), "Not established" items inline in place, **Limitations** card always present once an answer exists (Source Serif; lists important limits including insufficient evidence needs, FR-06.5, ERR-07), disclaimer "AI-generated research aid. Verify important findings using original sources."
6. **Report link** — Card "Report" with latest version and a link to the Report tab once a report exists.

**Secondary panel** — Radix Tabs: *Plan · Sources · Activity · Budget*. Tab counts shown in labels where meaningful ("Sources (9)"). Layout per breakpoint in §6.3.

**Evidence drawer** — see §8.6.

**Actions:** Start research (when ready), Cancel (while Running/Planning), open Report, open Sources, open any citation. **Resume** and **Restart** per §9.6 and §19.

**States:** see §9.6 (status matrix) and the per-component states in §12. Initial load: skeleton for question block, tracker and answer. Not found (`:id` invalid): "This investigation doesn't exist or was deleted." + Dashboard link.

**Accessibility:** one `h1` (investigation title); answer region `<article aria-labelledby>`; tracker is an ordered list (§9.2); stage/status announcements per §13.6; citation chips are buttons (§10); focus management per §10.6.

---

### 8.4 Research Plan Panel

| | |
|---|---|
| **Purpose** | Show how the question will be investigated and under which budget **before and during** research. |
| **Location** | Panel inside Workspace (secondary panel "Plan" tab; on mobile an accordion section; while an investigation is `Planning`/ready to start the plan is promoted into the primary column above the answer) |
| **Milestone** | M1 read-only; M2–M3 editing (FR-02b) |
| **PRD IDs** | FR-02.1, FR-02.2, FR-02b.1–.2, FR-11.1, ERR-10 |

**Content**

- Header: "Research plan", generation metadata in `mono-sm` (model ID, prompt version when stored, FR-P2).
- **Narrow-question note** (FR-02.1): when fewer than three sub-questions, show "Short plan: {reason}".
- **Sub-questions list** (3–8): ordered list; each item shows its number, the sub-question (`ui-body-lg`), and up to three search queries as `mono-sm` chips. Per-item progress marker once running: Pending / In progress / Done / Skipped (budget) / Failed, always text + icon.
- **Source types**: "Web" (M1), "Web + your documents" (M2+).
- **Budgets before running (FR-02.2):** the five limits as a 5-row definition list with "ceiling" note.
- **Start research** primary button (M1: explicit confirmation).

**Editing (Should, M2–M3; not rendered in M1):** each sub-question gets Edit, Remove, **Move up**, **Move down** buttons (keyboard and pointer alternatives to dragging; drag handle optional enhancement, never the only way — NFR-A, WCAG 2.5.7); "Add sub-question" button (blocked at 8, message "A plan can have up to 8 sub-questions"); queries editable with a cap of three per sub-question. Edits are validated against the plan schema (FR-P3) with inline errors. Approval switch (FR-02b.2) shows the "Awaiting approval" state.

**States:** Planning in progress (skeleton list + "Drafting a plan…"); plan failed (ERR-10: "The plan couldn't be generated. Nothing was searched. Try again."; Retry limited and bounded); plan locked while Running (read-only, message "The plan can't be changed during a run"); Cancelled/Interrupted (plan retained, items show where it stopped).
**Responsive/accessibility:** list semantics (`<ol>`); reorder announcements via live region "Moved to position 3 of 6".

---

### 8.5 Sources Explorer

| | |
|---|---|
| **Purpose** | Inspect every source considered: fetch status, provenance, excerpts, and what cites it. |
| **Route / milestone** | `/investigations/:id/sources` · M1 (PDF rows M2; credibility signals M3) |
| **PRD IDs** | FR-03.2, FR-03.4, FR-03.5, FR-10.1–.3, FR-W6–W10, FR-D3, FR-D9, UX-04, UX-06, ERR-04, ERR-05, FR-04.4 |

**Layout:** header with counts ("9 sources · 6 fetched · 1 partial · 2 not retrieved"); status filter (segmented ToggleGroup: All / Fetched / Partial / Not retrieved / Duplicate) — a design convenience, not a PRD requirement (DQ-13); the source list as a table (≥ 768 px) or cards.

**Columns:** Title + domain (`mono-sm`) · Type (Web / PDF) · Status badge · Retrieved (`<time>`) · Published (`Unknown` when absent, FR-W8/FR-10.1) · Author (`Unknown` when absent) · Passages (count) · Cited by (count of claims) · Expand control. M3 adds an age warning chip (FR-10.3) and source-type heuristic chip labeled "Heuristic" (FR-10.2), never a reliability score.

**Expanded row / card detail:** metadata list (original URL, canonical URL when trustworthy, retrieval timestamp, extraction version, FR-03.5); excerpt preview (first passages, `read-passage`) each with its passage ID in `mono-xs` and a **View in evidence panel** button that opens the drawer at that passage; **Open original** external link (see §10.7).

**Special states**

| Situation | Presentation |
|---|---|
| blocked / paywalled (ERR-05) | Row shows the status; detail text "DeepTrace doesn't bypass access controls. No text was saved from this page." No excerpt, no fabricated passage |
| failed (ERR-04) | Reason (for example "Address not found") and "Other sources weren't affected." |
| duplicate (FR-W7) | "Same content as {source}" link; excluded from counts of independent sources; DeepTrace does not claim independence from domain alone (FR-06.7) |
| partial | Warning note describing which part is missing |
| PDF (M2) | Shows physical page index and, when reliable, printed page label as distinct values ("PDF page 12 · printed page xii", FR-D3); extraction-quality badge |
| removed document (FR-D9) | Row remains in historical views as "Source removed"; excerpts are not shown; chips for it are inert |
| Empty | "No sources yet" while Planning/Running early; once finished with none: "No usable sources were found. See why in Activity." |
| Loading | Skeleton rows; sources appear progressively during a run (UX-03) |
| Error | Region banner with retry |

**Responsive:** cards below 768 px with the same fields stacked; filter becomes a Select.
**Accessibility:** real table with sortable headers (default sort: retrieval time desc), expandable rows via buttons with `aria-expanded`/`aria-controls`.

---

### 8.6 Evidence and Citation Drawer

| | |
|---|---|
| **Purpose** | Show exactly what was saved from the source, where it came from, what the software checked, and (from M3) what an AI judged — for one citation at a time. |
| **Opens from** | Citation chips (Workspace, Report, Compare), Sources rows, passage buttons |
| **Milestone** | M1 (web); M2 (PDF page, RAG); M3 (assessment layer) |
| **PRD IDs** | FR-06.2–06.7, FR-03.5, FR-05.3, FR-D2–D3, FR-D9, UX-04, UX-05, UX-06, NFR-A3, ERR-11 |

**Presentation by breakpoint:** docked 400 px panel (≥ 1280), 440 px overlay drawer (768–1279), full-height sheet (< 768). Overlay and sheet are modal Radix Dialogs; the docked panel is a non-modal `aside` (§10.6).

**Content order (top to bottom)**

1. **Header:** close button; "Evidence" kicker; **Source title** (`ui-h4`, wraps); source type chip (Web page / PDF); source status badge; "Citation 2 of 3 for this claim" with Previous / Next buttons (only when the claim has multiple citations).
2. **Locator:** web → host + path (`mono-sm`, truncated middle, full on focus/hover) and an **Open original ↗** link (external, §10.7); PDF → "PDF page 12" and, when reliably available, "printed page xii" (FR-D3); passage ID with copy button.
3. **Passage** (Sounding Line at its left, `--dt-highlight` behind the cited excerpt, Source Serif `read-passage`): the stored passage with surrounding context where the app stores it; the cited excerpt highlighted. If the passage is long, the area scrolls internally and auto-scrolls the highlight into view (instant under reduced motion).
4. **Retrieval details:** "Retrieved {date time}" (`<time>`), extraction version (FR-W4), ingestion version (FR-05.3), and for PDFs the extraction-quality badge.
5. **Automatic checks** (Layer A): three rows, each icon + text + status: *Passage found in saved sources*, *Belongs to this investigation*, *Quotation matches saved text* (or "No quotation presented" when the claim paraphrases). Section note: "These checks confirm the reference and wording. They don't confirm the claim is true."
6. **Automated assessment** (Layer B, **M3 only**): kicker "AUTOMATED ASSESSMENT"; assessment label chip (icon + text); sentence "An AI model judged this. It may be wrong."; **Model** (`mono-sm`), **Method** (name/version), assessed-at timestamp; link "How to read this". **In M1–M2 this section is replaced** by a single muted note: "Semantic assessment isn't performed in this version, so a valid citation here doesn't show that the source supports the claim." (Muted note on Ocean Navy = 5.03 ✅.)
7. **Cited by:** the claim text (truncated, expandable) and any other claims citing this passage; each is a button that scrolls to and highlights that claim in the page behind (overlay: closes drawer first).
8. **User review (M3, Should):** if the user overrode a stance, show original label, user label, and when.

**No percentage, score, star rating or "confidence" appears anywhere in the drawer (FR-06.7).**

**States**

| State | Presentation |
|---|---|
| Loading | Skeleton for title, passage and checks; focus already on the drawer heading |
| Normal (all checks passed) | As above |
| Reference check failed (ERR-11) | The chip that led here would normally not exist (citation suppressed); if reached by an old link: Danger banner "This reference couldn't be confirmed, so it isn't shown as evidence." No passage text is rendered |
| Quotation mismatch | Danger row in checks; the mismatching quote is not displayed as if it were a quote |
| Source removed (FR-D9) | "Source removed. This document was deleted, so the passage can't be shown. The claim that cited it keeps its text and is marked as no longer traceable." No fake link |
| Passage missing | "This passage isn't available in this investigation." |
| Offline | Works entirely from stored data (ERR-15); "Open original" link is still available but notes it needs the internet |

**Accessibility:** heading is the focus target on open; `aria-labelledby`; `Esc` closes; focus returns to the invoking chip; previous/next buttons have names like "Previous citation (1 of 3)". Details in §10.

---

### 8.7 Document Library

| | |
|---|---|
| **Purpose** | Upload, validate, list and remove PDFs; see extraction quality; attach documents to investigations. |
| **Route / milestone** | `/documents` · **M2** (cross-investigation library UX is Should, M3/V1) |
| **PRD IDs** | FR-04.1–.5, FR-05.4, FR-08.3, FR-D1–D9, SEC-15–17, UX-04, ERR-08, ERR-09, AC-12, AC-13 |

**Layout:** header "Documents" + **Upload PDF** button; limits note "Text-based PDFs up to 25 MB and 300 pages. Up to 10 PDFs per investigation." (values from SEC-15, configurable); drop zone; document list (table ≥ 768 px, cards below).

**Upload component (File upload):** a visible drop zone that is **also** a button opening the native file picker (keyboard access; drag is an enhancement only); multi-file; per-file progress rows.

**Per-file pipeline states (text + icon, announced politely):** Queued → Uploading → Validating → Extracting (page n of N) → Indexing → Ready; or Rejected. The pipeline copy never claims "exact" extraction (FR-D4).

**Rejection messages (specific, FR-D5, FR-D6, ERR-09):**

| Case | Message |
|---|---|
| Password-protected | "This PDF is password-protected. DeepTrace can't read encrypted files. Remove the password and upload it again." |
| Corrupt | "This file couldn't be read as a PDF. Nothing was saved." |
| Oversized (size/pages) | "This file is larger than the limit ({limit}). Nothing was saved." |
| Not a real PDF (disguised, SEC-16) | "This file isn't a valid PDF, so it wasn't saved." (no further detail about detection) |
| Too many documents | "This investigation already has 10 documents." |
| Duplicate (FR-D8) | "You've already uploaded this file. The existing copy was reused." |

Every rejection states what was saved ("Nothing was saved") and that partial indexing was rolled back (FR-D6).

**Scanned / image-only (FR-04.3, ERR-08):** Warning on the document and affected pages: "Some pages look like scans. Text recognition (OCR) isn't available in this version, so those pages can't be searched or cited."

**List columns:** Name · Pages · Size · Added · Extraction quality (badge) · Used in (count of investigations) · Actions (Add to investigation, Remove).

**Remove (FR-D9):** AlertDialog "Remove '{name}'? This deletes its saved text and search index from this computer. Existing reports that cited it will show 'Source removed' for those references."

**States:** Empty ("No documents yet — upload a text-based PDF to ask questions about it"); Loading skeletons; Error per file and per region; Offline: fully functional for upload/extraction that doesn't need the network (assumption — hosted embedding would be blocked and flagged, DQ-14).
**Responsive/accessibility:** progress rows are `role="status"` aggregated, not one announcement per percent; remove and add actions labeled with the document name.

---

### 8.8 Report Viewer

| | |
|---|---|
| **Purpose** | Preview a versioned Markdown report and download it. |
| **Route / milestone** | `/investigations/:id/report` · M1 |
| **PRD IDs** | FR-07.1–.5, FR-D9, FR-P2, SEC-18, UX-06, AC-16, AC-06 |

**Layout:** toolbar (sticky under tabs): **Version** select ("Version 2 — {date}"), **Download .md** primary button (FR-07.4), metadata disclosure button. Below: the report in a reading column (720 px, Source Serif), with a **References** section at the end.

**Fixed report structure (FR-07.1):** Title · Question · Summary · Findings · Supporting Evidence · Conflicting or Missing Evidence · Limitations · Methodology · References. A mini "On this report" anchor list appears as a right column ≥ 1280 px and as a collapsible section above the report on smaller screens.

**Mandatory elements:** disclaimer "AI-generated research aid. Verify important findings using original sources." at the top (in-app) and inside the downloaded file; Methodology section shows search queries, provider/model ID, prompt version, retrieval dates, source counts and notable omissions **without secrets** (FR-07.3, SEC-07).

**Citations in the report** use the same Citation Chip and open the Evidence Drawer (UX-06). Claims with unsupported/uncertain semantics are labeled in text (FR-07.2). Chips for removed sources are inert with the text "Source removed" (FR-D9).

**Validation at export (FR-07.2):** pressing Download first re-validates IDs and quotes; button shows "Checking references…"; result toast/banner: "Report checked: {n} references found, {m} quotations match. {k} claims are marked not established." The file downloads regardless, with the marked claims labeled inside it; a failed validation never silently strips text without a note.

**Versions (FR-07.5):** read-only; the selector lists immutable versions; older versions show a "You're viewing an older version" banner with "View latest". Creation of a new version is by a triggering action defined later (M3 regeneration after user corrections, UJ-3); no "Edit report" control exists.

**Rendering safety (SEC-18):** Markdown rendered with raw HTML disabled, links sanitized; external links get the external-link treatment (§10.7). Images from remote hosts are not loaded.

**States:** No report yet — "A report is created when research completes." (and during Budget reached/Cancelled: "Partial results are shown in the workspace. A report is available if one was generated."); Generating — skeleton + stage line; Failed — banner with what was saved; Loading — skeleton; Error downloading — "The file couldn't be saved. Your report is unchanged."
**Responsive:** toolbar wraps; version select full-width on mobile; tables inside reports scroll within their container.
**Accessibility:** report is an `<article>` with a proper heading outline starting at `h2` below the page `h1`; download status announced politely.

---

### 8.9 Settings

| | |
|---|---|
| **Purpose** | Configure provider credentials, understand and control data flow, set budgets and see storage. |
| **Route / milestone** | `/settings` · M1 |
| **PRD IDs** | SEC-01–09, SEC-03, SEC-05, FR-11.1, FR-W2, FR-W9, FR-10.3, UX-08, NFR-X1, ERR-03 |

**Layout:** left in-page section list (≥ 1024 px) or a Select (below) linking to anchored sections; sections are cards.

| Section | Content | Milestone |
|---|---|---|
| Providers | One card per role: **AI model**, **Search**, **Embeddings** (local by default; hosted option shows a data-transfer warning, SEC-03). Credential field is masked, never re-displays a stored value, shows "Saved" status and **Replace / Remove** (SEC-08). Provider names are populated from adapters (not hard-coded, OQ-01/02) | M1 (embeddings M2) |
| Data disclosure | The PRD §16.1 data-boundary table in plain language, per configured provider; consent state with **Revoke** (SEC-03); "No telemetry is collected" (SEC-02) | M1 |
| Run limits | Defaults and hard maxima for the five FR-11.1 limits | M1 |
| Web fetching | Read-only display of per-page limits (15 s, 5 MB, 5 redirects, FR-W2); editable within safe ceilings when implemented | M1 read-only |
| Storage | Data directory location, total size, per-investigation size warning threshold (~500 MB, NFR-X1) | M1 |
| Source age warning | Threshold in years (default 3, FR-10.3) | M3 |
| Domain rules | Allow/deny lists (FR-W9) | Should, deferred |
| Sensitive-document mode | SEC-05 | Should, deferred; not rendered until built |
| About | App version, link to docs, "Reopen setup wizard" | M1 |

**Not present:** theme switch (light theme is V1); any control for an unbuilt feature (§2.5).

**Save model:** each card saves independently with its own Save button; dirty state warns on navigation; success announced via status toast "Saved." (no celebratory styling).

**States:** Invalid key (ERR-03) — "The provider rejected this key. Calls have stopped. Check the key and try again." (no auto-retry); Unsaved — inline note; Secret handling — fields use `autocomplete="off"`, `type="password"` with a **Show/Hide** toggle only while the user is typing a new value; never reveal a stored value.
**Responsive/accessibility:** each card is a `<section>` with an `h2`; fields labelled; disclosures use plain text, not tooltips.

---

### 8.9a Destructive confirmation pattern (shared)

Radix AlertDialog; `role="alertdialog"`; title names the object ("Delete 'Climate policy review'?"); body says what is removed and what isn't; **Cancel** receives initial focus; destructive button uses the Danger button (§4.5) and the exact verb ("Delete investigation", "Remove document"); busy state while deleting; honest failure copy if any artifact could not be removed (FR-01.4, SEC-23). Used for: delete investigation, remove document, revoke consent (confirm), reset budgets (no).

---

### 8.10 Evidence Comparison View (optional)

| | |
|---|---|
| **Purpose** | Compare supporting and contradicting passages for a claim and let the user contest automated stance labels. |
| **Route / milestone** | `/investigations/:id/compare` · **M3, Should** — only if FR-09 is promoted; advanced analysis V1 |
| **PRD IDs** | FR-09.1–.4, FR-06.4, ERR-06, UJ-3, AC-08 |

**Terminology (important):** *passage-level* **stance** labels (`supports`, `contradicts`, `neutral`, `uncertain`, FR-09.1) are a different vocabulary from *claim-level* **assessment** labels (Supported / Uncertain / Contested / Unsupported, FR-06.4). The UI shows both under distinct headings and never reuses one set of words for the other: stance chips read "Supports this claim" / "Contradicts this claim" / "Neutral" / "Unclear" with a small "Automated label" tag.

**Layout (≥ 1024 px):** left column — claim list (searchable; contested claims first, each with its assessment label); main — the selected claim at top, then **two columns**: *Passages that support* | *Passages that contradict*; below, collapsible *Neutral* and *Unclear* groups. Each passage card: source, locator (page/URL), highlighted excerpt, stance chip, "Automated label" tag, **Contest label** button, "View in evidence panel".

**Mobile / narrow (equivalent sequential reading, FR-09.3):** single column with a ToggleGroup (*Supporting · Contradicting · Other*) that switches the group, or a continuous scroll in this order: claim → supporting → contradicting → other. Both sides remain reachable and in the same order as desktop.

**Contest flow (FR-09.4):** button opens a Dialog: choose a different stance or "Exclude this passage from the claim", optional note; Save. The card then shows **both** "Automated: Supports" and "Your review: Contradicts — {date}" (original is never overwritten). A **Changes since original** list and a "Regenerate report" action create a new immutable report version that records the changes' provenance (UJ-3, FR-07.5); the action is only shown when changes exist.

**Contested claims (FR-09.2):** surface both sides with limitations text; never silently choose a winner (ERR-06). A "How to read this" note states: "Both sides are shown. DeepTrace doesn't decide which is correct."

**States:** Empty — "No claims have conflicting evidence yet."; Loading skeleton; Error banner; Partial — claims lacking stance data are listed as "Not compared".
**Accessibility:** two-column region uses headings per column; Contest dialog is modal with focus return; stance chips are text + icon; list is keyboard-navigable.

---

### 8.11 First-Run Setup Wizard

| | |
|---|---|
| **Purpose** | Disclose external data flow before first use and help configure credentials. |
| **Route / milestone** | `/setup` · M1 (required for the first live run); reopenable from Settings |
| **PRD IDs** | UX-08, SEC-01, SEC-03, SEC-06, SEC-08, ERR-03, FR-11.1 |

**Layout:** full-page, centered 640 px card, Deep Navy background; an ordered stepper (“Step 2 of 5: What leaves your computer”) — text first, dots second.

| Step | Content |
|---|---|
| 1. Welcome | What DeepTrace does; "Stored on this computer. Not fully offline."; what it will **not** do (doesn't certify truth) |
| 2. Data flow | The PRD §16.1 table in plain language; explicit "I understand" checkbox required to continue; revocable later (SEC-03) |
| 3. AI model | Provider select + credential field (masked); "Save" ; failure copy per ERR-03 |
| 4. Search | Provider select + credential field |
| 5. Limits | Defaults for the five run limits with "ceilings, not targets"; Finish → Dashboard |

**Behavior:** Back/Next; progress saved after each step; "Skip for now" allowed on steps 3–5 (the user can browse saved data, but "Start research" is blocked until credentials exist); Escape does not exit; focus moves to the step heading on step change; errors summarized at the top.
**States:** Saving, invalid key, provider unreachable (distinguish from invalid key), offline ("Connect later when you're online").

---

## 9. Research Workspace Interaction Model

### 9.1 Lifecycle from the user's side

1. **Create** (`/new`) → status `Planning`; plan appears (§8.4).
2. **Start research** (M1 explicit confirmation) → `Running`; tracker begins.
3. Sources appear progressively; the answer appears once drafted and validated (see §9.4 for partial display).
4. Run ends in exactly one terminal-ish state: `Completed`, `Failed`, `Cancelled`, `Budget reached`, or the recoverable `Interrupted`/`Paused`.
5. Report created (when applicable) and linked.

### 9.2 Five-phase progress tracker

Five user-facing phases summarize the PRD's ten pipeline stages (PRD §11.1).

| Phase | PRD stages included | Present-participle stage text |
|---|---|---|
| 1. **Plan** | Plan | "Drafting the research plan" |
| 2. **Discover** | Discover (search) | "Searching for sources ({n} of {max} searches)" |
| 3. **Read** | Fetch → Extract → Retrieve/Rank → Draft | "Reading sources ({n} of {max} pages)" / "Drafting the answer" |
| 4. **Check** | Validate References/Quotes → Assess Claim Support (M3) | "Checking references and quotations" |
| 5. **Report** | Present → Report | "Preparing the report" |

*Assumption (DQ-01):* Draft is grouped under Read because it consumes the retrieved passages; the owner may regroup it under Check without any other design change. In M1–M2 the Check phase contains only the deterministic validation; "Assess Claim Support" joins it in M3 and the stage text then reads "Checking references, quotations and support".

**Phase states** (each phase shows its name and a state word, never an icon alone):

| State | Marker | Text | Color |
|---|---|---|---|
| Completed | `circle-check` filled | "Done" is **not** used; use "Completed" | Success |
| Active | 12 px ring/dot with Electric Blue; `loader` spinner if an operation is in flight | "In progress" | Electric Blue (non-text), label Text Primary |
| Pending | Hollow circle, Border Strong | "Pending" | Muted text on Deep Navy/Ocean Navy |
| Failed | `circle-x` | "Failed" | Danger |
| Stopped (Paused/Interrupted/Cancelled/Budget reached) | `circle-pause` / `unplug` / `ban` / `gauge` on the phase where work stopped | "Paused" / "Interrupted" / "Cancelled" / "Budget reached" | Warning (Cancelled: Secondary) |
| Skipped/not reached after a stop | Hollow circle, dimmed | "Not reached" | Muted |

**Layout:** horizontal stepper ≥ 768 px (five equal columns, connecting 2 px lines in Border Subtle; completed segments in Electric Blue) with the phase name under the marker; **compact** below 768 px: a single row "Phase 3 of 5 · Read — In progress" with a five-segment bar (each segment min 24 px wide with text alternative); tapping/activating the row expands a vertical list of all five phases. The connecting lines are decorative; state is in the text.

**Semantics:** `<ol aria-label="Research progress">`; each `<li>` includes visually-hidden state text; the active phase has `aria-current="step"`. It is **not** a progressbar and not an ARIA tablist.

### 9.3 Stage line and activity

Below the tracker a one-line **stage line** (`ui-body-lg`, Text Primary) describes the current work with real counts, for example "Reading sources — 6 of 15 pages". It updates at most once per second and is the only text in a polite live region for routine progress (§13.6). The first progress update must appear within 3 s of Start on the reference machine (NFR-P4); until real data exists, show "Starting…" with the spinner/static icon — never a fabricated percentage.

The **Activity** panel is a reverse-chronological log: timestamp (`mono-sm`), event ("Searched: {query}", "Fetched {domain} — fetched", "Fetch failed {domain} — timed out", "Rate limited — retrying in 8 s (attempt 2 of 3)", "Budget reached: searches"), source/passage links where relevant. It is **not** announced by screen readers except via the stage line and status changes. Event verbs are neutral ("Fetched", "Checked"), never "verified".

### 9.4 Answer composition and claim blocks

The answer is rendered in Source Serif as **claim blocks**: one to three sentences expressing a single factual proposition plus its citation chips, separated by `space-6`. Each block has the Sounding Line gutter (§3.6).

| Block type | Appearance | Required text/icon |
|---|---|---|
| **Cited claim** | Resting aqua Sounding Line; citation chips after the sentence | Chips (number + source hint) |
| **Cited claim, active** | Line 100%, subtle `--dt-tint-aqua` at 6% background while its drawer is open | — |
| **Not established** (FR-06.1, FR-06.5, ERR-07, ERR-11) | **Dashed** danger line, `circle-dashed` icon and the label **"Not established"** at the start of the block, in danger-tint chip; a following line "What would help: {additional evidence needed}" | Always text + icon + dashed line |
| **Citation removed** (ERR-11) | Same as Not established with note "A reference for this claim couldn't be confirmed and was removed." | |
| **Quote** | Quotation marks + `read-quote` italic, chip directly after | Only shown when quote check passed (FR-06.3) |
| **Source removed** (historical) | Claim text retained; chip replaced by inert "Source removed" tag | FR-D9 |
| **M3 assessed claim** | Cited claim plus a small assessment chip after the citation chips (Supported / Uncertain / Contested / Unsupported) with "Automated" tag | Hidden before M3 |

Every factual claim carries ≥ 1 valid citation chip **or** the Not established label (FR-06.1). Non-factual connective prose (transitions, headings) carries neither and uses no gutter line.

**Contested/missing evidence (M3):** a "Conflicting or missing evidence" subsection lists contested claims with the Violet Contested chip and a link to Evidence Compare; before M3, missing evidence is described in Limitations in prose.

**Streaming/partial display:** the answer is displayed **after** reference and quote validation so that no unvalidated citation chip is ever clickable; before then the region shows the stage line and skeleton. (If the backend later streams drafts, unvalidated text must be visibly marked "Draft — not yet checked" and carry no chips; deferred to API/PROMPTS, DQ-08.) For budget-reached or cancelled runs, whatever validated content exists is shown with a Partial-results banner (§9.6).

**Limitations card:** always present once an answer exists; Source Serif; includes: scope/time limits hit, insufficient-evidence statements, source coverage and independence caveats (FR-06.7: syndication and shared origins may count as one), age warnings (M3), non-English notes (ERR-16), truncation notes (ERR-17).

**Coverage line (FR-06.7):** a small non-numeric summary "Based on {n} sources ({k} independent-looking, {d} duplicates). Coverage and independence can't be guaranteed." The phrase "independent-looking" avoids asserting independence; no truth score.

### 9.5 Budget and usage

**Summary strip (Layer 1):** five compact meters in a row (wrapping on mobile): Steps `x / 25`, Searches `x / 20`, Pages `x / 15`, Tokens `≈ x / 400,000`, Time `mm:ss / 20:00`. Each meter: label, value (`mono-sm`, tabular), 4 px bar (Electric Blue fill on Sunken track; track and fill are decorative because the numbers carry the information). Tokens and money are prefixed "≈" and labeled "estimate" (FR-11.2). Reaching 100% turns the label to Warning text + `gauge` icon and the word "limit reached". Cost is shown **only** when trustworthy pricing is configured (FR-11.5); otherwise the Budget tab says "Cost estimate unavailable".

**Budget tab (Layer 2):** same five meters with larger labels, per-provider usage table (calls, estimated tokens, estimated cost where known), the configured limits (read-only during a run), and a text explanation "Limits are ceilings, not targets."

### 9.6 Status matrix (state, message, available actions)

Actions marked † are gated: **absent** until their milestone is implemented (§2.5). "Review" always means reading saved content.

| Status | Banner / notice (title — body) | Tracker | Available actions (M1) | Later |
|---|---|---|---|---|
| **Draft** | — "This investigation hasn't started." | All pending | Edit title, Continue to plan, Delete | — |
| **Planning** | — "Drafting a plan. Nothing has been searched yet." | Plan active | Cancel | — |
| **Awaiting approval / Ready to start** | Info — "Review the plan and run limits, then start." | Plan completed | **Start research**, Delete | Edit plan (FR-02b, M2–M3) |
| **Running** | — (stage line) | Active phase | **Cancel**, open sources/citations as they appear | Pause (see below) |
| **Completed** | Success (subtle) — "Research completed. Review the report and the limitations." | All completed | Open report, Review, Archive, Delete | — |
| **Paused** | Warning — "Paused. Saved evidence is kept." | Stopped marker | Review, Delete | Resume †M3 |
| **Interrupted** | Warning — "This run stopped when the app closed. Completed steps and sources are saved." | Stopped marker | Review, Delete | **Resume / Restart** †M3–M4 (FR-L2, L3) |
| **Failed** | Danger — "{What failed}. {What was saved}. {Next step}." | Failed marker | Review, Delete, Retry only where safe | Resume †M3 |
| **Cancelled** | Neutral — "You cancelled this run. Saved evidence is kept." | Stopped marker | Review, Delete | Resume †M3 |
| **Budget reached** | Warning — "Stopped: {limit} reached. Partial results are shown and may be incomplete." | Stopped marker (`gauge`) | Review, Open partial report, Delete | Resume with a new budget †M3 |
| **Archived** | Neutral — "Archived." | As before | Unarchive, Delete | — |

Rules for this matrix:

- **Resume is never rendered or enabled in M1 or M2.** On Interrupted/Paused/Failed/Cancelled/Budget-reached investigations in M1 the UI states what is true ("Resume isn't available in this version. Your saved evidence is kept.") but offers no button.
- **Restart** (a new run on the same question) is **not designed as available in M1**: the PRD names "Resume or Restart" for FR-L2 but defers resumable execution to M3–M4; whether a plain Restart ships earlier is DQ-02.
- **Pause** as a user action is not specified by the PRD as a control; the Paused state is displayed if the system produces it (FR-L4). A Pause button is deferred (DQ-03).
- Only `Completed` uses a Success treatment, and even that is understated: no animation, no confetti, no "Success!" copy.
- State changes are announced through the polite live region (§13.6) with the banner title text.

### 9.7 Cancel flow (FR-11.4, FR-L4)

**Cancel** (secondary button, `ban` icon) → confirmation popover/dialog: "Cancel this run? Evidence collected so far is kept." Buttons "Keep running" (default focus) / "Cancel run". After confirm: button becomes "Cancelling…" (loading); status → `Cancelled`. Cancelling never deletes anything.

### 9.8 Interaction details

| Interaction | Behavior |
|---|---|
| Clicking a citation chip | Opens/updates the Evidence Drawer (§10) |
| Clicking the same chip again | Closes the drawer, returns focus to the chip |
| Hovering/focusing a chip | Tooltip: "{Source title} · {locator}" (Raised surface, 8.50 aqua / 10.10 primary text); tooltip text is never the only access to information |
| Hover/focus a claim block | Sounding Line goes to 100% |
| Scroll position | Never auto-scrolled by the app during a run unless the user activates "Jump to latest"; new content appends below the reading position without shifting visible text |
| New sources arrive | The Sources tab count updates; no toast |
| Browser refresh during Running | State restored from stored data; if the backend process is gone the run is shown `Interrupted` (FR-L2) |
| Keyboard | `Tab` order follows visual order: header → tabs → tracker (not focusable unless expanded on compact) → run actions → answer chips → secondary panel tabs → drawer |

### 9.9 Loading, empty and failure in the workspace

| Situation | Presentation |
|---|---|
| Loading investigation | Skeleton: question, tracker, answer lines |
| No answer yet | "The answer will appear here after sources have been read and references checked." |
| No sources found (ERR-07) | Limitations-style card "No usable sources were found. Nothing is claimed." with link to Activity and a suggestion to refine the question |
| Search provider rate limited (ERR-01) | Activity line + Warning inline notice "Search is rate limited. Retrying in {n} s (attempt {k} of 3)." — bounded retries, no infinite spinner |
| LLM outage (ERR-02) | Warning/Danger banner "The AI model didn't respond. Your progress is saved." with a Retry only if safe |
| Invalid key (ERR-03) | Danger banner linking to Settings; run stops |
| Malformed model output (ERR-10) | "A step returned an unreadable result after {n} attempts. Saved so far: {…}." |
| Input truncated (ERR-17) | Limitations note + Activity line naming what was omitted |
| Non-English sources (ERR-16) | Notice on the affected sources and in Limitations |

---

## 10. Evidence and Citation Interaction Model

### 10.1 Citation chip anatomy

`[ 3 ]` or `[ 3 · p.12 ]` — IBM Plex Mono `mono-xs`, 4 px radius, **min 28 × 24 px** hit area (24 px floor, WCAG 2.5.8) with 4 px spacing between chips, Raised fill, 1 px Border Strong, Text Primary label. M3 adds a 12 px assessment icon at the right edge (icon + label are in the accessible name). **Chips are neutral, not aqua**: aqua is reserved for Sounding Line/highlight/focus/"Supported" so that merely having a citation is never styled like support.

Accessible name: "Citation 3: {Source title}, page 12. Opens evidence panel." (`aria-haspopup="dialog"` for overlay modes; `aria-expanded` reflects open state; `aria-controls` points to the drawer.) PDF page references use the physical page index and note the printed label when available (FR-D3).

A claim with several citations shows chips in a row with `gap-1`; more than **5** chips collapse to "+N more" opening the first hidden one in the drawer with Previous/Next to traverse.

### 10.2 What a user can learn, and how fast

| Question | Answer location | Clicks |
|---|---|---|
| "Where did this come from?" | Chip tooltip, then drawer header/locator | 1 |
| "What exactly does the source say?" | Drawer passage with highlighted excerpt | 1 |
| "Was this really in the saved source?" | Drawer — Automatic checks | 1 |
| "Does the source support the claim?" | M3: Drawer — Automated assessment (fallible). M1–M2: user reads the passage; drawer says no assessment is performed | 1 |
| "Is this source reliable?" | M3: heuristic indicators only (FR-10.2); never a score | — |

### 10.3 Drawer modes

| Mode | When | Modality | Focus handling |
|---|---|---|---|
| Docked | ≥ 1280 px | **Non-modal** `aside` (complementary) | Focus moves to the drawer heading on open; main content stays interactive; `Esc` closes when focus is inside; focus returns to the chip |
| Overlay | 768–1279 px | Modal dialog | Focus trapped; scrim; `Esc`, close button, and scrim click close; background inert |
| Full-height sheet | < 768 px | Modal dialog | As overlay; uses `100dvh`; safe-area padding; swipe-to-dismiss is optional and never the only way |

The same Evidence Panel component renders in all three modes (§11.17); only its container changes.

### 10.4 Opening, switching and closing

1. **Open:** click/Enter/Space on a chip. Drawer content loads (skeleton for ≤ 300 ms typical since data is local).
2. **Switch:** activating another chip while open replaces content, keeps the drawer open, moves focus to the new heading, announces "Evidence for citation {n}".
3. **Traverse:** Previous/Next within the claim's citations (keyboard `[` and `]` shortcuts are *optional* and must be discoverable; not required).
4. **Close:** close button, `Esc`, scrim click (modal modes), or activating the active chip again. The URL's `evidence` parameter is removed.
5. **Deep link:** `?evidence=<passageId>` opens the drawer on load (§7.4).
6. **Back button:** in modal modes the browser Back closes the drawer before leaving the page (history entry added when it opens).

### 10.5 Highlighting

The cited excerpt is highlighted within its stored passage with `--dt-highlight` (aqua 22%) and the Sounding Line; text stays Text Primary (6.56:1 on Ocean Navy). If the exact offset cannot be located (for example extraction version changed), show the passage without highlight and a note "The exact excerpt couldn't be located. The full passage is shown." (never a guessed highlight). For PDFs, highlight is within the page's stored text; rendering the original PDF page image is out of scope (§20).

### 10.6 Focus, announcements, keyboard

- Opening: focus to drawer `h2` (programmatic `tabindex="-1"`), announced as the dialog name.
- Closing: focus returns to the invoking chip; if the chip no longer exists (list changed) focus goes to the claim block container.
- `Tab` order inside: Close → Previous/Next → Open original → Copy ID → Cited-by buttons → (M3) assessment details link.
- Visible focus per §4.6 on every control inside.
- Docked mode must not obscure the focused element in the main column (WCAG 2.4.11): main column has `scroll-padding` equal to drawer widths where relevant.

### 10.7 External links

External URLs (source pages, publisher pages) are always a visible, labeled link: text + `external-link` icon, `target="_blank"`, `rel="noopener noreferrer"`, accessible suffix "(opens in a new tab)", and display the hostname in `mono-sm` so the destination is clear before clicking (UX-06). The app never auto-opens external pages and never proxies them. URLs shown in the UI are the stored original (and canonical when trustworthy, FR-03.5); credentials in URLs are never displayed (SEC-21).

### 10.8 Wording standards inside the evidence UI

| Do | Don't |
|---|---|
| "Passage found in saved sources" | "Verified" |
| "Quotation matches saved text" | "Quote is accurate" / "Fact-checked" |
| "Automated assessment: Supported. An AI model judged this. It may be wrong." | "Verified true", "High confidence", "98% supported" |
| "Not established" | "False" (the app has not established falsity) |
| "Contested — both sides shown" | "Disputed by experts" (unless that is itself sourced) |
| "Source removed" | A dead link |

### 10.9 "How to read evidence" help

A help popover (button "How to read this" near the answer header; Radix Popover, also reachable from the drawer) explains in five lines:
1. The aqua line links a claim to the passages it cites. It shows traceability, not truth.
2. Automatic checks confirm the reference and wording match what was saved.
3. Automated assessments (from M3) are an AI's judgment and may be wrong.
4. "Not established" means DeepTrace couldn't tie the claim to a saved passage.
5. Always read the original source for important decisions.

First-time users see it once after the first answer (dismissible, remembered locally); it is never forced again.

### 10.10 Error and edge cases

| Case | Behavior |
|---|---|
| Chip points to a passage that fails the reference check | Chip is not rendered (citation suppressed); claim becomes Not established (ERR-11) |
| Two chips resolve to the same passage | Both chips remain; drawer shows the same passage, "Cited by" lists both claims |
| Very long passage | Internal scroll, highlight scrolled into view, "Show full passage" expand if the stored context is truncated |
| RTL or non-Latin text | Passage container `dir="auto"`; fonts fall back gracefully |
| Passage removed due to document removal (FR-D9) | Source-removed state (§8.6) |
| Source updated since retrieval | The drawer shows the **saved** text and retrieval time; copy: "This is the text saved on {date}. The live page may have changed." |

---

## 11. Reusable Component Library

All components use semantic tokens (§3.4), the type scale (§5.2), the focus ring (§4.6) and the radii (§5.4). Radix UI primitives are used where marked; Lucide supplies icons. Each component lists its purpose, anatomy and constraints; the state matrix is §12.

Naming: PascalCase component names are proposals; folders and file layout are decided in `ARCHITECTURE.md`.

| # | Component | Radix / base | Milestone | Anatomy & key rules |
|---|---|---|---|---|
| 11.1 | **Button** | Native `<button>` (+ Radix Slot for link-as-button) | M0 | Variants: primary, secondary, ghost, destructive, icon-only. Height 40 (32 small, 44 touch). Label 14/20, weight 500; icon 16 px with 8 px gap. Icon-only requires accessible name and tooltip. Loading shows `loader` + "Working…", retains width, `aria-disabled`. |
| 11.2 | **Input** | Native `<input>` | M0 | Sunken fill, 1 px Border Strong, 6 px radius, 40 px height (44 mobile, 16 px text). Label above (13/20), helper text below (Muted, only on Deep/Ocean Navy/Sunken), error text with icon. Supports prefix/suffix icon, password with Show/Hide. |
| 11.3 | **Textarea** | Native | M0 | As Input; auto-grow with min rows, character counter (`mono-sm`) tied via `aria-describedby`; counter turns Danger text + icon on limit breach. |
| 11.4 | **Select / Dropdown menu / Switch / Checkbox / Radio / ToggleGroup** | Radix Select, DropdownMenu, Switch, Checkbox, RadioGroup, ToggleGroup | M0–M1 | Boundaries Border Strong; Switch "on" track Electric Blue with text "On"/"Off" visible; checked states use Light Aqua check mark on Sunken or Primary Blue fill with white check; hit area ≥ 24 px, 44 px touch. |
| 11.5 | **Navigation** (Sidebar, Header, InvestigationNav, MobileNavDialog) | Native `<nav>`; Radix Dialog for mobile | M0 | See §6–7. Selected: Ocean Blue fill + Text Primary + 3 px aqua indicator + `aria-current`. |
| 11.6 | **Card** | `<section>`/`<article>` | M0 | Ocean Navy, 1 px Border Subtle, 10 px radius, padding 24 (16 mobile). Optional header (`ui-h4`), footer actions. Never interactive as a whole unless it is a single link (stretched link). |
| 11.7 | **Table** | Native `<table>` | M1 | Header row Ocean Navy with `ui-caption` uppercase 0.02em headers, rows 1 px Border Subtle dividers, row hover Raised, tabular numerals, sticky header optional; collapses to cards below 768 px; scroll container for overflow; sortable headers are buttons with `aria-sort`. |
| 11.8 | **Tabs** | Radix Tabs | M1 | For in-page panels (Plan/Sources/Activity/Budget). 44 px height; selected 2 px aqua underline + Primary text; arrow-key roving focus. Not used for route navigation (§7.3). |
| 11.9 | **StatusBadge** (investigation, source, extraction, check) | Native `<span>` | M1 | Icon 12–14 px + text 12/16 weight 500, 4 px radius, tint background + status-color text/icon per §4.4. Text always visible. |
| 11.10 | **PhaseTracker** | Native `<ol>` | M1 | §9.2. |
| 11.11 | **BudgetMeter / BudgetStrip** | Native; optional Radix Progress with `aria-valuenow` | M1 | §9.5. Each meter has a text value; bar is decorative (`aria-hidden`) when text duplicates it. |
| 11.12 | **Modal / AlertDialog** | Radix Dialog, AlertDialog | M0–M1 | 14 px radius, Ocean Navy, Border Strong 1 px, scrim, max 520 px wide (full-screen sheet below 480 px for long forms), focus trap, `Esc`, return focus, title + description wired via `aria-labelledby`/`describedby`. AlertDialog initial focus on Cancel. |
| 11.13 | **Drawer / EvidencePanel container** | Radix Dialog (modal modes); custom `aside` (docked) | M1 | §8.6, §10.3. 14 px radius on overlay left corners; 0 docked; slide 200 ms (instant when reduced). |
| 11.14 | **Notification** — Toast + Banner + InlineAlert | Radix Toast (`role="status"`); native for banners | M1 | Toast: Raised surface, 10 px radius, auto-dismiss after 6 s for success/info (never for errors), pause on hover/focus, closable, never the only place important information appears. Banner: tinted per §4.4, icon + title + body + optional action; `role="alert"` only for new errors, else `role="status"` / static. |
| 11.15 | **FileUpload** | Native `<input type="file">` + drop zone | M2 | §8.7. Drop zone is a labelled button; per-file rows with state text; supports multiple files; rejects with the specific messages in §8.7. |
| 11.16 | **CitationChip** | Native `<button>` | M1 | §10.1. States: default, hover, focus, pressed, open/active, inert (source removed). |
| 11.17 | **EvidencePanel** (contents) and **PassagePreview** | Native | M1 | Passage preview: Sunken well, Sounding Line left, `read-passage`, highlight, locator row, ID chip in `mono-xs`, max-height with internal scroll. Reused in Sources rows, Compare cards and the drawer. |
| 11.18 | **AssessmentLabel** | Native `<span>` | **M3** | Icon + word (Supported / Uncertain / Contested / Unsupported) + "Automated" tag (`ui-caption`). Tint per §4.4. Includes `title`-independent accessible text "Automated assessment: Supported". Hidden before M3. |
| 11.19 | **CheckRow** (deterministic checks) | Native | M1 | Icon + label + state text (Passed / Failed / Not applicable). |
| 11.20 | **ClaimBlock** | Native `<div>` in `<article>` | M1 | §9.4. Slots: Sounding Line gutter, text, citation chip group, optional label/note. |
| 11.21 | **SourceCard / SourceRow** | Native | M1 | §8.5. Title (link), domain mono, badges, meta list, expand control. |
| 11.22 | **DocumentCard / DocumentRow** | Native | M2 | §8.7. Name, pages, size, quality badge, usage, actions. |
| 11.23 | **ReportViewer** | Native + sanitized Markdown renderer | M1 | §8.8. Serif article; `read-h2` etc.; tables scroll in container; no raw HTML (SEC-18). |
| 11.24 | **LoadingSkeleton** | Native | M0 | Sunken-to-Raised blocks matching final dimensions; `aria-hidden`; parent `aria-busy`; shimmer only if motion allowed. |
| 11.25 | **EmptyState** | Native | M0 | §8.0.4. |
| 11.26 | **Stepper** (wizard) | Native `<ol>` | M1 | Text first: "Step 2 of 5 — What leaves your computer". |
| 11.27 | **Tooltip / Popover** | Radix Tooltip, Popover | M0 | Raised surface; tooltip delay 400 ms; never the only information source; no interactive content in tooltips (use Popover). |
| 11.28 | **Collapsible / Accordion** | Radix Collapsible/Accordion | M1 | Used for mobile secondary panels and Run limits. Header button `aria-expanded`; 44 px min height. |
| 11.29 | **StanceChip / ComparePassageCard** | Native | **M3 (Should)** | §8.10. |
| 11.30 | **ExternalLink** | Native `<a>` | M1 | §10.7. |
| 11.31 | **CopyButton** | Native + live region | M1 | Copies IDs; announces "Copied". |
| 11.32 | **SkipLink, VisuallyHidden, LiveRegion** | Radix VisuallyHidden / native | M0 | §13. |

**Component rules**

1. Components never hard-code hex values; they use semantic tokens.
2. A component that shows evidence status must accept its text label as a **required** prop (cannot render color-only).
3. Evidence-layer components (CheckRow, AssessmentLabel) are separate components so that Layer A can never be styled like Layer B.
4. No component may render "Resume", "Pause", "Compare", assessment labels, or PDF features unless the corresponding milestone flag is on (§2.5).

---

## 12. Component Variants and State Matrix

State legend: ✔ required; — not applicable. All interactive components require **default, hover, focus-visible, active/pressed, disabled**; loading/error/selected where applicable.

### 12.1 Buttons

| Variant | Default | Hover | Pressed | Focus-visible | Disabled | Loading |
|---|---|---|---|---|---|---|
| Primary | `#0066D9` fill / white text | `#005BC4` | `#0050AD` | Aqua ring, 2 px offset | 40% opacity, `aria-disabled`, no hover | `loader` + "Working…", width locked |
| Secondary | Transparent, Border Strong, Primary text | Raised fill | Sunken fill | Aqua ring | 40% opacity | as above |
| Ghost / link-style | Link color text, no border | Underline, Raised fill if in a toolbar (text switches to Aqua) | Sunken fill | Aqua ring | 40% opacity | — |
| Destructive | `#FF8A8A` fill / Deep Navy text | `#FF7373` | `#FF5C5C` | Aqua ring, **outside** offset only | 40% opacity | as above |
| Icon-only | 40×40 (44 touch), icon Text Primary | Raised fill | Sunken fill | Aqua ring | 40% opacity | spinner |

Disabled controls use `aria-disabled="true"` where the control should stay focusable to explain why (for example offline); a true `disabled` is used otherwise. Disabled text is exempt from contrast thresholds but must remain legible and carry a reason when the control is a primary path.

### 12.2 Form controls

| State | Input / Textarea / Select |
|---|---|
| Default | Sunken fill, Border Strong, Primary text, Muted placeholder (6.61 on Deep, 7.34 on Sunken) |
| Hover | Border `#A9BBD0` (Secondary text color) |
| Focus | Aqua 2 px ring (offset 2) + Border Strong retained |
| Filled | As default |
| Error | Danger 2 px bottom/left emphasis **plus** error icon and message; `aria-invalid` |
| Disabled | 40% opacity, dashed Border Subtle |
| Read-only | No fill change, "Read-only" cue via lock icon where meaningful |
| Success (after validation) | Check icon + text only when helpful (not for every field) |

Placeholders are never the only label.

### 12.3 Navigation and tabs

| Element | Default | Hover | Selected | Focus-visible | Disabled |
|---|---|---|---|---|---|
| Sidebar item | Text Secondary label on Ocean Navy | Raised fill, Text Secondary → Primary | Ocean Blue fill, Primary text, white icon, aqua left bar, `aria-current` | Aqua 2 px ring, inset (offset −2 px) so the sidebar edge does not clip it; aqua vs Ocean Blue is 5.54:1 | — (items absent, not disabled) |
| Investigation nav link | Text Secondary | Text Primary + Raised bg | Text Primary + aqua underline, `aria-current` | Aqua ring | — |
| In-page Tabs trigger | Text Secondary | Primary text | Primary text + aqua underline, `aria-selected` | Aqua ring | 40% opacity |

### 12.4 Status badges

| Variant | Background | Text/icon | Border |
|---|---|---|---|
| Running / Planning | `--dt-tint` Electric Blue 18% | Text Primary + Electric icon (non-text) | none |
| Completed / Passed | Success tint | Success | none |
| Warning (Interrupted, Paused, Budget reached, Uncertain, degraded) | Warning tint | Warning | none |
| Danger (Failed, blocked, Failed check) | Danger tint | Danger | none |
| Contested | Contested tint | Contested | none |
| Neutral (Draft, Cancelled, duplicate, Archived) | none | Text Secondary | 1 px Border Strong |
| Not established | Danger tint | Danger | 1 px **dashed** Danger |

Badges are not interactive. If a badge opens an explanation, wrap it in a button and treat it as a CitationChip-like control.

### 12.5 CitationChip

| State | Appearance |
|---|---|
| Default | Raised fill, 1 px Border Strong, Primary mono label |
| Hover | Border `#A9BBD0`, tooltip after 400 ms |
| Focus-visible | Aqua ring |
| Pressed | Sunken fill |
| Open/active | 2 px aqua left edge + Selected tint; `aria-expanded="true"`; claim block gets active Sounding Line |
| Inert (source removed) | Dashed Border Strong, Muted label "Source removed" (muted on Ocean Navy 5.03), not focusable as a button but available as text |
| M3 assessed | Appends 12 px status icon; accessible name includes label |

### 12.6 ClaimBlock

| State | Gutter | Extra |
|---|---|---|
| Cited, rest | Aqua 35% line | Chips |
| Cited, hover/focus-within | Aqua 100% | — |
| Cited, active | Aqua 100% + 6% aqua tint | Drawer open |
| Not established | Dashed Danger line | Label + icon + "What would help" |
| Citation removed | Dashed Danger line | Label + note |
| M3 Contested | Aqua line retained + Contested chip | Link to Compare |
| Loading | Skeleton lines | — |

### 12.7 Phase tracker markers

See §9.2 table. Also required: reduced-motion static variant for Active.

### 12.8 Table rows and cards

Default (Ocean Navy), hover (Raised; muted text switches to Secondary, rule C2), focus-within (aqua ring on the row's link/button, not the whole row), selected (Ocean Blue only for the Dashboard's keyboard-selected row if introduced; otherwise unused), expanded (Sunken detail well), loading (skeleton), empty (§8.0.4), error (inline row error with retry).

### 12.9 Drawer / modal

| State | Behavior |
|---|---|
| Closed | Not in DOM/accessibility tree (or `inert`) |
| Opening | Slide 16 px + fade 200 ms (instant when reduced) |
| Open (loading) | Heading + skeleton |
| Open (loaded) | §8.6 |
| Open (error) | Banner inside; Close still available |
| Closing | Fade ≤ 120 ms; focus returned |

### 12.10 Notifications

| Type | Role | Duration | Dismiss |
|---|---|---|---|
| Toast info/success | `status` | 6 s, pause on hover/focus | Button |
| Toast error | `alert` | Persistent until dismissed | Button |
| Banner persistent (offline, storage) | `status` | Until condition clears | None, or dismiss for storage per session |
| Banner error (region) | `alert` on appearance | Until resolved | Retry/Dismiss |

### 12.11 FileUpload

Idle, drag-over (dashed aqua border + text "Drop to upload"), file-selected, uploading (progress text and bar), validating, extracting, indexing, ready, rejected (reason), warning (scan detected), and removed. Each state has text, not color alone.

### 12.12 AssessmentLabel (M3)

Variants Supported, Uncertain, Contested, Unsupported; each = icon + word + "Automated" tag; states default, hover (tooltip "An AI model judged this. It may be wrong."), focus (it is a button when it opens details), disabled/n.a. ("Not assessed").

### 12.13 Loading skeletons and empty states

Skeleton variants: line, paragraph (3–5 lines of varying width), card, table row, passage block, tracker. Empty-state variants: no investigations, no sources, no documents, no report, no comparison data, no filter results, offline. Each has icon, title, one sentence, one action.

---

## 13. Accessibility Requirements

Target: **WCAG 2.2 Level AA** for core flows (NFR-A1). Core flows for AC-17: (1) first-run setup, (2) create investigation, (3) run and read an answer, (4) open and read evidence, (5) download a report. M2 adds upload; M3 adds contest-a-label.

> **Verification status:** nothing below has been tested. This document specifies requirements and design-time checks; compliance may be claimed only after automated and manual audits (AC-17) pass.

### 13.1 Keyboard

| Requirement | Specification |
|---|---|
| All functionality operable by keyboard | Every control reachable by `Tab`/`Shift+Tab`; no keyboard traps except intentional modal traps with `Esc` exit |
| Order | DOM order = visual order; no positive `tabindex` |
| Skip link | First focusable item "Skip to main content" |
| Widgets | Radix handles Tabs (arrows), Select, DropdownMenu, Dialog, Popover, Tooltip (focus-triggered), Toast (hotkey off by default) |
| Plan reordering | Move up/down buttons (not drag-only; WCAG 2.5.7) |
| File upload | Button opens native picker; drop zone is optional |
| Citation chips | `Enter` and `Space` activate; `Esc` closes drawer |
| Shortcuts | None required. If added later they are single-modifier, documented, and do not conflict with screen readers (WCAG 2.1.4) |

### 13.2 Focus

- Visible aqua focus ring everywhere (§4.6), never removed.
- Focus not obscured (2.4.11): sticky header/tabs/docked drawer use `scroll-padding` so a focused element is never hidden behind them.
- Route change: focus moves to the page `h1`; modal open: to the dialog heading (or the Cancel button for AlertDialog); modal close: back to the trigger.
- Focus is never moved by background updates (progress, new sources).

### 13.3 Semantics and structure

- One `h1` per page; headings nest without skipping.
- Landmarks per §6.2.
- Lists for plans, phases and sources use `<ol>`/`<ul>`; tables use real table markup with `<th scope>`; definition lists for metadata.
- Buttons are `<button>`, navigation is `<a>`; no clickable `div`s.
- `<time datetime>` for timestamps; `lang` set on `<html>` and on foreign-language passages when known.
- The page title changes per route.

### 13.4 Names, labels and instructions

- Every control has a programmatic label; icon-only buttons have `aria-label` and tooltip.
- Required fields are marked in text ("Required"), not only an asterisk.
- Error messages are linked via `aria-describedby`; an error summary appears on failed submit with links to fields (3.3.1, 3.3.3).
- External links announce "(opens in a new tab)".
- Citation chips announce source and page (§10.1).

### 13.5 Color and non-text contrast

- Contrast rules C1–C8 (§4.3) are normative; a CI/design-lint check should flag forbidden pairings where feasible.
- Meaning is never carried by color alone (UX-05, NFR-A4): all statuses = icon + text; claim states also differ by line style (solid vs dashed).
- Interactive control boundaries ≥ 3:1 (Border Strong).
- Focus ring ≥ 3:1 against adjacent colors.
- The UI respects `forced-colors` (Windows High Contrast): borders become system colors; focus uses `outline` (not `box-shadow`) so it survives forced colors; SVG icons use `currentColor`. Windows is the primary platform (NFR-C1), so this is verified on Windows.

### 13.6 Status messages and live regions (WCAG 4.1.3)

| Event | Mechanism | Politeness |
|---|---|---|
| Phase change / stage line | Single live region, debounced to ≤ 1 announcement per 5 s unless phase changes | polite |
| Run status change (Completed, Failed, Cancelled, Budget reached, Interrupted) | Live region with banner title | polite (assertive for Failed) |
| Source count increments | Not announced (visible only) | — |
| Form validation summary | `role="alert"` on submit | assertive |
| Toasts | `role="status"` (errors `role="alert"`) | polite/assertive |
| Upload progress | One aggregated status line | polite |
| Copy ID | "Copied" | polite |
| Drawer open | Dialog name read by AT | — |

The activity log is not a live region. Percent counters never announce each increment.

### 13.7 Motion and animation

Honor `prefers-reduced-motion` per §5.6. No content flashes more than three times per second. Auto-updating content (stage line) has a text equivalent; no auto-advancing carousels or timed content except toast dismissal (errors persist).

### 13.8 Responsive reflow, zoom and spacing

- Reflow at 320 CSS px-equivalent (400% zoom of 1280) without two-dimensional scrolling for text content (1.4.10), except data tables/code that scroll within their container.
- Text resizes to 200% without loss; sizes in `rem`.
- Text spacing overrides (line-height 1.5, paragraph spacing 2×, letter 0.12em, word 0.16em) must not clip (1.4.12): no fixed heights on text containers.
- Targets ≥ 24 × 24 CSS px (2.5.8), 44 px on touch layouts.
- Orientation not locked.

### 13.9 Authentication and consistency

No login in MVP (D-01), so 3.3.8 does not apply; credentials entry in Settings supports paste (no paste blocking) and password managers. Consistent navigation order and consistent help (the "How to read this" popover appears in the same place) satisfy 3.2.3 and 3.2.6.

### 13.10 Verification plan (feeds AC-17, AC-19)

1. Automated: axe-core (or equivalent) in component and page tests — zero critical/serious on core pages.
2. Manual keyboard pass on the five core flows.
3. Screen reader smoke tests: NVDA + Chrome and NVDA + Edge on Windows (primary, NFR-C1, NFR-C2); VoiceOver later with Safari QA.
4. Zoom 200% / 400%, text-spacing bookmarklet, reduced motion, forced colors.
5. Contrast: recompute §4 with tooling after any token change.
6. Record results; only then update status from `planned` to `verified`.

---

## 14. Content and Microcopy Guidelines

### 14.1 Voice

Plain, calm, precise, non-promotional; second person ("you") for actions, first-person plural never. Short sentences. States facts and limits. No exclamation marks, no emoji, no humor in errors.

### 14.2 Vocabulary

| Use | Avoid |
|---|---|
| investigation, question, source, passage, citation, claim, report | chat, conversation, prompt (user-facing), search result (for sources) |
| "Cited" / "Not established" | "True", "False", "Verified", "Fact" |
| "Automated assessment" (M3) | "AI verification", "Fact check", "Confidence", "Reliability score" |
| "Checked" for deterministic checks | "Validated by AI" |
| "Stored on this computer" | "Private", "Secure", "Offline", "100% local" |
| "Stopped: budget reached" | "Done", "Finished", "Complete" (reserved for Completed) |
| "Saved evidence is kept" | "Nothing lost" (cannot promise) |
| "Estimated" for tokens/cost | Exact-looking costs |
| "Source removed" | Broken link |

### 14.3 Required fixed strings

| Where | Text |
|---|---|
| Reports and report viewer | "AI-generated research aid. Verify important findings using original sources." |
| Tagline | "Research you can trace." |
| Layer A note | "These checks confirm the reference and wording. They don't confirm the claim is true." |
| Layer B note (M3) | "An AI model judged this. It may be wrong." |
| M1–M2 drawer note | "Semantic assessment isn't performed in this version, so a valid citation here doesn't show that the source supports the claim." |
| Local-first statement | "Your investigations are stored on this computer. Searches, page requests and selected text still go to the providers you configure." |
| Budget note | "Limits are ceilings, not targets." |
| OCR | "OCR isn't available in this version, so scanned pages can't be searched or cited." |
| Telemetry | "DeepTrace doesn't collect telemetry." |

### 14.4 Banned claims

Never display: "guaranteed accurate", "truth verified", "completely reliable", "high confidence", "fact-checked", "AI-verified", "proven", "no hallucinations", any numeric confidence/accuracy for an individual claim, or any competitor comparison (PRD §6).

### 14.5 Error message pattern (PRD §17)

`{What failed}. {What was saved}. {What you can do}.` Examples:

| Case | Copy |
|---|---|
| ERR-01 search 429/5xx | "The search provider is busy. Your run is saved. DeepTrace will retry up to 3 times, or you can try again later." |
| ERR-02 LLM outage | "The AI model didn't respond. Progress so far is saved. Try again in a moment." |
| ERR-03 invalid key | "The provider rejected your key. Calls have stopped. Check the key in Settings." |
| ERR-04 DNS/URL | "{domain} couldn't be reached. Other sources weren't affected." |
| ERR-05 blocked/paywalled | "{domain} didn't allow access. No text was saved, and DeepTrace doesn't bypass access controls." |
| ERR-06 conflict | "These sources disagree. Both sides are shown. DeepTrace doesn't decide which is right." |
| ERR-07 insufficient | "The saved sources don't establish this. What would help: {…}." |
| ERR-08 scanned | "Some pages look like scans. OCR isn't available in this version, so they can't be searched or cited." |
| ERR-09 bad PDF | "This file couldn't be added ({reason}). Nothing was saved." |
| ERR-10 malformed | "A step returned an unreadable result after 3 attempts. Everything completed before it is saved." |
| ERR-11 invalid citation | "A reference for this claim couldn't be confirmed and was removed. The claim is marked not established." |
| ERR-12 crash | "This run stopped when the app closed. Completed steps and sources are saved." |
| ERR-13 budget | "Stopped: {limit} reached. Partial results are shown and may be incomplete." |
| ERR-14 disk/DB | "Couldn't save changes. Nothing was written. Free some disk space and try again." |
| ERR-15 offline | "You're offline. Saved investigations are available. Searching and AI steps need an internet connection." |
| ERR-16 non-English | "Some sources aren't in English. Results may be less reliable for them." |
| ERR-17 truncation | "Some text was left out to fit limits: {what}. This may affect completeness." |

### 14.6 Empty-state and button copy

Buttons use verb + object: "New investigation", "Start research", "Cancel run", "Download .md", "Upload PDF", "Open original". Destructive buttons repeat the object ("Delete investigation"). Avoid "OK", "Submit", "Yes/No".

### 14.7 Numbers, dates, units

Dates: locale-aware absolute (`2026-10-23 14:05`) with relative text ("2 h ago") as supplementary; time zone shown in tooltips. Counts use grouping separators; token counts abbreviated only in compact meters ("≈ 120k / 400k") with full numbers in the Budget tab. Currency only when pricing is trustworthy.

### 14.8 Localization

English only for MVP (PRD §20); strings live in a single resource layer so later localization is possible; no concatenated sentence fragments.

---

## 15. Responsive Behavior and Breakpoints

### 15.1 Breakpoints

| Name | Range | Tailwind-style token (proposal) |
|---|---|---|
| Mobile | 360–767 px | base (and `<md`) |
| Tablet | 768–1023 px | `md` = 768 |
| Desktop | 1024–1279 px | `lg` = 1024 |
| Wide | ≥ 1280 px | `xl` = 1280 |
| Extra-wide reading | ≥ 1600 px | center the content block (optional) |

Layouts are fluid within each range; below 360 px the layout must degrade gracefully (still no horizontal overflow) though 360 px is the supported minimum (UX-10).

### 15.2 Behavior summary by component

| Component | Mobile | Tablet | Desktop | Wide |
|---|---|---|---|---|
| Sidebar | Dialog | 64 px rail | 240 px (collapsible) | 240 px |
| Header | 56 px, menu button, title, overflow menu | 64 px | 64 px | 64 px |
| Investigation nav | Equal-width links, internal scroll if needed | Inline | Inline | Inline |
| Tracker | Compact row + expandable list | Horizontal | Horizontal | Horizontal |
| Budget strip | Wrap to 2–3 rows | One row | One row | One row |
| Secondary panel | Accordion | Accordion (or column if ≥ 560 px primary) | Accordion; column with rail | Docked column |
| Evidence | Full-height sheet | Overlay drawer | Overlay drawer | Docked panel |
| Dashboard list | Cards | Table | Table | Table |
| Sources | Cards | Table | Table | Table |
| Report | Toolbar wraps; TOC collapsible | Same | Same | TOC right column |
| Evidence Compare | Sequential groups | Two columns if ≥ 720 px content, otherwise sequential | Two columns | Two columns + claim list |
| Forms | Full width, sticky action bar | 720 px card | 720 px card | 720 px card |
| Modals | Full-width sheet ≤ 480 px | Centered | Centered | Centered |

### 15.3 Anti-overflow rules

- `min-width: 0` on all flex/grid children that contain text.
- `overflow-wrap: anywhere` on URLs, passage IDs and hashes (mono).
- Tables, code and Markdown tables scroll inside their own wrapper with a visible focusable scroll region (`tabindex="0"` with `role="region"` and label) so keyboard users can scroll it.
- Images (if any are allowed in reports) `max-width: 100%`; remote report images aren't loaded (§8.8).
- `html, body` never exceed `100vw`; verify with a viewport test at 360, 390, 768, 1024, 1280, 1440 px.
- Use `dvh` for full-height sheets; add `env(safe-area-inset-*)` padding.

### 15.4 Touch and pointer

44 px targets on touch (< 768 px or `pointer: coarse`); hover-only information always has a focus/tap equivalent; no reliance on hover for revealing actions (row action menus are visible).

### 15.5 Browser support

Chrome and Edge first (NFR-C2); Firefox and Safari after browser QA. Use of newer CSS (`dvh`, `:has`, container queries) must be confirmed against that support policy at implementation; fallbacks are required where Safari/Firefox support is uncertain.

---

## 16. Frontend Implementation Handoff

> No application code is provided or implied here. This section tells developers what to build and in what order.

### 16.1 Stack (planning defaults, D-04; final versions deferred to `ARCHITECTURE.md`)

React + TypeScript + Vite + Tailwind CSS; Radix UI primitives; Lucide icons. Routing library, state management, data-fetching and Markdown renderer are **not** decided here. Whatever is chosen must satisfy: route table (§7.4), sanitized Markdown with raw HTML disabled (SEC-18), accessible focus management on route change, and a single resource layer for strings.

### 16.2 Token delivery

1. Define §3.1–§3.4 as CSS custom properties on `:root` (dark theme = default, UX-01). Component styles consume **semantic** tokens only.
2. Map tokens into Tailwind's theme (colors, fontFamily, borderRadius, spacing aliases, breakpoints `md/lg/xl`) so utilities like `bg-surface`, `text-secondary`, `border-control`, `ring-focus` exist. Tailwind's default 4 px spacing scale matches §5.3.
3. Keep tokens in one source-controlled file; a V1 light theme later overrides the semantic layer only.
4. Provide a dev-only component gallery route or Storybook-equivalent showing every state in §12 (tooling choice deferred).
5. Do not use arbitrary Tailwind hex values in components; lint for it where feasible.

### 16.3 Fonts

Self-host per §5.1; place under a controlled static directory; include licenses; verify no network request to font CDNs in the browser network panel.

### 16.4 Icons

Import individual Lucide icons (tree-shaken); set `aria-hidden="true"` on decorative icons; icon size 16 px inline, 20 px nav, 48 px empty states; `currentColor` fill/stroke; stroke width 1.75–2.

### 16.5 Radix usage

Use Dialog (mobile nav, overlay drawer, modals), AlertDialog (destructive), Tabs (in-page panels), DropdownMenu (row actions), Select, Switch, Checkbox, RadioGroup, ToggleGroup, Collapsible/Accordion, Tooltip, Popover, Toast, VisuallyHidden, Progress (optional). Do **not** use Tabs for route navigation. The docked evidence panel is **not** a Dialog.

### 16.6 Build order by milestone

| Milestone | Frontend deliverables |
|---|---|
| **M0** | Tokens, fonts, Tailwind mapping, shell (sidebar, header, rail, mobile dialog), routing skeleton with placeholder pages, Button/Input/Textarea/Select/Switch/Checkbox/Card/Tooltip/Modal/Toast/Skeleton/EmptyState, focus ring, skip link, reduced-motion handling, contrast lint |
| **M1** | Dashboard (table/cards, status badges, delete), New Investigation, First-Run Wizard, Workspace (tracker, stage line, budget strip, claim blocks, citation chips, Limitations card), Plan panel (read-only), Sources Explorer (web), Evidence Drawer (Layer A checks, M1 note), Report Viewer (versions, download), Settings (providers, disclosure, limits, storage), banners/error patterns, offline handling |
| **M2** | Documents screen, FileUpload, per-file pipeline states, PDF locators/page labels in chips and drawer, extraction-quality badges, OCR-unavailable messages, plan editing (partial), embeddings settings |
| **M3** | AssessmentLabel and Layer B in drawer, assessment chips on claims, Evidence Compare (if promoted), Resume/Restart controls (when backend ready), Pause control if specified, history filters, source credibility signals and age warning, Settings additions |
| **M4** | Accessibility audit fixes, forced-colors/zoom/text-spacing fixes, performance tuning (NFR-P1, P4), usability-test fixes, final docs |
| **V1+** | §20 |

### 16.7 Feature flags / gating

A central capability map (`milestone → enabled features`) controls rendering of gated UI (§2.5). Gated components are not mounted when their flag is off; tests assert that "Resume", assessment labels, and Documents navigation are absent before their milestones.

### 16.8 Data and update contracts the UI assumes (to be confirmed in `API.md`)

| Assumption | Reason |
|---|---|
| Answer is delivered as structured claim blocks, each with text, citation passage IDs and claim state | Needed for ClaimBlock and chip rendering (DQ-08) |
| Each citation carries validation results (reference, belongs, quote) | Needed for Layer A rows |
| Run progress delivered through a mechanism that supports ≤ 1 update/s and a first update within 3 s | UX-03, NFR-P4 (polling vs push is an architecture choice) |
| Budget values carry an `estimated` flag | FR-11.2 |
| Sources expose status enum, retrieval timestamp, nullable date/author | FR-03.4, FR-W8 |
| Passages expose stable IDs, locator, offsets, ingestion version, and a removed flag | FR-05.3, FR-D9 |
| Secrets are never returned to the UI | SEC-08 |

### 16.9 Test hooks

Stable `data-testid` conventions for: status badge, phase tracker items, claim blocks, citation chips, drawer sections, check rows, source rows. Tests cover state matrices in §12, absence of gated features, keyboard flows, and reduced-motion variants.

### 16.10 Performance guidance

Dashboard must remain responsive with 200 investigations (NFR-P1); avoid re-rendering the whole answer on each progress tick (update only the stage line, tracker and meters at ≤ 1 Hz); lazy-load Compare and Report viewer code; no remote assets. Targets are proposals pending the benchmark policy (PRD §15, OQ-04).

---

## 17. Design Acceptance Criteria

Design is accepted per milestone when the items below pass review **and** the PRD ACs referenced are met. Items are testable by inspection or automated test.

| ID | Criterion | Milestone | PRD link |
|---|---|---|---|
| DA-01 | All five brand colors and supporting colors match §3 exactly; no other hues appear except derived tints (§3.3) | M0 | D-02, UX-01 |
| DA-02 | Every foreground/background combination in use appears in §4 as permitted; lint finds none of §4.7 | M0–M4 | NFR-A2 |
| DA-03 | Focus ring visible on every interactive control, ≥ 3:1 vs adjacent surface | M0 | UX-11, NFR-A |
| DA-04 | Three fonts self-hosted; no external font/network requests | M0 | SEC-02 |
| DA-05 | At 360, 390, 768, 1024, 1280, 1440 px no document-level horizontal overflow on every primary view | M1 | UX-10 |
| DA-06 | Sidebar, tabs, tracker, secondary panel and evidence mode switch at the §6.3 breakpoints | M1 | UX-02 |
| DA-07 | Every factual claim in the answer shows a valid chip or the "Not established" marker | M1 | FR-06.1 |
| DA-08 | Citation chip opens the drawer showing source title, locator, saved passage with highlight, retrieval time and Layer A checks | M1 | FR-06.6, UX-06 |
| DA-09 | No UI string in §14.4 appears; no numeric confidence appears | M1 | FR-06.7 |
| DA-10 | M1/M2 show **no** assessment labels, Resume, Pause, Compare or Documents (before M2) | M1–M2 | §2.5 |
| DA-11 | Each investigation status in §9.6 renders its banner, tracker marker and only its permitted actions; only Completed is labeled completed | M1 | UX-07, FR-11.3 |
| DA-12 | Budget strip shows five meters; tokens/cost marked estimate; cost hidden when untrustworthy | M1 | FR-11.2, FR-11.5 |
| DA-13 | All errors in §14.5 render using what-failed/what-saved/what-next | M1 | PRD §17 |
| DA-14 | Delete flows use AlertDialog with honest scope and failure copy | M1 | UX-09, FR-01.4 |
| DA-15 | Report viewer shows FR-07.1 sections, disclaimer, metadata without secrets, version selector, sanitized Markdown | M1 | FR-07, SEC-18, AC-16 |
| DA-16 | First-run wizard discloses data flow and requires acknowledgment before use | M1 | UX-08, SEC-03 |
| DA-17 | Settings never re-display a saved secret | M1 | SEC-08 |
| DA-18 | Upload UI shows pipeline states, specific rejection messages, scan/OCR warning | M2 | FR-04, FR-D, AC-12, AC-13 |
| DA-19 | PDF chips and drawer show physical page index (and printed label when reliable) | M2 | FR-D3 |
| DA-20 | Removed-source references display "Source removed" with no dead link | M2 | FR-D9 |
| DA-21 | Assessment labels show icon + word + "Automated" tag; drawer shows model and method; no percentages | M3 | FR-06.4 |
| DA-22 | Evidence Compare (if shipped) shows both sides, preserves original labels beside user overrides, and has equivalent mobile order | M3 | FR-09 |
| DA-23 | Resume/Restart appear only when backend support is verified | M3–M4 | FR-L2–L3 |
| DA-24 | Reduced-motion variant verified for every animated element | M4 | NFR-A5 |
| DA-25 | Automated a11y: zero critical/serious; manual keyboard pass on five flows | M4 | AC-17 |
| DA-26 | Forced-colors, 200% zoom and text-spacing checks pass | M4 | NFR-A1 |
| DA-27 | Four of five novice testers complete a report unassisted (design contribution to usability) | M4 | OBJ-7, AC-19 |

---

## 18. PRD Traceability Matrix

### 18.1 Screen-to-requirement matrix

| Screen / section | PRD requirements | Milestone | Verification |
|---|---|---|---|
| Dashboard §8.1 | FR-01.2–.5, FR-08.1–.2, FR-08.4, FR-11.3, UX-07, NFR-P1, NFR-X1, ERR-15 | M1 (filters M3) | AC-01, UX review, DA-05/11 |
| New Investigation §8.2 | FR-01.1, FR-02.2, FR-11.1, FR-11.5, SEC-03, ERR-03 | M1 | AC-01/02, DA-12/16 |
| Workspace §8.3, §9 | FR-02.2, FR-06.1–.7, FR-11, FR-L1–L5, UX-03–07, ERR-01–13/17 | M1 | AC-03/06/09/11, DA-07/11/12/13 |
| Plan panel §8.4 | FR-02.1–.2, FR-02b.1–.2, FR-P3, ERR-10 | M1 read-only; M2–M3 edit | AC-02 |
| Sources §8.5 | FR-03.2–.5, FR-10, FR-W6–W10, FR-D3, FR-D9, UX-04, ERR-04/05 | M1 (+M2, M3) | AC-03/09, DA-19/20 |
| Evidence drawer §8.6, §10 | FR-06.2–.7, FR-05.3, FR-D2/D3/D9, UX-04–06, NFR-A3, ERR-11 | M1 (+M2, M3) | AC-06, DA-08/21 |
| Documents §8.7 | FR-04, FR-05.4, FR-08.3, FR-D1–D9, SEC-15–17, ERR-08/09 | M2 | AC-04/12/13, DA-18 |
| Report viewer §8.8 | FR-07.1–.5, FR-P2, FR-D9, SEC-18, UX-06 | M1 | AC-06/16, DA-15 |
| Settings §8.9 | SEC-01–09, FR-11.1, FR-W2, FR-W9, FR-10.3, NFR-X1, UX-08 | M1 | AC-15, DA-17 |
| Evidence Compare §8.10 | FR-09.1–.4, ERR-06, UJ-3 | M3 Should | AC-08 (if shipped), DA-22 |
| Setup wizard §8.11 | UX-08, SEC-03, SEC-06/08, ERR-03 | M1 | DA-16 |
| App shell §6, routes §7 | UX-02, UX-10, UX-11, D-02 | M0–M1 | DA-05/06 |
| Tokens/contrast §3–5 | UX-01, NFR-A2, NFR-A4, NFR-A5 | M0 | DA-01–04 |
| Accessibility §13 | NFR-A1–A5, UX-05, UX-11 | M0–M4 | AC-17, DA-25/26 |
| Microcopy §14 | PRD §17, FR-06.7, §8 (risks) | M1 | DA-09/13 |

### 18.2 Requirement-to-design lookup (UX, NFR-A, selected FR)

| Requirement | Satisfied in |
|---|---|
| UX-01 dark theme, tokens in DESIGN | §3–5 |
| UX-02 responsive collapsible nav | §6, §15 |
| UX-03 stage, source count, budget updates | §9.2–9.5 |
| UX-04 source/evidence cards with excerpt, provenance, status | §8.5, §8.6 |
| UX-05 text+icon for unsupported/uncertain/contested | §2.4, §9.4, §12.4–12.6 |
| UX-06 citation opens saved passage; external link marked | §10 |
| UX-07 empty/loading/paused/failed/budget/partial states | §8.0.4, §9.6, §9.9 |
| UX-08 first-run wizard | §8.11 |
| UX-09 confirm destructive | §8.9a |
| UX-10 360 px, no overflow | §6.3, §15 |
| UX-11 keyboard, focus, labels, reduced motion | §13 |
| NFR-A1/A2/A3/A4/A5 | §13, §4, §10.6, §13.5, §5.6 |
| FR-06.1–.7 | §2.3, §9.4, §10 |
| FR-07 | §8.8 |
| FR-11 | §8.2, §9.5, §9.7 |
| FR-L2–L3 | §9.6 (gated), §19 |
| FR-D3, FR-D9 | §8.5–8.8, §10 |
| FR-09 | §8.10 |

### 18.3 Error-to-UI lookup

| ERR | Surface |
|---|---|
| 01, 02 | Workspace banner + Activity (§9.9) |
| 03 | Banner + Settings; wizard (§8.9, §8.11) |
| 04, 05 | Sources row detail (§8.5) |
| 06 | Compare / Conflicting evidence (§8.10, §9.4) |
| 07, 11 | Claim block "Not established" (§9.4) |
| 08, 09 | Documents (§8.7) |
| 10 | Plan panel / banner (§8.4, §9.9) |
| 12 | Interrupted banner (§9.6) |
| 13 | Budget-reached banner + tracker (§9.5–9.6) |
| 14 | Toast/banner (§14.5) |
| 15 | Offline banner (§8.0.4) |
| 16, 17 | Limitations + notices (§9.4, §9.9) |

---

## 19. Open Questions and Deferred Decisions

### 19.1 Differences and tensions between the handoff brief and PRD v1.1.0

The PRD is authoritative. Where the handoff brief and PRD differ or are silent, this document follows the stated resolution.

| ID | Observation | Resolution used here |
|---|---|---|
| R-1 | The brief lists "Document Library" as an M2 screen; PRD FR-08.3 makes a *cross-investigation library* a Should (M3). | M2 Documents screen = upload, validate, list, remove, attach to an investigation (PRD §14 "PDF library (M2)"). Cross-investigation retrieval/opt-in library (FR-05.4, FR-08.3) is M3 Should/V1 and not designed as available earlier. |
| R-2 | The brief says Resume is not functional until implemented. PRD FR-L2 specifies "Resume or Restart" but defers resumable execution to M3–M4. | M1/M2: no Resume button. Whether a plain **Restart** ships in M1 is open (DQ-02). |
| R-3 | PRD §7.2 says FR-06 is delivered "M1; semantics strengthened M3". The brief places semantic assessments in M3. | Layer B labels hidden in M1–M2; M1 shows only Layer A checks plus the "Not established" rule-based marker. If the owner wants a minimal assessment in M1, the already-designed M3 components can be switched on earlier without redesign. |
| R-4 | The PRD's FR-06.1 allows "Unsupported/Not established" for uncited claims; the brief's Layer B also uses "Unsupported". | "Not established" = rule-based, no valid citation (M1+). "Unsupported" = AI assessment (M3). Distinct words prevent conflation. |
| R-5 | PRD defines *stance* labels (supports/contradicts/neutral/uncertain, FR-09.1) separately from *claim assessment* labels (FR-06.4). The brief mentions only the latter. | Two vocabularies kept separate (§8.10). |
| R-6 | The brief's five phases (Plan, Discover, Read, Check, Report) vs the PRD's ten stages. | Mapping in §9.2; Draft grouped under Read (DQ-01). |
| R-7 | The PRD lists **Paused** as a state but defines no user-facing pause control. | Paused displayed if produced (FR-L4); no Pause button (DQ-03). |
| R-8 | The PRD requires offline behavior (ERR-15), storage warnings (NFR-X1), export-time revalidation (FR-07.2), and a "Source removed" state (FR-D9); the brief does not mention them. | Added to the design (§8.0.4, §8.1, §8.8, §10). |
| R-9 | The PRD marks M1 "Awaiting approval" optional and says M1 may use explicit Start confirmation (FR-02b.2). | M1 label "Ready to start" with a Start button; plan approval switch appears with FR-02b. |
| R-10 | The brief names a handoff file `PRD.md`; the supplied file is `PRD__1_.md`. | Treated as the same PRD (v1.1.0 header confirmed). |

### 19.2 Open design questions

| ID | Question | Needed by | Resolve in |
|---|---|---|---|
| DQ-01 | Should Draft sit under *Read* or *Check* in the tracker? | M1 | Owner review of this document |
| DQ-02 | Does a plain **Restart** (new run, same question) ship in M1, or only with M3 Resume? | M1 | PRD / owner |
| DQ-03 | Is a user **Pause** control wanted, and in which milestone? | M3 | PRD / owner |
| DQ-04 | Final M1 label for Awaiting approval ("Ready to start" vs "Awaiting approval") | M1 | Owner review |
| DQ-05 | Title length limit (proposed 120) | M1 | DATABASE/API |
| DQ-06 | Hard maximums for each run limit (FR-11.1 "safe hard maximums" unspecified) | M1 | ARCHITECTURE / SECURITY |
| DQ-07 | Is the question immutable after creation? | M1 | PRD |
| DQ-08 | Claim granularity and structure of the answer payload; whether drafts stream | M1 | API / PROMPTS |
| DQ-09 | Passage ID format shown to users and in reports (for example `P-0042`) | M1 | DATABASE / API |
| DQ-10 | Report version creation triggers before M3 (only the initial report in M1?) | M1 | PRD / API |
| DQ-11 | Credential "Test connection" control in Settings/wizard (useful but not in PRD) | M1 | INTEGRATIONS |
| DQ-12 | Dashboard pagination above 200 investigations | M3 | Benchmark (OQ-04) |
| DQ-13 | Sources status filter (design convenience, not in PRD) — keep or drop? | M1 | Owner |
| DQ-14 | Behavior of upload/extraction when offline and hosted embeddings configured | M2 | ARCHITECTURE |
| DQ-15 | In-app PDF page rendering vs passage text only | M2/V1 | Owner |
| DQ-16 | Whether derived colors in §3.3 (destructive hover/pressed, tints) are approved | M0 | Owner |
| DQ-17 | Provider names and logos in Settings (OQ-01/OQ-02 unresolved) | M1 | INTEGRATIONS |
| DQ-18 | Minimum viable keyboard shortcut set (none required) | M4 | Usability results |

### 19.3 Deferred by PRD

OQ-01 search provider; OQ-02 LLM provider and cost controls; OQ-03 embeddings and vector store; OQ-04 reference hardware; OQ-05 license/distribution; OQ-06 groundedness reviewers; D-04–D-06 architecture defaults; light theme (V1); OCR, local LLM, multi-user (Future).

### 19.4 Assumptions made in this document

1. Contrast values are computed, not tool-verified (re-run with tooling at M0 and after token changes).
2. Icon names are from Lucide's naming as known today; confirm at the pinned version.
3. Panel widths (240/64/320/400) and the 720 px reading column are design proposals validated only by arithmetic in §6.3, not by user testing.
4. Local UI preferences (sidebar state, "How to read this" dismissal) may use browser local storage; research data does not (it lives in the local backend).
5. Tooltips, toasts and transitions use the timings in §5.6; usability testing (OBJ-7) may adjust them.

---

## 20. Future Design Enhancements

Everything here is **not** part of the MVP design contract.

| Item | Source | Notes |
|---|---|---|
| Light theme | UX-01, V1 | Swap the semantic token layer; recompute all contrast pairs; the Sounding Line needs a dark-on-light equivalent |
| Citation style presets (APA/MLA/IEEE) | FR-12 (V1) | Reference formatting in Report Viewer |
| PDF/DOCX export | FR-13 (V1) | Export dialog with validation-at-export messaging |
| BibTeX and archive export | FR-14 (V1) | Portable investigation export (NFR-D1) |
| Cross-investigation library UX and library-wide retrieval opt-in | FR-08.3, FR-05.4 | Opt-in flow with explicit scope disclosure |
| Advanced conflict analysis | FR-09 (V1) | Timelines, claim clustering; keep "both sides shown" rule |
| Source credibility signals visualisation | FR-10 | Always heuristic, never truth scores |
| Scanned-PDF OCR | FR-15 (Future) | Replaces the OCR-unavailable messages; quality badges extend |
| Local LLM option | FR-16 (Future) | Settings provider card, sensitive-document mode (SEC-05) |
| Multi-user and collaboration | FR-17 (Future) | Requires auth screens and sharing models; outside MVP |
| JS-rendered fetch | Future | New source statuses |
| Drawn Sounding Line connector between claim and docked drawer | §3.6 | Optional visual refinement; must remain subtle and respect reduced motion |
| In-app PDF page rendering with excerpt highlight | DQ-15 | Larger drawer layout |
| User-defined keyboard shortcuts | DQ-18 | Only if usability testing shows value |
| Dashboard visual analytics | — | Not requested; avoid until it serves the "evidence first" principle |

---

*End of document — DeepTrace AI design specification v1.0.0 (draft). Next document in the PRD §23 order: `docs/INTEGRATIONS.md`.*
