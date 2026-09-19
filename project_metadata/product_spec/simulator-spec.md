# Product Specification — dataclustering-solver

| Column | Meaning |
| --- | --- |
| **Type** | `F` functional · `NF` non-functional |

---

## 1. Product scope

| # | Requirement | Type |
| --- | --- | :-: |
| 1.1 | The problem being solved is the assignment of events to storage containers so as to minimize the volume read but not selected, given an observed selection history. | F |
| 1.2 | The project ships **no assignment strategy**, and no means of scoring one. It states the problem, the measures it is judged by, and what deploying a layout on a production engine involves. Naming a strategy as the answer is outside what it claims. | F |
| 1.3 | Skipping is treated in a *logical* sense throughout — which containers a query would open and what that would cost. Nothing here executes a query against a storage system, and no figure is a wall-clock read time. | NF |
| 1.4 | Every worked figure is indicative, not predictive. A small margin between two layouts is to be read as no margin. | NF |
| 1.5 | The system has **two targets and no external service dependency**: a local page served from loopback by a process on a single developer machine, and the same `site/` tree served as static files from a public host. Both are the authored tree as it sits. Neither reaches a third-party network, and the page itself fetches nothing from off its own origin (12.2.2). | NF |
| 1.6 | The **presentation page** is the product. It authors no number; each section's content lives in its own product spec. | F |

---

## 3. Domain model

| # | Requirement | Type |
| --- | --- | :-: |
| 3.1.1 | Demand is recorded as a **two-column selection log** — `record_id`, `query_id` — positives only and append-only: a row's presence *is* the observation, and absence means not selected. It is the sole workload input; selection sets and supports are projections of it, never independently authored. | F |
| 3.1.4 | Events selected by no query appear in the log **not at all**, and are handled as first-class: real bytes, zero demand breadth, counted in size health. | F |
| 3.2.2 | The objective is **aggregate waste** — materialized volume summed over all queries, less selected volume. A single quantity: no weighted sum of competing cost terms, and no frequency weight on a query. | F |
| 3.3.1 | Container resolution is an **exact per-event index** carrying the filterable features, `container_id`, and `record_id`, so activation equals containment with no false positives or negatives. | F |
| 3.3.4 | Index cost is **λ-invariant** and therefore absent from the objective — excluded because it is constant, not because it is negligible — and stays **visible in reported figures**. | F |
| 3.4.1 | Container size bounds, enforced distributionally rather than pointwise. The lower bound is the binding constraint: refinement never increases waste, so the size floor is the sole force opposing granularity. | F |
| 3.4.3 | Write-time assignability: a layout must be evaluable on a newly arriving event from that event alone, without global state. | F |

---

## 4. Dataset contract and providers

| # | Requirement | Type |
| --- | --- | :-: |
| 4.1 | A dataset is three authored CSV files — `events.csv`, `selections.csv`, `queries.csv` — plus `manifest.json`. Everything else is derived. | F |
| 4.2 | Column roles are decided by **convention, not enumeration**: `record_id` is **identity and arrival sequence** — dense, 0-based, and ascending in the order the provider established (4.6), so an event's position is readable from it without reference to any other event; `blob_*_compressed_bytes` / `blob_*_decompressed_bytes` are sizes, `_`-prefixed are hidden, everything else is a partitionable feature. The `blob_` prefix is **enforced** — the objective is byte-weighted, so a corpus whose sizes cannot be found is rejected at validation rather than scored wrongly. No other prefix is enforced anywhere: an unrecognised column is still a feature, which is what keeps 4.3 true. | F |
| 4.3 | No provider-chosen column name may appear in the simulator core. A corpus with unfamiliar column names loads with no code change. | NF |
| 4.4 | Providers are a registry (`register` / `get` / `available`). Adding one requires no change above the seam. | F |
| 4.5 | A `synthetic` provider generates a corpus whose demand structure is known by construction. | F |
| 4.6 | A provider **writes events in arrival order** — by ingest time, tie-broken deterministically — and mints `record_id` from the resulting row position, so the order is resolved once at write time and never reconstructed by a reader. An `external` provider adopts a corpus produced elsewhere from the three CSVs alone, deriving supports and per-query byte totals on ingest, and renumbering keys by row position while preserving the originals. | F |
| 4.7 | A `curated` provider slot for a small committed reference corpus. | F |
| 4.8 | Dataset parameters live with the provider that owns them, never in the simulator's shared config. | NF |
| 4.9 | Hidden (`_`-prefixed) columns are present in the table as provenance but are **absent from the feature set** a reader of the corpus sees, so a generator's internal key is never mistaken for something the corpus is described by. | F |
| 4.10 | Datasets are **immutable and read-only** — the simulator never writes to one. Regeneration produces a new dataset id, and every metric row is stamped with it so results from different corpora cannot be compared on one chart. | F |
| 4.12 | The manifest carries a **per-feature-column summary** — name, dtype, and a description of its domain — written by the provider against the corpus it produced, so a column's domain is readable without loading the corpus. Hidden, identity and blob-size columns are absent from it. | F |
| 4.13 | Loading **validates that `record_id` is a dense 0-based range** and rejects a corpus that is not, so 4.2's sequence is a checked property of every loaded dataset rather than a claim a provider is trusted on. | F |

