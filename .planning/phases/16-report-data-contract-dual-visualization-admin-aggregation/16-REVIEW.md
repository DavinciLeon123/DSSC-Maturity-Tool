---
phase: 16-report-data-contract-dual-visualization-admin-aggregation
reviewed: 2026-07-28T17:26:43Z
depth: standard
files_reviewed: 3
files_reviewed_list:
  - backend/app/services/report_generator.py
  - backend/app/templates/report.html
  - backend/tests/services/test_report_generator.py
findings:
  critical: 2
  warning: 2
  info: 2
  total: 6
status: issues_found
---

# Phase 16: Code Review Report

**Reviewed:** 2026-07-28T17:26:43Z
**Depth:** standard
**Files Reviewed:** 3
**Status:** issues_found

## Summary

Scope: gap-closure plan 16-05 (commits `271a543` fix(16-05) position-aware
radar text-anchor + widened viewBox [G-16-1], and `61ec7a4` fix(16-05)
flatten priority-row/legend to single-level flex [G-16-2]), diffed against
`2d45ae0fde646a8060c3087bd3ea8e7763ef7e55`. This supersedes the phase's prior
16-REVIEW.md (17-file, full-phase review) for these 3 files only.

**What was verified as correct:**
- `anchor_for()`'s angle math is correct: traced through n=3, n=4, and the
  real 6-category config by hand and by executing `generate_radar_svg()`
  directly — for the real config it produces exactly 2 "middle" (top/bottom),
  2 "start" (right side), 2 "end" (left side) anchors, matching the new
  tests. The longest real category name ("Control over Data & Trust", 25
  chars, index 4) lands on an "end"-anchored left-side axis and, per manual
  computation of its rendered `x` position against the new `viewBox`, has
  ~210px of margin available against an estimated ~165px text-width need —
  not clipped.
- `xml_escape(s["name"])` (threat T-16-05-01 / WR-05) is still applied
  unconditionally before every `<text>` interpolation — the gap-closure diff
  only added the `text-anchor` attribute (a fixed enum value, no injection
  surface) and did not touch the escaping call. Confirmed both by reading
  the diff and by the still-passing
  `test_radar_svg_escapes_special_characters_in_category_name`.
- The flattened `.priority-row`/`.legend-item` HTML structure genuinely
  removes the nested-flex-in-flex shape that triggered the WeasyPrint 69.0
  bug (confirmed via diff: no flex container is nested inside another flex
  container post-fix).

**What is not correct — two BLOCKERs found by tracing through CSS/SVG
layout mechanics rather than by pattern-matching the diff:**
1. Widening the radar SVG's `viewBox` (G-16-1) changes its aspect ratio from
   square to ~2.1:1 wide, which — combined with `report.html`'s *unchanged*
   `.radar-wrap svg { width: 100%; max-width: 360px; height: auto; }` —
   causes the browser/WeasyPrint to render the entire chart (hexagon **and**
   all `font-size="11"` text) at roughly half its previous scale, because
   `height: auto` derives from the SVG's now much-wider intrinsic aspect
   ratio. See CR-01.
2. The G-16-2 flatten makes the score column's x-position independent of the
   *preceding* `.priority-name`'s width (as claimed and tested), but not of
   the *following* `.priority-band-label`'s width — and real maturity-band
   labels vary substantially in length ("Needs attention" vs "Mature").
   Traced through the flexbox free-space distribution algorithm by hand: the
   score column's actual screen position shifts per row by the difference in
   adjacent label width, so scores still won't line up vertically across
   rows whenever a report spans more than one maturity band (the normal
   case). See CR-02.

Neither regression would be caught by `test_report_generator.py`, since
every assertion there operates on the raw SVG/HTML string (attribute
presence, CSS rule text, substring containment) rather than on
computed/rendered layout — see IN-02.

## Critical Issues

### CR-01: Widened radar-chart viewBox shrinks the whole chart (and its text) to roughly half size via the unchanged CSS aspect-ratio-locked sizing

**File:** `backend/app/services/report_generator.py:202-220`, interacting with `backend/app/templates/report.html:59`

**Issue:** G-16-1 widens the SVG's `viewBox` horizontally to give
outward-growing labels room:
```python
horizontal_margin = (longest_name_len * label_font_size * avg_char_width_factor) + 10
view_min_x = -horizontal_margin
view_width = size + 2 * horizontal_margin
...
f'<svg viewBox="{view_min_x:.1f} 0 {view_width:.1f} {size}" ...'
```
For the real 6-category config this produces `viewBox="-175.0 0 670.0 320"`
(verified by executing `generate_radar_svg()` directly against
`config/dssc-questionnaire.json`) — an aspect ratio of `670/320 ≈ 2.09`,
versus the previous `320/320 = 1.0` (square).

