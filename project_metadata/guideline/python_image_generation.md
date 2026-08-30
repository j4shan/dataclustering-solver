# Python image generation

How the project's raster figures are made during authoring. There is no image model in the loop:
a figure is drawn by a deterministic Python program. That program is a temporary production tool;
after the rendered PNG passes visual review, retain the prompt and accepted PNG and remove the
renderer and any private drawing helper.

## Authoring set and retained pair

| Artifact | Role |
| --- | --- |
| `resources/img_prompt/<figure>_prompt.txt` | the retained **specification** — format, palette, type scale, instance, layout, what to keep out |
| `tools/render_<figure>.py` | the temporary **renderer** — the only implementation while the figure is being produced |
| `resources/img/<figure>.png` | the retained **accepted output** |

Keep the prompt and the renderer in step. When the render cannot do what the prompt describes,
change the prompt — a prompt that describes a figure nobody drew is worse than no prompt. Once
the output is accepted, delete the renderer; later visual changes start a new authoring pass rather
than claiming the retained PNG can still be reproduced from source.

## Rules that earned their place

**Author the instance as data, derive every number.** Item lists, group membership and which
containers are touched live in one dict at the top of the renderer. Counts printed in the figure
are computed from it. Nothing in a figure is a typed-in number, so a changed instance cannot
leave a stale total behind.

**Draw at 2× and downsample once with LANCZOS.** Small type, hatch lines and hairline rules are
otherwise ragged. Do it at the end, in one place — never per element.

**Encode state on three channels, never on colour.** Fill *and* shape *and* a word. Reserve shape
for one meaning only, and say in the legend which meaning it carries; a shape doing double duty
(packaging *and* selection state) will be misread.

**Fonts.** Load `SFNS.ttf` / `SFNSMono.ttf` from `/System/Library/Fonts` and select weight with
`set_variation_by_name` — the SF variable fonts expose `Regular`…`Bold`. Cache by
`(size, weight, mono)`. Use `anchor=` rather than measuring by hand.

**Draw glyphs, do not type them.** A check mark set as text depends on a face that may not haveFol
it, and `.notdef` renders as a box that passes a naive "is it blank" test. Two lines cost less.
The same goes for Unicode subscripts.

**Composite silhouettes need a mask.** To hatch or fill a shape made of several primitives, draw
the primitives into an `L` mask and paste through it. Paste coordinates must be `int` — Pillow
raises on floats, and the accumulator in a laid-out row will produce them.

## Failure modes already paid for

**A figure that takes minutes is hung, not slow.** A static 1920 × 1080 frame renders in about
0.2 s. If it does not, stop optimising and find the loop: `faulthandler.dump_traceback_later(25,
exit=True)` names the line.

**Dashed paths: walk by remaining length.** Carrying dash phase across corners by subtracting an
accumulator goes negative whenever `dash > gap`, which drives the walk position backwards and
never terminates. Track "distance left in the current dash", flip state when it reaches zero.

**Full-canvas per-frame work is the cost.** Blur and composite dominate, not the frame count. A
blur is low-frequency: blur at quarter size and upscale. For any animation, redraw only the
bounding box of what changed.

**Show a thing leaving its place, and it must clear that place.** An element drawn as pulled out
of a slot must move further than its own width, or it covers the slot it left and the point is
lost. Link the two with a connector so the pairing is explicit.

**Labels belong where there is room.** Four names will not fit across one narrow container. Draw
the silhouettes in place and name the items where they land. Keep arrow tags ~20 px clear of the
shaft, and check that a tag centred on a curve's midpoint does not sit on the curve.

## Verify by looking

Read the rendered PNG back and inspect it. Collisions, clipping and overlap are invisible in the
source and obvious in the image. Assertions about layout that the eye can check in one pass are
not worth writing as tests; the instance-derived counts are.