---

## 5. Data generation (synthetic provider)

| # | Requirement | Type |
| --- | --- | :-: |
| 5.1 | Fully determined by a seed and a parameter set; the dataset id is a hash over those parameters. | F |
| 5.1.1 | The provider ships **exactly one** dataset configuration, small enough that a reader of the workload generator can predict what a query selects. | F |
| 5.3 | Events carry flat features with no implied hierarchy, plus a date axis along which demand decays. Recency is a **decaying weight, not a cutoff** — no event is categorically excluded by age, and the only hard edge is causality. Transaction dates are **generated in ascending order**, modelling a corpus that accumulates in time: event time and ingest time coincide, so arrival order (4.2) carries the recency gradient. | F |
| 5.4 | Verbose payloads are **not materialized** — only each event's compressed and decompressed size, drawn from a skewed distribution. | F |
| 5.4.1 | The corpus carries a **dominant clusterable demand driver**, `brand_id`, the client identifier in a multi-tenant system: the most-wanted brand's events are selected about ten times as often as the least-wanted, and the driver **redistributes demand rather than adding it**, so it is structure to exploit and not a volume knob. The per-event draw is written as a hidden column, analysable without appearing among the corpus's features (4.9). | F |
| 5.8 | The corpus must contain a **substantial never-selected population**, arising by degree rather than by boundary, and a history long enough for the decay to reach a genuinely cold region — without both, it has no skippable data by construction. | F |
| 5.11 | The selection table is immutable observed history — never resampled, reweighted, or perturbed. | F |
| 5.12.1 | `set_name` (`training` / `validation`) is **authored with the dataset** and never derived, so set membership is identical across every run. | F |
| 5.12.2 | The split is **temporal, not random** — earliest queries build, latest validate, with the boundary checked rather than asserted — and every query type contributes to both halves, so a validation result cannot be an artifact of one type landing entirely on one side. Order is carried by query time, identity by `query_id`; ordering is never inferred from an identifier. | F |

---

## 8. Command line

| # | Requirement | Type |
| --- | --- | :-: |
| 8.9 | A CLI drives the two operations the product has: **`generate`** builds a corpus, and **`gui`** serves the page in the foreground. With no subcommand it names them and exits non-zero rather than guessing which was meant. | F |

---

## 9. Explainer visualization

| # | Requirement | Type |
| --- | --- | :-: |
| 9.3 | Cell states are **needed / wasted / skipped**, encoded by colour *and* by fill (solid, striped, empty) so the figure survives colour-blindness, greyscale print, and forced-colours. | NF |
| 9.4 | Data colours are validated against both surfaces for lightness band, chroma, CVD separation, and contrast before use. | NF |
| 9.7 | Figures are generated, emitted as light and dark pairs, and embedded so a Markdown host switches between them by theme. Generated figures are never hand-edited. | F |
| 9.11 | Explainer assets illustrate; they are not test fixtures, and the simulator does not load them. | NF |
| 9.16 | Embedded graphical HTML — the pane fragments the page mounts — is **served through `/figures/`**, distinct from the application shell and from generated figure pairs. | F |

---

## 10. Engineering and quality

### 10.1 Correctness

| # | Requirement | Type |
| --- | --- | :-: |
| 10.1.3 | **No runtime sidecar**: nothing ships in the product whose only purpose is to check other code — no shadow mode, no debug-only parallel path, no self-verifying wrapper. | NF |