`report.html`'s CSS for this element is untouched by this diff:
```css
.radar-wrap svg { width: 100%; max-width: 360px; height: auto; }
```
Because the `<svg>` has a `viewBox` but no explicit `width`/`height`
attributes, `height: auto` resolves via the element's *intrinsic aspect
ratio*, which is now the widened viewBox's ratio. At the CSS cap of
`width: 360px`, the computed height becomes `360 / 2.09 ≈ 172px` — down from
`360px` (a square) before this fix. Since every coordinate in the SVG (the
hexagon polygon, the axis spokes, and every `font-size="11"` `<text>`
label) is scaled by the same uniform factor to fit that box, the effective
on-screen scale drops from `360/320 ≈ 1.125×` to `360/670 ≈ 0.537×` —
roughly **2.1× smaller** than before. Concretely, the 11-unit SVG label
font renders at ~`12.4px` before this fix and ~`5.9px` after it: the axis
labels — the very thing G-16-1 was fixing to stop clipping — become close
to illegible instead of clipped, and the chart itself shrinks to less than
half its intended visual footprint in both the in-app card and the
fixed-width PDF page (the exact rendering context this function's own
docstring calls out: "scales in both the responsive in-app card and the
fixed-width PDF page").

This bug reproduces for the real production config today (not a
hypothetical edge case), and would also affect the admin org-average
chart, which this module's docstring states reuses the same
`generate_radar_svg()` output verbatim.

**Fix:** Size the `<svg>` by its intended visual height instead of a width
cap, so a wider viewBox no longer forces a shorter render:
```css
.radar-wrap svg {
  height: 320px;      /* match the intended visual chart size */
  width: auto;
  max-width: 100%;    /* still shrink gracefully on narrow viewports/PDF pages */
}
```
Alternatively, keep width-based sizing but decouple the label margin from
the rendered viewBox's aspect ratio — e.g. render the labels in a
fixed-height overflow area outside the scaled `viewBox`, or clamp
`view_width` growth so the ratio never exceeds a bound the CSS is built to
tolerate. Either way, this needs a real rendered-pixel check (browser or
WeasyPrint screenshot), not just a viewBox-string assertion, before it can
be called fixed — see IN-02.

---

### CR-02: Score column position still depends on a variable-width sibling (`.priority-band-label`), so scores won't align across rows with different maturity bands

**File:** `backend/app/templates/report.html:69-103, 172-177`

**Issue:** G-16-2's fix makes `.priority-score`'s position independent of
`.priority-name`'s width (the specific WeasyPrint bug that was reported and
the specific thing `test_priority_score_column_css_has_fixed_width_and_right_align`
checks for) — that part is correctly fixed. But the flex row is:
```
[band-dot] [priority-name: flex:1, flex-basis:0] [priority-score: min-width:48px] [priority-band-label: no flex, content width]
```
`priority-name` is the *only* flex-grow item, so per the flexbox algorithm
it absorbs `container_width - (dot + score + label + 3×gap)` — i.e. its
resolved width (and therefore where the score column starts) is a function
of `.priority-band-label`'s content width, which is **not fixed**. Real
maturity-band labels vary substantially:
```
"Needs attention"  (red)     — 15 chars
"Developing"       (orange)  — 10 chars
"Mature"           (green)   — 6 chars
```
(confirmed against `config/dssc-questionnaire.json`'s `maturity_bands`).
Working through the free-space distribution by hand: `score`'s left edge =
`container_width - score_width - label_width - 2×gap`. Since this
formula's only per-row variable is `label_width`, a row banded "red" (long
label) will render its score column measurably further left than a row
banded "green" (short label) — by roughly the pixel-width difference
between "Needs attention" and "Mature" (tens of pixels at 13px font). Any
report whose 6 dimensions span more than one maturity band — the ordinary
case, since `build_priority_list` explicitly always returns all 6
dimensions sorted by score rather than filtering to one band — will still
show a visibly staggered score column, which is the exact user-facing
symptom (UAT bug) this gap-closure round was meant to eliminate.

**Fix:** Give the trailing column a fixed width too, so only
`.priority-name` (the genuinely variable-length field) absorbs free space:
```css
.priority-band-label {
  font-size: 13px;
  color: rgba(6,0,79,0.65);
  white-space: nowrap;
  min-width: 120px;   /* fixed-width column: keeps score's position independent
                          of which band's label follows it */
}
```
(size `120px` to the longest real label, "Needs attention", plus margin —
same technique already used for `.priority-score`). Alternatively, switch
`.priority-row` to CSS Grid with explicit fixed-width trailing columns
(`grid-template-columns: auto 1fr auto 140px`), which guarantees column
alignment regardless of any one cell's content length — this is the layout
primitive actually suited to "align a column across rows," which
flexbox's single-item free-space model does not provide by construction.

## Warnings

### WR-01: Flatten widened the band-dot-to-name-text gap from 4px to 16px, an apparently unintended visual regression

**File:** `backend/app/templates/report.html:69-75` (compare with pre-fix `.priority-name { display:flex; gap:4px; ... }`, now removed)

