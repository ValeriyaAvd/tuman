# Production art prompts

Mode: built-in ImageGen. Inputs: original PNG files preserved under `v1/`.
Generated source sheets are under `generated/`. Native-frame fitting uses nearest-neighbour
sampling, bounded palettes and binary alpha; this file records the drawing prompts.

## Hero

Edit target: the supplied production sprite sheet for a top-down psychological horror game.
Redraw it with twice as much pixel-art detail, crisp hand-placed pixels, a restrained PS1-era
32-bit pixel-art mood, NO smoothing, muted olive-brown jacket, grey-brown trousers, dark worn
boots, pale tired face, short brown hair. Preserve EXACTLY the 5 columns by 3 rows, same frame
order and same pose/silhouette/foot alignment in every cell. Row 1 facing down; row 2 facing up;
row 3 facing right. Each row has idle then four walking frames. This is a functional sprite sheet,
NOT a concept illustration. No text, borders, ground, shadows outside sprites, extra cells, weapons
or scenery. Transparent background. Add jacket seams, collar, pockets, subtle cloth folds, hair
clusters and boot soles while keeping silhouette recognizable. Output tightly aligned evenly-spaced
5x3 sprite sheet; intended native sheet 120x114 pixels, 24x38 pixels per frame; may output exact
integer upscale of that sheet. Keep each frame in its own equal cell without crossing boundaries.

## Monster

Production sprite sheet edit, two columns and ONE row only, transparent background. Redraw the
provided 2-frame top-down horror monster with higher-resolution crisp 32-bit-style pixel art; exact
target two 24x40 pixel frames, may output an integer upscale. Preserve original creature: faceless
pale grey humanoid with distorted sack-like head, long gaunt arms, hunched narrow torso, dirty dark
reddish-brown trousers, heavy uneven gait. First frame standing, second frame one walking step.
Restrained fog-town psychological horror atmosphere, damp cloth, mottled grey skin, fine seams and
folds. NOT cute, NOT anime, NOT zombie gore. Both frames exactly same scale, baseline, centered in
equal cells with transparent padding. Flat pixel clusters and sharp edges, no blurred painting,
background, text, extra creatures, props, shadows, borders or grid.

## Items

Redraw these game item sprites into ONE organized production sheet, exactly 3 columns by 2 rows
of equal square cells, one object centered per cell, transparent background. Order: top left worn
horizontal metal flashlight aimed RIGHT (inventory icon); top middle damp yellowed handwritten
folded note; top right diagonal rusty iron pipe (inventory icon). Bottom left a longer diagonal pipe
lying on ground with tiny rust flakes but no ground; bottom middle a small horizontal flashlight
side view aimed RIGHT switched off; bottom right EXACT SAME side view flashlight aimed RIGHT
switched on, warm yellow glass only (no cone or bloom). Retain each original design, subdued grey
brown olive palette, crisp detailed pixel art with 32x32-pixel native cells (integer upscale allowed).
Show metal rim, small switch, grip ribs; pipe's scratched steel and rust; paper creases, torn corners
and tiny illegible writing. No labels, captions, cell outlines, grid, scenery, hands, extra items or
soft painting. High contrast readable tiny game icons; every cell has clear transparent margins.

### Transparency refinement

Precise background extraction on this game sprite sheet. Remove ALL dark background, colored
clouds, glows, halos and shadows outside the six objects. Make the entire space between/around
objects truly alpha-transparent. Keep the exact 3-column 2-row layout, each object's position and
pixel design unchanged. Keep the warm glass INSIDE bottom-right flashlight, but zero exterior
glow. Preserve the sprites' opaque interiors and crisp pixel contours. Do not add any background
or checkerboard; real transparency required.

## Hero revision: supplied JRPG reference

Built-in ImageGen. Reference: `assets/references/hero_ref.png`.
Saved drawing: `generated/hero-ref-v3.png`; packed game asset: `data/hero.png`.

Use the attached game screenshot as a STYLE AND PROPORTION reference only. Create a production
character sprite sheet for an ORIGINAL male protagonist of a foggy abandoned-town horror game.
Match the screenshot's compact JRPG/chibi pixel proportions: large round head about 45 percent of
total height, readable dark eyes, chunky layered brown hair, short body and boots, clean clustered
pixels and muted atmospheric colors. Keep protagonist outfit a worn muted olive jacket over charcoal
shirt, brown-grey trousers and dark boots. Adult tired serious expression, no school uniform.
EXACTLY FIVE COLUMNS and THREE ROWS of equal cells. Row 1 facing DOWN, row 2 facing UP,
row 3 facing RIGHT. Each row: idle, then 4 distinct walking poses. Every frame the same scale and feet
baseline, centered, limbs inside the cell. Target game-native frame 24x38 pixels (sheet120x114);
output an enlarged sprite sheet fitting that exact 5:3 grid for later nearest-neighbour fitting.
Transparent background with no exterior shadows, NO grid lines, labels, text, scenery, weapons,
accessories, extra rows, lighting halos, perspective or blur. Detailed but clearly pixel art as in
reference, not painted realism. Make hands visible and consistent near the lower jacket so equipment
can attach.