### 10.2 Performance and footprint

| # | Requirement | Type |
| --- | --- | :-: |
| 10.2.3 | A subsequent run does not re-parse the corpus or rebuild derived support from scratch when those artifacts are already present. | NF |

### 10.3 Runtime shape and dependencies

| # | Requirement | Type |
| --- | --- | :-: |
| 10.3.1 | **Two dependency sets that do not overlap.** Serving the page needs a minimal ASGI stack and nothing else; building a corpus needs a numeric stack. Neither set may acquire the other's packages, and there is **no template engine** in either. **The split is a requirement rather than a packaging convenience:** the serving process hands over authored files and has nothing to compute (12.2.5), so shipping it a numeric stack would install libraries that exist only to perform an operation the process never performs. Keeping them out is what makes that structural rather than a matter of discipline. **The reason both lists are short is where this runs:** the page is opened on someone else's machine, from a clean checkout, minutes before it is needed, and every added dependency is one more way that fails in front of an audience. The browser side is unaffected: 10.3.5 still admits no third-party asset and no build step. | NF |
| 10.3.2 | **No database and no query engine.** Persistence is inspectable files and in-process arrays. The page holds no store of its own and keeps no session state that survives a reload. | NF |
| 10.3.3 | Explainer figures remain regenerable without a third-party drawing library. Raster-production tools are temporary: after their PNGs pass visual review and are committed, those tools may be removed while the prompt and accepted PNG remain. Those finalized rasters are intentionally not reproducible from the repository. | NF |
| 10.3.4 | Data formats stay inspectable and diffable, accepting size cost to do so. This puts a practical ceiling on any committed corpus. | NF |
| 10.3.5 | The browser side ships **no third-party JavaScript, CSS, font, or icon set**, and **nothing transforms the page between authoring and the browser**: no bundler, no transpiler, no template engine, no server-side rendering. What is served is a file someone authored or a generator wrote and the repository committed (10.3.10) — never a document assembled per request. | NF |
| 10.3.6 | Tooling needed only to *produce* a committed artifact may take dependencies the runtime does not. It is declared as an optional dependency group, is absent from the default install, and the shipped product does not import it. | NF |
| 10.3.7 | Every run writes an **execution log**: events and errors to stdout, and the same records to one file per run, named so the directory sorts into the order things happened. The file is a **tee, not a replacement** — the command is one a reader is watching, and moving errors somewhere they must go looking would make a failed demonstration harder to read. **Interface is not a record**: a prompt, a status line and the served URL stay on stdout as themselves. Run files are **not pruned, rotated, or capped** — the directory is disposable, and deleting it is the whole retention policy — but a name is never reused, because losing records is the one outcome worse than keeping too many. | F |
| 10.3.7.2 | Records carry **no reader-supplied content** — not a request body, not a path a reader typed. Identifiers and counts stand in. This keeps 12.2.7's rule that operational state is never a channel between readers, and it disposes of log injection by having nothing to inject into rather than by escaping. | NF |
| 10.3.8 | **Two checkouts install the same versions.** Runtime packages carry open-ended lower bounds, so without a resolved install two checkouts differ and a demonstration fails where it cannot be debugged. | NF |
| 10.3.9 | **Every tool a documented command needs is a declared dependency**, in a group that command's instructions name. A documented command that cannot run after the documented install is a defect of the packaging, not of the reader. Under 10.3.1's split this binds on `generate`, which names the group that carries the numeric stack and **fails saying which group supplies it** rather than failing on a missing import the reader never asked for. Serving the page needs only the default install. | NF |
| 10.3.10 | **A generated artifact the product ships is versioned with the product.** A clone has it without rebuilding. | NF |
| 10.3.11 | **A committed generated artifact whose generator is retained is current with respect to that generator.** Editing a source or generator without rerunning it leaves the repository shipping the older output. Currency is asserted by running the shipped generator and comparing, never by a second implementation. Finalized raster PNGs whose temporary production tools were removed under 10.3.3 are fixed, visually reviewed assets and are outside this generator-currency check. | NF |

---

## 12. The presentation page

### 12.1 Application shell