**Issue:** Before this diff, `.priority-name` was itself a flex container
with `gap: 4px` between its nested `.band-dot` and the name text — a tight
badge-to-label pairing. After flattening, `band-dot` and `priority-name`
are now direct siblings of `.priority-row`, which has a single
`gap: 16px` applying uniformly between *all four* children (dot→name,
name→score, score→label). The dot is now 4× further from its label than
before. This is a real visual side effect of the fix (not called out in
the docstring/comments, which only discuss the WeasyPrint bug and the
score-column requirement), and it's inconsistent with `.legend-item`'s
deliberately-preserved 8px dot-to-label spacing (`margin-right: 8px`) in
the same template — the same visual element (a maturity-band dot next to
a label) now has three different spacings in one document (4px pre-fix /
16px in the priority list / 8px in the legend).

**Fix:** Give `.band-dot` its own explicit spacing in the `.priority-row`
context instead of relying on the row's uniform gap, e.g.:
```css
.priority-row { display: flex; align-items: center; padding: 16px 0; border-bottom: 1px solid #f0f0f0; gap: 16px; }
.priority-row .band-dot { margin-right: -8px; }  /* claw back 8px of the 16px row gap to match the legend's 8px */
```
or restructure the gap so the dot uses `margin-right` explicitly and the
row's `gap` only applies to the remaining (name/score/label) boundaries.

### WR-02: `anchor_for()` re-derives the same axis angle formula as `point()` — duplicated math that can silently drift

**File:** `backend/app/services/report_generator.py:153-164`

**Issue:** `point()` and the new `anchor_for()` both independently compute
`angle = (2 * math.pi * i / n) - (math.pi / 2)`. They are correct and
consistent today (verified: the code renders exactly 2/2/2
middle/start/end for the 6-axis config, matching the axis positions
`point()` draws), but the two functions have no shared source of truth — a
future change to the angle offset or direction in one (e.g. adjusting the
`-pi/2` start offset, or reversing axis winding) would silently
desynchronize label anchoring from actual axis position unless both call
sites are remembered and updated together.

**Fix:** Factor the angle computation into a single helper both functions
call:
```python
def axis_angle(i: int) -> float:
    return (2 * math.pi * i / n) - (math.pi / 2)

def point(i: int, value_fraction: float) -> tuple[float, float]:
    angle = axis_angle(i)
    r = radius * value_fraction
    return (cx + r * math.cos(angle), cy + r * math.sin(angle))

def anchor_for(i: int) -> str:
    cos_angle = math.cos(axis_angle(i))
    ...
```

## Info

### IN-01: `avg_char_width_factor = 0.6` is an unvalidated heuristic for a proportional (non-monospace) font

**File:** `backend/app/services/report_generator.py:207-208`

**Issue:** `horizontal_margin` is estimated as
`longest_name_len * label_font_size * 0.6 + 10`, a rough average-character-
width approximation for the Rubik font at 11px. This is reasonable and,
per manual calculation against the real config's longest name, currently
leaves a comfortable buffer (~45px) rather than being right at the edge.
But it's an estimate with no runtime feedback loop (no actual
text-measurement, e.g. via a font-metrics table) — if a future
admin-editable questionnaire (explicitly flagged as a future risk in this
same function's docstring) introduces a much longer or wider-character
category name, this heuristic could under-provision the margin and
reintroduce clipping with no test or assertion to catch it.

**Fix:** Not urgent given today's config, but worth a code comment
cross-reference to this ticket, or (stronger) a minimum-margin floor
derived from a worst-case per-character width rather than an average, e.g.
bias `avg_char_width_factor` upward (e.g. 0.65-0.7) to trade a little extra
margin for a larger safety buffer, since CR-01's fix will decouple margin
growth from overall chart shrinkage.

### IN-02: No test in `test_report_generator.py` observes actual rendered layout — both CR-01 and CR-02 pass every existing assertion

**File:** `backend/tests/services/test_report_generator.py:96-121, 307-322`

**Issue:** `test_priority_score_column_css_has_fixed_width_and_right_align`
only regex-matches that the `.priority-score` CSS rule contains
`min-width` and `text-align: right` declarations — it does not (and, as a
pure-Python unit test without a layout engine, cannot) verify that the
score column actually renders at a consistent x-position across rows with
differing band labels (CR-02). Likewise
`test_radar_svg_viewbox_widened_horizontally` only checks that
`min_x < 0` and `width > height` as raw numbers — it never checks the
resulting aspect ratio against the template's CSS sizing rules, so it
can't catch CR-01's chart-shrinkage regression. Both bugs are real,
reproduce with the shipped production config, and are invisible to this
test suite by construction.

**Fix:** For layout-sensitive fixes like these, add (even a lightweight)
rendered-output check — e.g. a Playwright/WeasyPrint snapshot test that
measures the actual pixel bounding boxes of `.priority-score` across two
rows with different band labels, and the actual rendered `<svg>` height at
the CSS-capped width — before marking G-16-1/G-16-2 done. Pure
string/regex assertions on markup are a reasonable smoke test but should
not be treated as proof that a visual-alignment bug is fixed.

---

_Reviewed: 2026-07-28T17:26:43Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