| # | Requirement | Type |
| --- | --- | :-: |
| 12.1.1 | A **single page** with five sections in fixed order: Problem Statement, Measuring Data Layout Fitness, Drawing Storage Boundary, Go Live on Databricks Lakehouse, Business Insights as Byproduct. Each is a left/right pair on a wide viewport. **One section is displayed at a time**, chosen by 12.1.3's control; the other four are not laid out. The order is what the control presents and what the titles name, not a sequence the page is read through in one pass. | F |
| 12.1.2 | On a wide viewport each pane **scrolls independently** within a bounded height. The left explanation stays put while the right one is read. Wide content *inside* a pane — a table, a diagram, a long identifier — scrolls horizontally within its own container. The page itself never scrolls horizontally. | F |
| 12.1.3 | Sections carry stable anchors and are individually linkable; a persistent control **selects one of them for display**. A link to a section's anchor opens the page with that section showing, so the address bar names what is on screen and a copied URL reopens it. | F |
| 12.1.3.1 | The **section heading is the navigation label**. When a section also has a distinct editorial name, that name is the **left pane title**, not a second heading above the split. | F |
| 12.1.3.2 | The section heading **stands alone**. It is not followed by a one-line footnote, lede, or subtitle under the title. | F |
| 12.1.3.3 | The top bar is the **section control only**. It does not carry the project title. The browser tab title remains the formal project name. | F |
| 12.1.3.4 | The top bar is a **raised 3D bar**: a ground-to-recessed face, a top-edge highlight, and a drop shadow, composed from 12.7 tokens. | NF |
| 12.1.3.5 | A selectable tab **highlights on mouse-over** so it is visibly choosable before it is selected. | NF |
| 12.1.4 | The design language is **standard macOS**. Where an earlier proposal for this project diverged from the platform, the platform wins: AppKit metrics, AppKit control behaviour, Core Animation timing, and the platform's keyboard-only focus convention. The single exception is colour and type, which 12.1.5 takes from elsewhere. | NF |
| 12.1.5 | The **colour theme and font configuration are taken from the Claude Code documentation** (`code.claude.com/docs`), not from AppKit's system palette. Its ground is a warm paper white and its type is configured as a branded stack that falls through to the system font. Resolved values and their measured contrast are fixed in 12.7. | NF |
| 12.1.5.1 | The page is **light only** and offers no dark variant — a deliberate single-look commitment in service of 12.1's first objective, not an unfinished palette. The document declares a light colour scheme so native controls match, and every colour is painted explicitly rather than inherited from the host. | NF |
| 12.1.6 | Below the split's breakpoint the panes stack, right beneath left, in the same order the sections are listed. Nothing is hidden at a narrow width. | NF |
| 12.1.7 | The **page-level scroll model is stated, not left to emerge**. On a wide viewport the **selected section fills the height below the top bar** and its panes are bounded to that height — which is what gives 12.1.2's independent scroll something to be bounded by. Scrolling belongs to the panes: the page itself has nothing to scroll through, because the sections 12.1.3 does not select are not laid out. Below 12.1.6's breakpoint the bound is **released**: the selected section's panes grow to their content and the page scrolls once, so a stacked reader never meets a scroll inside a scroll. | F |
| 12.1.9 | Type is set for **sustained reading**: leading generous enough for long passages, and numerals aligned in tables. Problem Statement's illustration, terminology, and formulation panes are each set one pixel larger than chrome — body **14px** against 13px, and headings and small type by the same step. Measuring Data Layout Fitness, Drawing Storage Boundary, Go Live on Databricks Lakehouse, and Business Insights as Byproduct use a reading size one pixel larger than Problem Statement's — body **15px**. The formulation fills its pane. Those walkthroughs fill their walkthrough panes. Other reading prose keeps a character-width measure. | NF |
| 12.1.10 | Embedded images and graphs carry a **reusable zoom widget**: a `+` / `−` pair at the top-middle of the figure stage. The default size remains today's fit-width. The buttons step a short scale ladder, are keyboard reachable and labelled, use 12.7 chrome, and hold the scale only for the current view. When the drawing is larger than the stage, the reader **grabs it and drags to pan**; the stage also scrolls. Pan is session-only and resets when the scale returns to fit-width. Tables and prose are not zoomed. | F |

### 12.2 Serving and process model

| # | Requirement | Type |
| --- | --- | :-: |
| 12.2.1 | Served over **HTTP**, started by **one command**, in **one process**, **bound to loopback**. The page is a local reading surface: the process that serves it is reachable only from the machine running it. | F |
| 12.2.2 | The page makes **no outbound request**. Every asset comes from the origin that served the page, on either target (1.5). | NF |
| 12.2.5 | The server **hands over authored files and adds no logic of its own**. It declares no route: one static mount over one tree answers every request, and what it answers with is what the repository ships. | NF |
| 12.2.7 | **No reader's data outlives the request that produced it, and nothing one reader sends is reachable by another.** A request carries everything needed to answer it and a response is complete in itself: no session, no per-reader identity, no memory of what was asked before, and no cache keyed by a request's content or its sender. Nothing at all is held across requests, because the answer to every request is a file read off disk. **What a reader wants kept is theirs to keep.** | NF |
| 12.2.8 | **One command serves the page, in the foreground.** It binds, prints the URL, and opens the reader's browser unless told not to; Ctrl-C or `SIGTERM` stops it. A port already in use fails the bind and says so, rather than being taken from whatever holds it. | F |
| 12.2.13 | **Every URL a page emits is relative to its own document.** A leading slash resolves against whatever host the page was opened from rather than against the page, so it breaks the moment the site is served from anywhere but the root of an origin. | F |

### 12.3 Problem Statement

| # | Requirement | Type |
| --- | --- | :-: |
| 12.3 | The same **two-pane** split as the other sections: independently scrolling panes on the 12.1.5 / 12.7 theme. The illustration sits on the **left**; the terminology dictionary sits above the formal statement on the **right**; that order when stacked. On a wide viewport the terminology band is **30%** of the right column and the formal statement is **70%**. Content, vocabulary, and figures are specified by [`section-problem-illustration.md`](section-problem-illustration.md). | F |

### 12.5 Go Live on Databricks Lakehouse

| # | Requirement | Type |
| --- | --- | :-: |
| 12.5 | The section's reader-facing title is **Go Live on Databricks Lakehouse**, matching its navigation label. The same **two-pane** split as the other sections: independently scrolling panes on the 12.1.5 / 12.7 theme. The go-live process sits on the **left**; the right-pane figures sit on the **right**; that order when stacked. Content and figures are specified by [`section-databricks-deployment.md`](section-databricks-deployment.md). | F |

### 12.8 Measuring Data Layout Fitness

| # | Requirement | Type |
| --- | --- | :-: |
| 12.8 | The section's reader-facing title is **Measuring Data Layout Fitness**, matching its navigation label. The same **two-pane** split as the other sections: independently scrolling panes on the 12.1.5 / 12.7 theme. The walkthrough sits on the **left**; the terminology dictionary sits above the figures on the **right**; that order when stacked. On a wide viewport the terminology band is **30%** of the right column and the figures are **70%**. Content, vocabulary, and figures are specified by [`section-gini-illustration.md`](section-gini-illustration.md). | F |

### 12.9 Drawing Storage Boundary

| # | Requirement | Type |
| --- | --- | :-: |
| 12.9 | The section's reader-facing title is **Drawing Storage Boundary**, matching its navigation label. The same **two-pane** split as the other sections: independently scrolling panes on the 12.1.5 / 12.7 theme. The walkthrough sits on the **left**; the three deferred figures sit on the **right**; that order when stacked. Content and the deferred figures are specified by [`section-budget-illustration.md`](section-budget-illustration.md). | F |

### 12.10 Business Insights as Byproduct

| # | Requirement | Type |
| --- | --- | :-: |
| 12.10 | The section's reader-facing title is **Business Insights as Byproduct**, matching its navigation label. The same **two-pane** split as the other sections: independently scrolling panes on the 12.1.5 / 12.7 theme. The walkthrough sits on the **left**; the figure sits on the **right**; that order when stacked. On a wide viewport the left pane is **30%** of the split and the right pane is **70%**. Content, vocabulary, and the figure are specified by [`section-kpi-illustration.md`](section-kpi-illustration.md). | F |

### 12.6 Quality

| # | Requirement | Type |
| --- | --- | :-: |
| 12.6.1 | Every control is **keyboard reachable and programmatically labelled**, and the section panes are landmarks a screen reader can navigate. | NF |
| 12.6.1.1 | The focus ring appears for **keyboard navigation and not on a mouse click**, matching the platform convention (12.1.4). | NF |
| 12.6.2 | Any state carried by colour is **also carried by something that is not colour** — fill, shape, or text — matching the figures' encoding (9.3). | NF |
| 12.6.4 | **The page asserts no number of its own.** Every figure it displays is traceable to the authored section content, the scenario file, or a committed figure, and a value with no such source is a defect. | NF |
| 12.6.5 | **Nothing that came from a request is ever parsed as markup.** Every other string the page displays is written as text. A boundary that holds only while the input is trusted is not a boundary. | NF |

### 12.7 Design tokens

#### 12.7.1 Colour

| # | Requirement | Type |
| --- | --- | :-: |
| 12.7.1.1 | The ground is **`#FDFDF7`** as served by `code.claude.com/docs`. Cards sit on it. `#F3F3F3` is the **recessed plane**, and its use is enumerated rather than left to taste: table header rows and the terminology panels. A third fill is an invented value. | NF |
| 12.7.1.2 | Ink follows the same source's ramp, assigned by measured contrast: body **`#0E0E0E`** (18.9:1), secondary **`#505050`** (7.9:1), muted **`#707070`** (4.9:1). `#707070` is the **floor for text** — nothing lighter carries a word. | NF |
| 12.7.1.3 | Separators and rules use `#DEDEDE` and `#CECECE`. These are below any text threshold by construction and must never be used for type. | NF |
| 12.7.1.4 | The source's accent **`#D4A27F`** measures 2.2:1 and is therefore **decorative only** — fills, markers, and rules. Placing text on it, or using it as a text colour, is a defect. | NF |
| 12.7.1.5 | Links in reading prose use **`#0B62D6`** (5.5:1). The platform's `#007AFF` measures 3.9:1 and fails AA for body text, so it is reserved for **UI chrome** — focus rings and selection — where the 3:1 component threshold governs. | NF |

#### 12.7.2 Type

| # | Requirement | Type |
| --- | --- | :-: |
| 12.7.2.1 | The stack is the documentation's own: `"Anthropic Sans", -apple-system, BlinkMacSystemFont, "Segoe UI", system-ui, sans-serif`. | NF |
| 12.7.2.2 | **No font file is shipped or fetched** (10.3.5, 12.2.2). `Anthropic Sans` is proprietary and will not resolve locally, so the stack falls through to `-apple-system` and renders as SF on a Mac. Adopting the configuration therefore costs nothing and lands on the platform font by design, not by accident. | NF |
| 12.7.2.3 | Monospace is `ui-monospace, SFMono-Regular, "SF Mono", Menlo, monospace`, used for identifiers, byte counts, and dataset ids. | NF |
| 12.7.2.4 | Body text is **13px** — AppKit's `systemFontSize`. The 17pt Dynamic Type body is an iOS metric and reads as a ported iOS app on a Mac; it is not used. | NF |
| 12.7.2.5 | Section-tab labels are **14px** — one pixel above chrome (12.7.2.4). | NF |

#### 12.7.3 Metrics

| # | Requirement | Type |
| --- | --- | :-: |
| 12.7.3.1 | Spacing follows an **8pt grid with a 4pt sub-unit**. | NF |
| 12.7.3.2 | Corner radii: window `12px`, card `10px`, control `6px`, checkbox `4px`. | NF |
| 12.7.3.3 | Control heights: regular `24px`, small `20px`; the top bar is ~`50px`. | NF |
| 12.7.3.4 | These are **platform convention, not published specification** — Apple documents no numeric values for radii, control heights, or durations. They are recorded here so the page is internally consistent, and are not claimed as official. | NF |

#### 12.7.4 Motion

| # | Requirement | Type |
| --- | --- | :-: |
| 12.7.4.1 | Easing uses the **Core Animation constants**: `cubic-bezier(0.42, 0, 0.58, 1)` for ease-in-ease-out and `cubic-bezier(0.25, 0.1, 0.25, 1)` for the default curve. Generic web easings are not substituted for these, **because these are the curves the platform's own controls move on** (12.1.4) — a generic ease is not wrong in isolation, it is wrong *beside* a native control doing something slightly different. | NF |
| 12.7.4.3 | All motion is suppressed under **`prefers-reduced-motion: reduce`**, and nothing is hidden instead: a reader who asked for less motion asked for a still page, not a page missing part of itself. | NF |

---
