# UI Specification — dataclustering-solver demonstration GUI

**Status:** current snapshot. This document states what the GUI requires *now*.

**Relationship to the simulator spec.** [`simulator-spec.md`](simulator-spec.md) is the
authority on the problem, the harness, the plugin seams, and the engineering rules. This
document is the authority on the surface that presents them. It continues that document's
numbering from §12, so an id is unambiguous across both files: anything `12.x` or `13.x` is
here, everything below §12 is there. Requirements referenced without qualification — `7.1.9`,
`10.3.5` — live in the simulator spec.

**Scope of authority.** Where this document and a source file disagree, one of them is wrong
and the disagreement is a defect.

| Column | Meaning |
| --- | --- |
| **Type** | `F` functional · `NF` non-functional · `I` implementation guideline |

**Requirements and guidelines are different kinds of statement, and the difference is binding.**
`F` and `NF` rows say what the product must do and which qualities it must hold. They are the
deliverable, and the code is judged against them. `I` rows record the design or technology
*currently chosen* to satisfy one of them.

Three rules follow, and together they are what stops an implementation from hardening into a
requirement:

- **Every `I` names the requirement it serves.** A guideline with no parent is either a
  requirement in disguise — in which case it is promoted — or dead weight, in which case it is
  deleted.
- **An `I` is replaceable.** Any alternative that demonstrably satisfies the parent is
  admissible, and adopting one is a design change, not a spec violation. Where a guideline and
  prevailing industry practice diverge, **the guideline is what gives way** — unless a
  requirement is what rules the mainstream option out, and then that requirement says so in its
  own words and carries the reason.
- **A requirement does not name a library, a framework, or a wire format** unless
  interoperating with that exact thing is the requirement.

Where one row states both — a requirement and the mechanism currently meeting it — the
requirement keeps the id and the mechanism moves to a sub-id typed `I`. Ids are never reused
and never renumbered, so a promotion or a demotion is visible as a change of `Type`, not as a
change of address.

---

## 12. Demonstration GUI

One page, served locally, carrying four sections: the problem, a benchmark of assignment
strategies against the harness, the production design, and a Gini split-search illustration.
One is displayed at a time and the others wait behind the navigation, so the reader chooses
where to be rather than scrolling past what they did not ask for. Each section is split left
and right — an explanatory pane beside a demonstrative one — and the fixed order they are
presented in is the order the argument runs: understand, then try, then build, then examine
one screening search.

The GUI is a **presentation surface and nothing more**. It renders artifacts that already
exist and calls the primitive operation that already exists (7.2.4). Where it would need a
number the harness does not produce, the harness gains the number and the requirement is
recorded in the simulator spec — the GUI never computes one for itself.

**The design objectives are ranked, and the ranking settles arguments.** *Reader experience*
comes first and is second to none: where legibility and comfort conflict with anything else in
this document, they win. *Maintainability* comes second — the page must stay cheap to extend as
sections and strategies are added. Everything else, visual ambition included, is subordinate to
those two in that order.

### 12.1 Application shell

| # | Requirement | Type |
| --- | --- | :-: |
| 12.1.1 | A **single page** with four sections in fixed order: A problem statement, B assignment strategy benchmark, C production design, D Gini split-search illustration. Each is a left/right pair on a wide viewport. **One section is displayed at a time**, chosen by 12.1.3's control; the other three are not laid out. The order is what the control presents and what the letters name, not a sequence the page is read through in one pass. | F |
| 12.1.2 | On a wide viewport each pane **scrolls independently** within a bounded height, so the left explanation stays put while the right one is read. Wide content *inside* a pane — a table, a diagram, a long identifier — scrolls horizontally within its own container. The page itself never scrolls horizontally. | F |
| 12.1.3 | Sections carry stable anchors and are individually linkable; a persistent control **selects one of them for display**. A link to a section's anchor opens the page with that section showing, so the address bar names what is on screen and a copied URL reopens it. | F |
| 12.1.4 | The design language is **standard macOS**. Where an earlier proposal for this project diverged from the platform, the platform wins: AppKit metrics, AppKit control behaviour, Core Animation timing, and the platform's keyboard-only focus convention. The single exception is colour and type, which 12.1.5 takes from elsewhere. | NF |
| 12.1.5 | The **colour theme and font configuration are taken from the Claude Code documentation** (`code.claude.com/docs`), not from AppKit's system palette. Its ground is a warm paper white and its type is configured as a branded stack that falls through to the system font. Resolved values and their measured contrast are fixed in 12.7. | NF |
| 12.1.5.1 | The page is **light only** and offers no dark variant — a deliberate single-look commitment in service of 12.1's first objective, not an unfinished palette. `color-scheme: light` is declared so native controls match, and every colour is painted explicitly rather than inherited from the host. | NF |
| 12.1.5.2 | This **knowingly diverges from the canvas** (9.10), which keeps its three-state theming and is unaffected. The divergence is recorded rather than silently introduced, and 9.12 keeps the two separate artifacts. Where the GUI shows a generated chart it uses the **light** variant of the pair (8.8), which continues to be produced in both. | NF |
| 12.1.6 | Below the split's breakpoint the panes stack, right beneath left, in the same order the sections are numbered. Nothing is hidden at a narrow width. | NF |
| 12.1.7 | The **page-level scroll model is stated, not left to emerge**. On a wide viewport the **selected section fills the height below the top bar** and its panes are bounded to that height — which is what gives 12.1.2's independent scroll something to be bounded by. Scrolling belongs to the panes: the page itself has nothing to scroll through, because the sections 12.1.3 does not select are not laid out. Below 12.1.6's breakpoint the bound is **released**: the selected section's panes grow to their content and the page scrolls once, so a stacked reader never meets a scroll inside a scroll. | F |
| 12.1.8 | Any action that can outlast a frame shows a **progress indicator** — a spinner on the control that started it — and the control is disabled while it is in flight so it cannot be fired twice. The spinner's geometry and cadence are fixed in 12.7.4. | F |
| 12.1.8.1 | The indicator appears **immediately on the click that starts the action, and stays for at least one second** even when the work finishes sooner. An action that returns before it is seen to have started reads as a control that did nothing, and the reader clicks again; the floor guarantees every run is witnessed. One second is exactly one revolution of 12.7.4.2's cadence, so the spinner is never cut mid-turn. | NF |
| 12.1.9 | Type is set for **sustained reading**: leading generous enough for long passages, and numerals aligned in tables. Section A's two panes are each set one pixel larger than chrome (12.3.1.2, 12.3.5.5). Section D's two panes are each set one pixel larger than Section A's reading size (12.8.7). The formulation fills its pane (12.3.1.1). Section D's left walkthrough fills its pane (12.8.1.6). Other reading prose keeps a character-width measure. | NF |

### 12.2 Serving and process model

| # | Requirement | Type |
| --- | --- | :-: |
| 12.2.1 | Served over **HTTP**, started by **one command**, in **one process**, with **no build step** between the authored source and what a browser receives. The **bind address is supplied by the environment and defaults to loopback**, so a local demonstration is reachable only from the machine running it, and a deployed instance binds what its platform requires (10.3.12) — where the front door rather than the socket is what makes it unreachable otherwise (12.2.15). What the repository holds is what is served, which is what makes 12.2.2 and 12.6.5 checkable by reading a file rather than by trusting a pipeline. | F |
| 12.2.1.1 | Currently **FastAPI on uvicorn**, single worker — static serving, path containment and request validation come from the framework rather than being hand-rolled at the seam that faces the network. The constraint is not this document's to relax: **10.3.1 owns it**, as the rule naming what the GUI may depend on, and it admits this stack and no template engine. The page is still authored HTML served as authored. Serves 12.2.1 and 10.3.1. | I |
| 12.2.2 | The page makes **no outbound request**. Every asset is served from the local process; nothing is fetched from a CDN and no font is loaded from the network. | NF |
| 12.2.3 | The **catalog document** (8.11.1) is read **once at startup**, parsed, and held for the process's life. **No corpus is loaded, at startup or ever.** The document is the only data the process serves and it is a few hundred kilobytes, so holding it costs what a page of static assets costs — where a corpus held for the same reason cost two orders of magnitude more to answer questions no reader can now ask. | NF |
| 12.2.4 | **The server performs no evaluation.** There is no job queue, no polling, no socket, and no wall-clock ceiling, because there is no request whose cost depends on anything a caller sends: every figure Section B displays was computed before the process started. What bounds a request is therefore the size of the document, which is fixed before the first connection. **This is what makes a 24/7 public instance affordable to state rather than to hope for** — the resource an instance needs is known at build time and does not move under load. | NF |
| 12.2.5 | The server **serves pre-computed figures and adds no scoring logic**. Any computation it performs beyond shaping a response for display is a defect, and belongs behind 7.2.4 — which the serving process cannot reach, because 10.3.1 keeps the harness out of the exhibit's dependency set. The prohibition is therefore structural rather than a matter of discipline: the libraries a violation would need are not installed. | NF |
| 12.2.6 | The interface between page and server is **JSON over HTTP**, exercisable without a browser, so the whole of Section B's behaviour is testable under pytest. Section B's whole server-side surface is **one GET**; it sends no request carrying reader input at all. | NF |
| 12.2.7 | **No reader's data outlives the request that produced it, and nothing one reader sends is reachable by another.** A request carries everything needed to answer it and a response is complete in itself: no session, no per-reader identity, no memory of what was asked before, and no cache keyed by a request's content or its sender. What is held across requests is fixed **before the first connection**, identical for every reader, and derived from no request — the catalog document read at startup (12.2.3) and the process's own identity (12.2.9). The reason is the deployment target: 1.5 serves this publicly as well as on loopback, and a public process is where per-reader state stops being a convenience and becomes a leak between readers — the more so under a shared origin (12.6.5.3). Because none of it was ever built, there is nothing to unwind. **What a reader wants kept is theirs to keep** (13.4). | NF |
| 12.2.7.1 | **The boundary is what a write contains, not whether a write happens.** *Product data* — anything a request asked the system to produce: an evaluation's metric rows (12.4.3.5), a constructed layout, a response body — is **returned to its caller and not persisted**. *Operational state* — a log line, a pid or socket file, a temporary file scoped to one request, a counter or trace about the process itself — is **permitted, as it is for any serving process**; this one already writes a request line per request to its own output. Two questions settle a case, and either one excludes: **is it read back to shape a later response**, and **is it the product the reader asked for**. A write that is neither records the serving rather than the served, and is allowed. **Operational state is never a channel** — it is unreachable through the served interface, no response is shaped by it, and it therefore cannot carry anything between readers. Serves 12.2.7. | NF |
| 12.2.8 | **One command launches the page, and survives being typed twice.** Interactive launch from the control plane (8.9.1) is a **managed background operation**: the menu returns after the instance reports ready, and the serving process outlives the menu. The `gui` subcommand remains a **foreground** launch for a deployed instance and for scripts that already wait on it. Before binding, either path probes the target host and port, and an instance already serving is **reported rather than collided with** — an `Address already in use` traceback is the failure most likely to happen in front of an audience, in the least readable form there is. On finding one it offers **restart, shutdown, or leave it running**, and leaving it running is what pressing Enter does. A listener that is **not this server is never terminated**: the port is this project's guess, and the process holding it is not this command's to stop. | F |
| 12.2.8.1 | A launch that binds **opens the page in the reader's browser**, adding no dependency to do it (10.3.1) and fetching nothing (12.2.2). From the control plane the browser opens **only after the background instance reports ready**. Suppressed by an explicit opt-out, and whenever stdin is not a terminal — a test run and a CI job must never spawn one. | NF |
| 12.2.9 | A running instance is **identifiable by the launcher over the interface it already serves**: a fixed service signature, its process id, the dataset it loaded, and the moment it started. **The signature identifies it, not the mere fact of a reply** — another service answering the same path with well-formed JSON is a foreign listener, and treating it as ours would mean signalling a stranger's process. | F |
| 12.2.9.1 | Currently `GET /api/health`, and **no pid file**. Not because a pid file is disallowed — 12.2.7.1 permits one as operational state — but because asking the socket is the better answer to 12.2.8's question: an instance is recognisable whatever directory or checkout it was started from, and a process that died hard leaves nothing stale behind to reason about. A health endpoint is also what the platform running the deployed image already expects (10.3.12), and is where 12.2.16 leaves readiness. It is the one endpoint the deployed instance answers without the front door's secret, under 12.2.15's single exemption and in the reduced form that clause requires. Serves 12.2.8 and 12.2.9. | I |
| 12.2.10 | The process shuts down on **`SIGTERM` as cleanly as on Ctrl-C** — the listening socket closes and the command exits 0. Restart depends on this rather than on the exit alone: a process that stopped without closing its listener would leave the relaunch to fail against a port that still looks taken. **No escalation to `SIGKILL`** — something ignoring `SIGTERM` is doing what this command does not understand, and the pid is reported for the reader to decide. | F |
| 12.2.11 | Every decision 12.2.8 offers is **addressable without a terminal** — `--stop`, `--restart` (never both), `--no-browser` — and a flag wins over the prompt. Where an instance is running, stdin is not a terminal, and no flag was given, the command **exits non-zero and says which flags would settle it**, rather than reading silence as permission to replace the demonstration being given. The rule set deciding all of this is held apart from both the socket and the terminal, so the whole launch path is assertable under pytest (12.2.6). | NF |
| 12.2.12 | A request body **above a stated ceiling is refused with 413**, and never read past that ceiling whatever the request declared. Trusting `Content-Length` to be honest is the other half of the same mistake, so the bound applies to the declared length *and* to the bytes actually taken. A refusal decided before the body was read closes the connection rather than leaving a half-read request on a reusable socket. | F |
| 12.2.13 | **Every URL a page emits is relative to its own document, and no page addresses anything above its own mount point.** An instance is served under a path prefix it is not told about and must not assume, so a root-absolute reference leaves this instance's namespace and lands in whatever else shares the domain — figures that do not load, and a catalog fetched from an address belonging to something else. Relative addressing is correct only where the document's own URL ends in a slash, so **the deployment guarantees the trailing slash**, redirecting the bare path to it permanently. The rule is checked against what is served rather than remembered: no served asset contains a root-absolute reference. | F |
| 12.2.15 | **A publicly bound instance is reachable only through its front door.** A hosting platform gives a service a public hostname of its own, so the bind address cannot be what excludes direct access. Instead the front door presents a **shared secret, supplied as configuration and never committed**, and a request arriving without it is refused. Without this the platform hostname bypasses the path prefix, the trailing-slash redirect (12.2.13) and every protection configured at the front door, the rate limit among them. This is not authentication of a reader (13.1): it identifies the route a request arrived by, never the person who sent it. **The readiness endpoint (12.2.9.1) is the single exemption**, because the platform's own probe reaches the instance on an internal address and has no way to be given the secret: refusing it would leave every deployed instance permanently unready, so the protection would take the service down rather than defend it. What makes the exemption safe is that the exempt answer is **reduced to whether the process is up** — 12.2.9's identifying detail, the process id, the dataset and the start time, is withheld from a request that did not arrive through the front door. | F |
| 12.2.16 | The instance **describes itself over the interface it already serves**, so a listing page can present it without holding a second copy that goes stale: `GET /exhibit.json` returns a stable identifier, a title, a one-sentence claim, tags, and a version. **The identifier is the mount prefix**, which is what makes it unique across everything sharing the domain (12.2.13). Readiness stays separate, at 12.2.9.1's health endpoint: a listing page asks what this is, a platform asks whether it is up. | F |

### 12.3 Section A — problem statement

| # | Requirement | Type |
| --- | --- | :-: |
| 12.3.1 | **Right**: a read-only, independently scrolling, complete and faithful rendering of the embedded problem statement. It is the document, not a summary of it, and nothing in it is paraphrased. | F |
| 12.3.1.1 | The formulation **fills the width of the right pane**. It is not clamped to a character measure inside that pane. Wide content still scrolls inside its own container (12.1.2). | NF |
| 12.3.1.2 | Type in the right pane is **one pixel larger** than the corresponding 12.7.2 sizes — body **14px** against 13px, and headings and small type by the same step. Serves 12.1.9. | I |
| 12.3.2 | The document's **mathematics renders as the problem statement writes it**, with **no client-side maths library and no web font** fetched to achieve it (10.3.5, 12.2.2). | F |
| 12.3.2.1 | Currently **pre-rendered to HTML ahead of serving** rather than parsed in the browser, with mathematics emitted as **native MathML**. Pre-rendering is what moves the one dependency-heavy step to build time, where 10.3.6 already allows it, and MathML is the browser's own typesetting rather than a library's. Serves 12.3.2. | I |
| 12.3.3 | A **table of contents is injected at the top**, generated from the document's own headings rather than authored beside them, and each entry scrolls the pane to its section. A heading added to the problem statement appears in it with no further edit. | F |
| 12.3.3.1 | A **contents list authored in the document is dropped from the fragment**. The problem statement carries one for readers on a Markdown host, where nothing generates a list; the pane injects its own under 12.3.3, and rendering both would show two lists and file a *Contents* entry inside the generated one. Serves 12.3.3. | F |
| 12.3.4 | The problem-statement pane is **fully static** — no control, no state, nothing to interact with beyond scrolling and following a link. | F |
| 12.3.5 | **Left**: a **closed, ordered editorial walkthrough** with three prose stages and the two static raster illustrations specified by 12.3.5.3. It establishes a dispensary medicine-cabinet mental model, maps that model to a data-warehouse fetch, shows how demand history can inform a different arrangement, and ends by handing the reader to the detailed framework on the right. Nothing else appears in the pane — no outbound link list, separate event table, separate index table, or alternate scenario. | F |
| 12.3.5.1 | The left pane carries the three narrative requirements 12.3.5.1.1–12.3.5.1.3 in that order. The two illustrations sit between those prose stages: the first makes the retrieval and its technical correspondences visible; the second makes the rearrangement opportunity visible. Connecting prose may bridge them, but may not introduce a fourth prose stage. | F |
| 12.3.5.1.1 | Begin with a dispensary medicine-cabinet account in ordinary language: one counter batch contains three prescriptions; the drawer chart names the drawers to pull; each named drawer comes to the counter whole; prescribed boxes are kept while the other handled boxes are put back unused; unnamed drawers stay shut. Establish that the wasted effort is the handling beyond the three boxes the patients need before introducing the first illustration. | F |
| 12.3.5.1.2 | Use the first illustration and adjacent prose to map the same retrieval to a data-warehouse fetch: prescription ask to query, inventory catalog to index-table lookup, small drawer to storage container, medicine box to record, prescribed box to selected record, every handled box to materialized volume, and every unused box put back to waste. State that the containing unit is fetched whole. Then use the second illustration to show a demonstration restocking scheme that learns from demand history and rearranges equal-capacity drawers by demand band. Present that scheme as an explanation of what assignment can change, not as a ranked or recommended strategy. | F |
| 12.3.5.1.3 | Inform the reader that the formal problem statement is presented in the right panel. | F |
| 12.3.5.2 | The pane contains exactly two illustrations, both with a visible title inside the raster and an adjacent explanatory caption. The titles are *Fulfill Prescription Requests* for `A.medical-cabinet` and *Optimize inventory layout by learning from demand history* for `A.smart-organizer`. | F |
| 12.3.5.3 | The pane inserts exactly the two committed raster illustrations below at the stated narrative locations. The first establishes one concrete request and the cost of whole-drawer handling. The second retains the medicine-cabinet setting and its equal-capacity drawers, then broadens from one request to demand history so the reader can see what a restocking scheme observes and changes. | F |

**12.3.5.3 illustration prompts**

- **After (1), before (2) — `A.medical-cabinet`, *Fulfill Prescription Requests*.** Use `resources/img/section_a_medical_cabinet.png`. Show the three-prescription ask, the inventory-catalog lookup, the nine-drawer cabinet, the three drawers opened whole, and the split between the three boxes kept and the nine boxes put back. Its parenthetical labels introduce the technical correspondence at the boundary between the ordinary account and the technical explanation. The caption states the observation: the lookup narrows the drawers, but opening a drawer handles every box inside it.
- **After (2), before (3) — `A.smart-organizer`, *Optimize inventory layout by learning from demand history*.** Use `resources/img/section_a_smart_organizer.png`. Show the usage report, demand-band thresholds, and a new equal-capacity drawer arrangement. The adjacent prose explains that demand history supplies evidence for changing which medicines share a drawer, while drawer capacity and the retrieval mechanism remain fixed. The caption identifies the displayed rule as a deliberately simple demonstration, not a recommendation.

| # | Requirement | Type |
| --- | --- | :-: |
| 12.3.5.4 | The two committed PNGs are flat editorial diagrams — not photoreal, 3D, screenshots, UI chrome, or server racks. They use the warm paper ground and ink of 12.1.5 / 12.7, page sans and mono where the tabular source material requires it, one restrained repeating palette, and state treatments that do not rely on colour alone. The browser scales each image to the pane width without distorting its aspect ratio. | F |
| 12.3.5.5 | Type in the left pane is **one pixel larger** than the corresponding 12.7.2 sizes — body **14px** against 13px, and headings and small type by the same step. Serves 12.1.9. | I |

| # | Requirement | Type |
| --- | --- | :-: |
| 12.3.6 | Vocabulary follows the learning order. Stage (1) prose uses dispensary, medicine cabinet, small drawer, medicine box, prescriptions, counter batch, prescribed, drawer chart, handling, putting back unused, and wasted effort. The first illustration then places query, lookup table, storage containers, and query response beside the familiar objects they name. Stage (2) completes the mapping to data warehouse, storage container, container capacity, record, query, **index table**, container activation, materialized volume, selected records, waste, skipped container, layout, assignment strategy, demand history, and demand band. Stage (3) uses those terms only to identify what the right panel develops. | F |
| 12.3.6.1 | The pane is written in **plain language**. Every technical term is defined beside the medicine-cabinet object, action, or observation that gives it meaning; the first raster's parenthetical mappings count as adjacent context. No glossary precedes the walkthrough. Serves 12.3.6. | F |
| 12.3.8 | Figure pairs authored for a theme-switching Markdown host are **collapsed to their light variant** at pre-render, so a reader whose system is dark is never served a dark figure on this light page (12.1.5.1). | F |

### 12.4 Section B — assignment strategy benchmark

Section B is a **benchmark surface, not a single-run form**. The reader meets a catalogue of
Assignment Strategy candidates that the harness scored before the page was served, each swept
across four container capacities, selects up to four of them, and reads those against the
shipped baseline in one report.

**Nothing in this section is computed while a reader is looking at it.** An earlier draft let
the reader compose candidates in the browser and scored them on demand. It worked, and it cost
what it worked with: the corpus resident in the serving process for that process's life, a peak
approaching half a gigabyte, and seconds of CPU per click — a bill paid by every deployed
instance whether or not anyone pressed the control. Since the family is bounded (12.4.1) and
its capacity sweep is bounded, the space a reader could reach was always small enough to
enumerate, so it is enumerated once, offline, by 8.11's catalog generator.

**The capability was relocated, not removed.** Scoring an arbitrary chain against an arbitrary
capacity is exactly as available as it was, through the CLI (8.9), against any corpus — which
is the surface a contributor doing that work is already using. What was given up is the
*browser's* ability to start that work, and it is recorded as 13.18.

#### 12.4.1 The Assignment Strategy

| # | Requirement | Type |
| --- | --- | :-: |
| 12.4.1.1 | An **Assignment Strategy (A.S.)** places every event in two steps. First the corpus is split as a decision tree is grown: a **chain of group-by expressions over feature columns**, each stage regrouping every split the previous stage produced, splitting two ways or many. Second, every resulting **leaf** is bucketed into containers of a bounded record capacity. Those two steps are the entire family, and nothing else about it is configurable. | F |
| 12.4.1.2 | A stage expression is drawn from a **closed grammar** — comparison, set membership, and arithmetic against exactly one column reference, plus literals — parsed to serializable data and **evaluated by an interpreter over the column**, never by `eval` or any other execution of reader-supplied text in the host language. An expression naming a column the dataset does not carry, or comparing against a literal the column's dtype cannot hold, is rejected before anything runs. | F |
| 12.4.1.3 | The chain is a **set, not a sequence**: every stage applies to every split with no early stopping, so a leaf is an equivalence class of the whole key tuple and permuting the expressions cannot move an event. Expressions are sorted into a canonical order before anything runs, so two permutations produce not merely equivalent partitions but the identical layout. Canonical form is the **analyzed expression's own text**, so `a>5` and `a > 5` are one configuration and therefore one `Params` in the metric table, and one row rather than two. | F |
| 12.4.1.4 | Capacity is a **record count and a maximum**, shared by every leaf of the strategy. Containers are **filled to the capacity**: a leaf of `n` records becomes `n // capacity` full containers and one remainder holding what is left, and a leaf no larger than the capacity is its own remainder. This is the packing rule the baseline already uses, and using one rule for both is what makes a candidate and the baseline comparable as *groupings* rather than as two different packings. The cost is real and accepted: a remainder container per leaf, some of them nearly empty, and a measurably higher waste ratio than an even split over the same leaves. No column of P2 shows that fragmentation — 13.14 records why none can — so it is stated here rather than left for a reader to discover. Containers fill in **arrival order, which `record_id` carries** — again the baseline's order, which is what makes 12.4.1.5 exact rather than approximate on a dataset that was not written in arrival order. Ordering within a leaf is otherwise arbitrary and stays arbitrary; nothing about it is a claim. | F |
| 12.4.1.5 | The **zero-length chain reproduces `insertion_order`**: one leaf, bucketed by capacity in read order. The baseline is the family's degenerate case rather than a separate mechanism, which is what makes measuring a candidate against it meaningful. | F |
| 12.4.1.6 | The family registers as `kind = demonstration` and reads features by design (7.1.2.3). It exists to give this section something to present. It is a fixture, and no arrangement of it that scores well is a result (1.2) — which is why the catalogue drawn from it is ordered structurally rather than by score (8.11.3) and says so where the reader can see it (12.4.2.4). | F |
| 12.4.1.7 | Bucketing carries a **per-leaf write cursor and is therefore stateful**, while the chain is a pure function of one event's features. This is a recorded divergence from write-time assignability (3.4.3): the chain half routes a newly arrived event from that event alone, the bucketing half does not. Recorded rather than hidden — 7.1.6 remains the seam where it would be checked. | NF |

#### 12.4.2 Left pane — the strategy catalogue

| # | Requirement | Type |
| --- | --- | :-: |
| 12.4.2.1 | The panel is a **list of the catalogued Assignment Strategies**, one entry apiece, and it is the only place a reader chooses anything in this section. Each entry carries its **label**, its **group-by chain in the grammar's canonical spelling** (12.4.1.3), the **split count after each stage** (8.11.2), the **leaf count** the chain ends at, and the **container count at each swept capacity**. The chain figures are properties of the chain and appear once; the container count depends on capacity and is therefore shown per capacity. Together they are what distinguishes two entries before any score is read: how finely each one cut the corpus, and at what cost in containers. | F |
| 12.4.2.2 | A reader **selects up to four entries**, and the selection is what the three views draw. The ceiling is four because 12.4.5.1 reserves sixteen candidate rows and 12.4.6.3 makes a series one A.S. — so a fifth selection would break a bound the report promises rather than merely crowd it. At the limit the unselected entries are **disabled rather than hidden**, so the ceiling is visible before it is reached. Selection is marked by something that is not colour alone (12.6.2). | F |
| 12.4.2.3 | The panel states **what is being clustered** before it lists what clusters it: a short account of the corpus and its columns — name, dtype, and a domain summary — read from the **catalog document's provenance block** (8.11.1) and never enumerated in the page (4.3). The corpus is not loaded by the serving process (12.2.3), so the document carrying its own column summary forward is what keeps this true. | F |
| 12.4.2.4 | The panel states, **where the reader sees it and not only in this document**, that these are demonstration fixtures rather than recommendations (1.2, 12.4.1.6), and that their order is structural rather than a ranking (8.11.3). A catalogue of scored candidates is read as a leaderboard unless it says otherwise, and the disclaimer belongs beside the list rather than in a specification the reader will never open. | F |
| 12.4.2.5 | The panel holds **no control that starts work**: no evaluation, no request, no expression to type, no capacity to enter, and nothing to delete. Changing the selection redraws the three views from data the browser already holds, so it is immediate and cannot fail. There is consequently **no progress indication, no error surface and no stale marker in this section** — 12.1.8 continues to govern the shell's own asynchronous work, and finds none here. | F |
| 12.4.2.6 | **Every figure in the panel is a field of the catalog document.** The page computes none of them — not a split count, not a leaf count, not a container count, not a total (12.6.4). Where a figure is wanted that the document does not carry, the document gains it and the requirement is recorded in the simulator spec (8.11), exactly as 12.2.5 requires of the server. | F |

#### 12.4.3 Right pane — the benchmark report

| # | Requirement | Type |
| --- | --- | :-: |
| 12.4.3.1 | **Right**: a read-only, independently scrolling report carrying **three views in fixed order** — P1 the process diagram (12.4.4), P2 the summary table (12.4.5), P3 the paired scatter plots (12.4.6). The order is the sequence a reader needs them in: what was built, what it scored, how the scores trade off. | F |
| 12.4.3.2 | Layouts are **built from the training queries only and scored on both halves** (6.2.3), with training and validation reported as paired columns and the held-out figures given the visual weight (5.12.6). A single number presented without its set name is a defect. | F |
| 12.4.3.3 | The pane states the **dataset id, event count, and query count** it ran against, so a reported figure is never detached from the dataset that produced it (4.10). | F |
| 12.4.3.4 | The report may carry the **labels, units, and one-line captions** a figure needs to be read unaided — the deliberate exception to 8.8, which continues to govern the generated static report. | F |
| 12.4.3.5 | The report is drawn from the **metric rows the catalog document carries** (8.11.1) — the rows a sweep produces, in the schema a sweep produces them in (8.10), each tagged with the entry that produced it and all of them sharing the **batch id of the build** that made them (8.3.1). The page is handed the rows themselves rather than a summary of them, because 12.6.4 makes every displayed number traceable to one. **Nothing a reader does reaches the server**: the selection is applied in the browser to rows it already holds, so this section originates no request carrying reader input and there is nothing about a reader for the process to persist or leak (12.2.7). | F |
| 12.4.3.8 | With no entry selected the pane is **empty and says so**, naming the list that will fill it. | F |

#### 12.4.4 P1 — the process view

| # | Requirement | Type |
| --- | --- | :-: |
| 12.4.4.1 | P1 draws the split **top to bottom, one column per A.S., every column side by side from a shared root** standing for the whole corpus. Side by side from one root is what makes two chains comparable at a glance. | F |
| 12.4.4.2 | An **arrow is a group-by stage, labelled with its expression in the grammar's canonical spelling**. A **block is a stage's result and carries no number** (13.16). Stages are drawn in the canonical order they are evaluated in rather than the order they were typed, which is what P1 exists to show: what became of what the reader wrote — several expressions resolved into one canonically-ordered set. | F |
| 12.4.4.3 | **No KPI appears in P1.** Skipping, waste and cost belong to P2 and P3. A diagram carrying structure and score together invites reading a result off a picture whose geometry means nothing. | F |
| 12.4.4.4 | P1 shows **nothing that depends on capacity**, and bucketing is **not drawn as a stage**. A chain has one shape across its whole sweep; drawing the sweep here would quadruple every column to say the same thing four times. | F |
| 12.4.4.5 | Columns are **ragged**. Chains of different lengths end at different depths and are not padded to a common one — the depth is information. | F |
| 12.4.4.6 | The baseline is **absent** from P1. Its diagram is a root with no arrows, which would spend a column showing nothing. | F |

#### 12.4.5 P2 — the summary table

| # | Requirement | Type |
| --- | --- | :-: |
| 12.4.5.1 | P2 is one row per **(A.S., capacity)** pair — the finest granularity this section produces — bounded by construction at sixteen candidate rows, with **four rows reserved at the top for the baseline** across its own capacity sweep, for twenty. | F |
| 12.4.5.2 | Columns are **grouped and the groups are labelled**: split, data-skipping, metadata-cost. Twenty rows of ungrouped numbers is a table nobody reads. | F |
| 12.4.5.3 | The split group carries the **container count**, and it is **not optional**. P1 shows subset counts without scores and P3 plots one cost against another; P2 is the only place a reader sees how finely a candidate cut the corpus beside what that cutting bought. The count below the size floor (6.3.5) was carried here and **was dropped** — 13.14 records why. | F |
| 12.4.5.4 | **Baseline lift** (6.3.4) is taken against the baseline **at the same capacity**. A candidate row at a capacity the baseline did not sweep shows a **blank cell** — never a substituted, nearest, or interpolated reference. A comparison against a layout that was never built is not a comparison. | F |

#### 12.4.6 P3 — the scatter plots

| # | Requirement | Type |
| --- | --- | :-: |
| 12.4.6.1 | P3 is **two scatter plots side by side**, sharing an X domain and a width so a point's horizontal position means the same thing in both. X is **total container count** on both. Y is **activated record count** on the first and **activated record byte weight** on the second. | F |
| 12.4.6.2 | Both axes are **costs**, so the reading is a Pareto one and lower-left is better. The pair exists because the two Y axes disagree exactly when activation concentrates in unusually large or unusually small events — and that disagreement is the finding, not a redundancy. | NF |
| 12.4.6.3 | A **series is one A.S. across its capacity sweep**: one colour, one legend entry, points connected in capacity order. The connecting line is the granularity–waste trade the sweep traces, and is neither a fit nor a trend. | F |
| 12.4.6.4 | Every point is **direct-labelled with its capacity**. A reader never has to hover to learn which point is which. | F |
| 12.4.6.5 | The baseline is a **grey dashed connected line**, not a colour series with a legend entry. It is the reference the candidates are read against, not a fifth candidate. | F |
| 12.4.6.6 | Highlighting is **series-level and mirrored across both plots**: emphasizing one A.S. in either plot emphasizes it in the other. The **legend is the control** — focusable and keyboard-operable (12.6.1) — and pointer hover is its mirror, never a second mechanism with its own reach. | F |
| 12.4.6.7 | **Highlight adds emphasis and never information.** Everything a reader needs is already drawn: capacity on the point, identity in the legend, the numbers in P2. This is what keeps 12.6.2 true, keeps both plots readable in print, and holds 13.7's exception to a narrow one. | NF |
| 12.4.6.8 | Series take the validated report palette (9.4) rather than the UI accent (12.7.1.6), and each is distinguished by **marker shape as well as colour** (12.6.2). | NF |
| 12.4.6.9 | Both plots are drawn on the **held-out set**, named in the caption and in each plot's accessible label. 12.4.3.2 makes a number without its set name a defect and 12.4.6.1–8 do not choose between the halves, so the choice is made here: P2 is where both are compared, and P3 is where the trade is read, which is a held-out reading (5.12.6). | F |
| 12.4.6.10 | Each plot is drawn in a **fixed box of SVG user units and never scaled above it**, so text inside is drawn at a known size rather than at whatever a pane's width implies. Chart text is set at or below `--text-small` in those units — the one type in the page not taken directly from 12.7.2, because a scaled coordinate system has no fixed relationship to a pixel. Below the box's width the plot scales down with the pane, as Section A's figures do. | NF |

### 12.5 Section C — production design

| # | Requirement | Type |
| --- | --- | :-: |
| 12.5.1 | The same **two-pane** split as Section A: explanatory prose beside diagrams. Section C keeps the document on the left. | F |
| 12.5.2 | It **renders [`production-design.md`](production-design.md)** — dynamic partitioning, containerization, and data skipping on Databricks and Spark — and authors no engine-mapping content of its own. The table illustrations of 12.5.7 are an appendix on the right pane, not a claim about the engine. Connecting prose in 12.5.7.1 may name the engine mechanism; the four tables remain the storage-model instance. | F |
| 12.5.3 | Diagrams are drawn from the 12.7 palette and **fetch nothing to render** (12.2.2). | F |
| 12.5.3.1 | Currently **inline SVG or HTML**, with no third-party diagramming library (10.3.5). Serves 12.5.3. | I |
| 12.5.3.2 | The right pane frames its three engine diagrams as an **editorial sequence**: a short lead states that the abstract two-phase read now has concrete Spark and Databricks machinery, and a short transition after the third diagram separates that engine mapping from 12.5.7's storage-model appendix. These paragraphs may restate mechanisms already governed by `production-design.md`; they author no engine claim of their own (12.5.2). | F |
| 12.5.3.3 | Each of the three engine diagrams carries a **visible title** in the pane as well as the SVG `<title>` and `<desc>` that announce it to assistive technology. A title available only through the accessibility tree does not establish the editorial sequence for a sighted reader. | F |
| 12.5.4 | The left pane renders `production-design.md` at **Section A's parity**: pre-rendered to HTML ahead of serving with mathematics as native MathML (12.3.2), a table of contents injected from the document's own headings (12.3.3), and figure pairs collapsed to their light variant (12.3.8). Both sections render a committed Markdown artifact, and one pre-render serves them both — a second rendering path would be a second thing to keep faithful. | F |
| 12.5.5 | The rendering is **complete and faithful**, not an excerpt. The engine mapping is a deliverable in its own right; a section that summarizes it is a fourth restatement to keep true. | F |
| 12.5.6 | Where the artifact marks content as **unwritten or provisional, the page shows that mark** rather than rendering the gap as though it were finished prose. | F |
| 12.5.7 | The right pane **appends**, after the three engine diagrams and 12.5.3.2's transition, the table illustrations of 12.5.7.1 — `c-event-table`, `c-index-table`, `c-event-support`, and `c-container-activation` — in that order. A horizontal rule follows the transition before the first table, and another stands between every pair of tables. These are the twelve-event storage-model instance; they are not a measurement of the engine (12.6.4). | F |
| 12.5.7.1 | The appendix is the four graphics and one connecting paragraph below, in that order. All four graphics share one visual system: flat editorial diagram (not photoreal, not 3D, not a screenshot of an application); warm paper ground and ink of 12.1.5 / 12.7; ruled table grids in the page sans; keyword chips for formal terms; hatched fill for the blob column; no UI chrome, no server racks, no closet. One instance recurs so each drawing is the previous table re-used, not a new corpus: events `r01`–`r12`; containers `c1` = `r01`–`r04`, `c2` = `r05`–`r08`, `c3` = `r09`–`r12`; queries `q1`, `q2`, `q3` with selections `q1` = {`r01`, `r03`}, `q2` = {`r03`, `r06`}, `q3` = {`r10`, `r11`}; features as written on the rows below. | F |

**12.5.7.1 graphics**

- **`c-event-table` — twelve events in three containers.** Wide frame, three banks side by side, labelled container c1, c2, c3. Each bank is a four-row table: `record_id`, `container_id`, `features`, `blob`. The blob column is wider than the others and hatched (the payload a read pays for); the other three columns are what the index keeps. Rows: c1 — r01 us-east, click; r02 us-east, click; r03 us-east, view; r04 us-west, click. c2 — r05 us-west, view; r06 eu-west, click; r07 eu-west, view; r08 ap-south, click. c3 — r09 ap-south, view; r10 us-east, purchase; r11 us-west, purchase; r12 eu-west, purchase. No query flags, no highlight. Visible title: *Twelve events in three containers*.
- **Index paragraph.** Short prose, no figure. Name the index table’s stored schema: one row per event, columns `features`, `container_id`, `record_id`. A query scans that table, evaluates its predicate on `features`, and collects the `container_id`s of matching rows — those are the containers to open. Then name the engine counterpart: under Spark, `container_id` is realized as a **partition** (Hive-style `PARTITIONED BY` values on the files). **Dynamic partition pruning (DPP)** is the same motion at runtime — a filter, often from the small side of a join, is applied against those partition values so unmatched partitions are never scanned. Do not rename the column. Do not draw the engine.
- **`c-index-table` — the index table.** One twelve-row table, same events in the same order. Two column groups under a split heading: stored (`features`, `container_id`, `record_id`) and computed from the selection log (`q1`, `q2`, `q3`). No blob column. A bordered 1 marks a selection; an empty cell is not selected. The 1s sit on (r01, q1), (r03, q1), (r03, q2), (r06, q2), (r10, q3), (r11, q3) and nowhere else. Chip **index table** on the stored group; chip **selection log** on the computed group. Visible title: *The index table*.
- **`c-event-support` — event support.** The same three-bank table as `c-event-table`. Row r03 is outlined (stroke, not a tint); every other row is quiet. A single-stroke arrow with an open arrowhead points at r03 from below. Chip **event support**. Note: the event support of r03 is q1 and q2 — the queries that selected it. r03 itself is not activated; a selection is what will activate the container it sits in. Visible title: *Event support*.
- **`c-container-activation` — activation and container support.** The same three-bank table again. Bank c1 is outlined as a whole (all four rows); c2 and c3 stay quiet. A single-stroke arrow with an open arrowhead points at c1 from below. Chip **activation** on the outlined bank; chip **container support** on the note. Note: activation is all-or-nothing at the container — one selected event obliges every event in c1. The container support of c1 is q1 and q2 — the union of its members' event supports, and the queries that must open it. Visible title: *Activation and container support*.

| # | Requirement | Type |
| --- | --- | :-: |
| 12.5.7.2 | Every illustration in the appendix carries a **visible title**, not only an accessible one. A drawing whose sole announcement is an SVG `<title>` or a caption beneath its legend is unannounced to a sighted reader. The titles of `c-event-table`, `c-index-table`, `c-event-support`, and `c-container-activation` are those named in 12.5.7.1. | F |

### 12.8 Section D — Gini split-search illustration

Section D is a **static strategy illustration**. It teaches weighted-Gini split
search as a screening idea. It does not run a search, does not score a layout,
and does not recommend a chain (1.2, 13.13, 13.19).

| # | Requirement | Type |
| --- | --- | :-: |
| 12.8 | The same **two-pane** split as Section A: independently scrolling panes on the 12.1.5 / 12.7 theme. The walkthrough sits on the **left**; the figures sit on the **right**; that order when stacked. | F |
| 12.8.1 | **Left**: a closed, ordered editorial walkthrough in committed Markdown, **text only** — no figures. Three stages in linearized learning order. Connecting prose may bridge them; it may not add a fourth stage or move warehouse vocabulary ahead of the inequality-only account. | F |
| 12.8.1.1 | Stage (1) teaches inequality of wealth across population shares. It may use only ordinary inequality language plus the public technical terms Lorenz curve and Gini coefficient. It contains none of: warehouse, container, record, query, index, materialized, selected, layout, assignment, strategy, skip. | F |
| 12.8.1.2 | Stage (2) maps the same construction onto fetch frequency (`used_count`) and feature-grain splits. It states that $G(S)$ screens a logical split. | F |
| 12.8.1.3 | Stage (3) walks a heuristic that grows a group-by-chain or a selective tree, records marginal efficiency, and stops when the next cut returns too little. It names Section B as the surface that scores a physical layout. | F |
| 12.8.1.4 | No assignment strategy is selected, ranked, or recommended (1.2). | F |
| 12.8.1.5 | $G(S)$ does not equal the aggregate waste ($W(\lambda)$, defined in §2.5) and does not compute a skipping ratio. | F |
| 12.8.1.6 | The walkthrough **fills the width of the left pane**. It is not clamped to a character measure inside that pane. Wide content still scrolls inside its own container (12.1.2). | NF |
| 12.8.2 | The left pane is **pre-rendered to HTML ahead of serving** on the same path as 12.3.2 / 12.5.4, with mathematics as native MathML. **No contents list is injected** — the pane is a sequential presentation, not a reference document. | F |
| 12.8.2.1 | Currently the same renderer as 12.3.2.1. Serves 12.8.2. | I |
| 12.8.3 | **Right**: exactly the four illustrations of 12.8.3.1, each with its specified **visible title**. Graph only: visible titles and one-line figcaptions that name what is drawn; no editorial lede. Drawn from the wine-red / warm-rose / dark-green / cool-sage explainer family of the Section A illustration prompts, not from the 12.7 gray series. No orange. No state by colour alone (12.6.2). | F |
| 12.8.3.1 | The four figures, in order: `D.lorenz-wealth` (*When wealth sits in few hands*) — Lorenz diagram, inequality language only; `D.split-comparison` (*The same twelve records, two cuts*) — event-type versus region on the shared instance; `D.selective-tree` (*A chain multiplies every branch; a tree need not*) — full chain versus a tree that splits only the hot leaf; `D.search-trajectory` (*Stop when the next cut returns too little*) — Gini against group count, with a stop region. A later figure changes only the relationship its prompt names. | F |
| 12.8.3.2 | Currently **inline SVG**, no diagramming library (10.3.5). Serves 12.8.3. | I |
| 12.8.4 | One **shared instance** from the second figure onward: the twelve events and selections of 12.5.7.1, with `used_count` derived from that log. Numbers on the figures are that instance's arithmetic, not a measurement (12.6.4). | F |
| 12.8.5 | The pane is **fully static** — no control that starts a search, no state beyond scrolling and following a definition link. | F |
| 12.8.6 | The left pane follows [`introduction_writing_style.md`](guideline/introduction_writing_style.md): each stage is mental model, terms, formula, observations, takeaway; a formula or two or more new terms is introduced with a definition table; later emphasis uses the citation form *the concept description* (`symbol`, defined in §X). | NF |
| 12.8.6.1 | The first introduction of a public technical term is a **wiki weblink**. Later mentions use the citation form. This is a scoped exception to a closed pane: definition links only; no artifact or alternate-scenario links. | F |
| 12.8.7 | Type in both panes is **one pixel larger** than Section A's reading sizes — body **15px** against A's 14px, and headings and small type by the same step. Serves 12.1.9. | I |

### 12.6 Quality

| # | Requirement | Type |
| --- | --- | :-: |
| 12.6.1 | Every control is **keyboard reachable and programmatically labelled**, and the section panes are landmarks a screen reader can navigate. | NF |
| 12.6.1.1 | The focus ring appears for **keyboard navigation and not on a mouse click**, matching the platform convention (12.1.4). Currently drawn on `:focus-visible` only, never bare `:focus`. Serves 12.6.1. | NF |
| 12.6.2 | Any state carried by colour is **also carried by something that is not colour** — fill, shape, or text — matching the figures' encoding (9.3). | NF |
| 12.6.3 | **Unit coverage on the scripts that carry logic is what is required**: the document pre-render (12.3.2, 12.5.4, 12.8.2), the expression grammar (12.4.1.2), the parameter schema and its factory validation (7.1.7, 7.1.8), the catalog generator and the document it emits (8.11), and the JSON interface (12.2.6). These run under pytest with no browser, and are the coverage this section requires. | NF |
| 12.6.3.1 | **Browser-driven checks are not performed.** JavaScript behaviour is asserted as unit tests against a DOM stand-in, which is the coverage 12.6.3 requires, and no test tooling installs a browser (10.3.9). The consequence is named rather than left to be discovered: **12.1.2, 12.1.6, 12.1.7 and 12.4.6.1 are held by inspection, not by test** — a change to the shell's scroll model, or to the two plots' shared width, is verified by opening the page. A requirement whose verification is a person looking at it should say so rather than appear covered. | NF |
| 12.6.3.2 | **A test may not pin a value the spec types `I`.** Where the stylesheet must agree with §12.7, one drift check reads the section and compares; an assertion naming a particular hex, radius or curve would make a permitted restyle a failure, which is the opposite of what typing those rows `I` decided. What a test may assert is a *threshold* — a contrast floor, a grid property, a reduced-motion setting — because those survive a restyle and the values do not. | NF |
| 12.6.4 | **The GUI asserts no number of its own.** Every figure it displays is traceable to a metric row, the dataset manifest, or the scenario file, and a value with no such source is a defect. | NF |
| 12.6.5 | **Nothing that came from a request is ever parsed as markup.** The page assigns HTML in exactly one place — mounting the pre-rendered document fragments (12.3.2, 12.5.4, 12.8.2), which are build artifacts of this repository's own committed Markdown, named by an authored attribute. Every other string it displays came from a fetched document — a catalogue label, a canonical expression, a metric row's own fields — and is written as text or built as nodes. **That the strings now originate in a build artifact rather than in a reader's keystrokes does not relax the rule**: the page cannot tell the difference, the document is authored input like any other, and a boundary that holds only while the input is trusted is not a boundary. 13.3 rules out a sanitizer library, so it is kept by construction rather than by cleaning, and 12.4.1.2 keeps the matching boundary where expressions are parsed. | NF |
| 12.6.5.1 | Every response carries a **`Content-Security-Policy`** and **`X-Content-Type-Options: nosniff`**, so 12.2.2's no-outbound-request promise is enforced by the browser rather than only asserted in a test. `script-src` admits **no inline script and no `eval`** — both scripts are external files, so there is nothing inline to admit. `style-src` allows inline styles, and only because the document pre-render emits `style=` attributes; teaching it to emit classes is what would retire the concession, which is recorded here so the exception does not read as the rule. | NF |
| 12.6.5.2 | Reader-supplied text is **bounded at the seam**, and any refusal reports the bound without **echoing the offending text**, which would be the amplification the bound exists to prevent. Section B no longer sends any (12.4.2.5), so what this now governs is the request line itself and whatever a later surface adds — the rule is kept because removing a bound when its last caller goes away is how the next caller arrives unbounded. | NF |
| 12.6.5.3 | **Every fetch directive in the policy names this instance's own mount point.** Where the instance is the whole origin — a laptop, with no front door and no siblings — `'self'` *is* that mount point, and naming an absolute URL instead would be a narrower statement about nothing that breaks as soon as the port changes. Where a front door has put siblings on one domain, `'self'` is the wrong statement and the configured base URL is named instead. `'self'` is an origin-level keyword, and such an origin holds sibling deployments that have nothing to do with this one — so `'self'` widens script, style, image and connection sources from this instance to the whole domain the moment a second one is added, which is the opposite of what the policy is for. CSP source expressions match on path, so most of what a separate origin would have given is recoverable. Two limits are stated rather than left implicit: browser storage is keyed by origin and **cannot** be path-scoped, which is part of why 13.4 forbids it outright; and CSP binds browsers, so it protects readers rather than endpoints — endpoint protection is 12.2.12 and 12.2.15. Serves 12.6.5.1. | NF |
| 12.6.6 | A class a **mounted fragment uses and the stylesheet does not define is a defect**. Fragments are authored apart from the stylesheet and mount by assignment (12.6.5), so a rule that was never written fails silently: the markup is correct, the selector matches nothing, and the element renders as a browser default inside an otherwise tokenized page. Nothing else in the page's construction would catch it. | NF |

### 12.7 Design tokens

The resolved values 12.1.4 and 12.1.5 refer to. Colour and type come from the Claude Code
documentation; everything structural comes from the platform. Contrast figures are **measured
against the `#FDFDF7` ground**, not assumed, and they decide which role a colour may take.

**Most of this section is `I`, and deliberately so.** A hex, a radius, a font stack and an
easing curve are choices, replaceable by any other set that holds the page together — restyling
is not a spec violation. What stays `NF` is the handful of rows where a *threshold* rather than
a value is the point: the contrast floors that decide whether a colour may carry a word
(12.7.1.2, 12.7.1.4, 12.7.1.5), the rule that no font file is shipped or fetched (12.7.2.2), the
data palette's separate job and its re-validation (12.7.1.6), and the reduced-motion setting
(12.7.4.3). Those survive a restyle; the values do not.

#### 12.7.1 Colour

| # | Requirement | Type |
| --- | --- | :-: |
| 12.7.1.1 | The ground is **`#FDFDF7`** — `--background-light: 253 253 247` as served by `code.claude.com/docs`. Cards sit on it. `#F3F3F3` is the **recessed plane**, and its use is enumerated rather than left to taste: the strategy catalogue's entries (12.4.2.1), the report's empty state (12.4.3.8), and table header rows. It is a ground only — text that sits over it is measured against `#FDFDF7`, since the two are within a hair of each other and the stricter of the pair governs. | I |
| 12.7.1.2 | Ink follows the same source's ramp, assigned by measured contrast: body **`#0E0E0E`** (18.9:1), secondary **`#505050`** (7.9:1), muted **`#707070`** (4.9:1). `#707070` is the **floor for text** — nothing lighter carries a word. | NF |
| 12.7.1.3 | Separators and rules use `#DEDEDE` and `#CECECE`. These are below any text threshold by construction and must never be used for type. | I |
| 12.7.1.4 | The source's accent **`#D4A27F`** measures 2.2:1 and is therefore **decorative only** — fills, markers, and rules. Placing text on it, or using it as a text colour, is a defect. | NF |
| 12.7.1.5 | Links in reading prose use **`#0B62D6`** (5.5:1). The platform's `#007AFF` measures 3.9:1 and fails AA for body text, so it is reserved for **UI chrome** — focus rings and selection — where the 3:1 component threshold governs. | NF |
| 12.7.1.6 | Chart series keep the validated report palette (9.4) rather than adopting the UI accent; identity in data and accent in chrome are different jobs. The palette is re-validated against `#FDFDF7` whenever the ground changes. | NF |

#### 12.7.2 Type

| # | Requirement | Type |
| --- | --- | :-: |
| 12.7.2.1 | The stack is the documentation's own: `"Anthropic Sans", -apple-system, BlinkMacSystemFont, "Segoe UI", system-ui, sans-serif`. | I |
| 12.7.2.2 | **No font file is shipped or fetched** (10.3.5, 12.2.2). `Anthropic Sans` is proprietary and will not resolve locally, so the stack falls through to `-apple-system` and renders as SF on a Mac. Adopting the configuration therefore costs nothing and lands on the platform font by design, not by accident. | NF |
| 12.7.2.3 | Monospace is `ui-monospace, SFMono-Regular, "SF Mono", Menlo, monospace`, used for identifiers, byte counts, and dataset ids. | I |
| 12.7.2.4 | Body text is **13px** — AppKit's `systemFontSize`. The 17pt Dynamic Type body is an iOS metric and reads as a ported iOS app on a Mac; it is not used. | I |

#### 12.7.3 Metrics

| # | Requirement | Type |
| --- | --- | :-: |
| 12.7.3.1 | Spacing follows an **8pt grid with a 4pt sub-unit**. | I |
| 12.7.3.2 | Corner radii: window `12px`, card `10px`, control `6px`, checkbox `4px`. | I |
| 12.7.3.3 | Control heights: regular `24px`, small `20px`; the top bar is ~`50px`. | I |
| 12.7.3.4 | These are **platform convention, not published specification** — Apple documents no numeric values for radii, control heights, or durations. They are recorded here so the page is internally consistent, and are not claimed as official. | I |

#### 12.7.4 Motion

| # | Requirement | Type |
| --- | --- | :-: |
| 12.7.4.1 | Easing uses the **Core Animation constants**: `cubic-bezier(0.42, 0, 0.58, 1)` for ease-in-ease-out and `cubic-bezier(0.25, 0.1, 0.25, 1)` for the default curve. Generic web easings are not substituted for these, **because these are the curves the platform's own controls move on** (12.1.4) — a generic ease is not wrong in isolation, it is wrong *beside* a native control doing something slightly different. | I |
| 12.7.4.2 | The spinner of 12.1.8 reproduces `NSProgressIndicator`'s documented cadence: **12 blades at 30°, one step every 1/12 s, one revolution per second**. | I |
| 12.7.4.3 | All motion is suppressed under **`prefers-reduced-motion: reduce`**, the spinner degrading to a static indicator rather than disappearing. | NF |

---

## 13. Deliberately not required

Recorded so their absence reads as a decision rather than an omission. These continue §11 of
the simulator spec, which carries the exclusions that are not about the GUI.

| # | Item | Why |
| --- | --- | --- |
| 13.1 | Authentication, authorization, sessions, or multi-user support | 12.2.7 — the server holds nothing on any reader's behalf, so there is no per-reader thing for access control to protect. That, rather than a network boundary, is what makes public serving survivable, and it is why the exclusion outlives the loopback binding that once justified it. 12.2.15's shared secret is not a counter-example: it identifies the route a request arrived by, not the caller, and no reader ever presents a credential |
| 13.3 | A client-side framework, bundler, or package manager | **The project ships zero third-party browser code, so a package manager would be managing an empty set** — that is the reason, rather than a position on client tooling. The build step one brings would also break what 12.2.2 relies on: that the file served is the file authored, verifiable by reading it. **What would flip this: the first genuine client-side dependency.** At that point a manager is managing something, and this row is revisited rather than cited. 10.3.5 carries the same rule for the runtime side |
| 13.4 | **Persisting** GUI state — which catalogue entries a reader selected, or anything else the current view is drawn from — anywhere, by any mechanism | **Not required at this stage, regardless of where it could be put or how easily.** 10.3.2 — the page is a quick interactive demonstration, not a workspace to return to, and no evaluation result needs to outlive the request that produced it. This is a flat exclusion rather than a preference between stores: not `localStorage`, not a cookie, not a URL fragment, and not the server (12.2.7), because the deployment is public and reader state held server-side does not survive that. The browser-side half has since acquired a second and harder reason: sibling deployments share one origin, and browser storage is keyed by origin rather than by path (12.6.5.3), so anything this page stored would be readable by whatever else shares the domain. **Any caching or persistence of state is handled at the user's level** — whatever a reader wants kept is theirs to keep, and the page will not keep it for them. What remains is the working memory the current view is drawn from, which is not persistence: a reader returns to a report by selecting the same entries again, against a catalogue that is identical for every reader |
| 13.5 | Editing the dataset, the selection log, or the layout from the GUI | 4.10 and 5.11 — datasets are immutable and the selection table is observed history. The GUI reads the precomputed catalogue (12.2.3, 12.2.5); it never scores and never writes a dataset |
| 13.7 | Pointer hover states as a required affordance **on controls** | Standard AppKit push buttons do not hover-highlight, and the residual behaviour was removed in macOS Monterey. 12.1.4 defers to the platform. **Data marks are the exception**: 12.4.6.6 makes hover a mirror of the legend's series highlight, because a chart is not an AppKit control and the platform has no convention to defer to. The exception is bounded by 12.4.6.7 — hover adds emphasis and never information — so no value is reachable only by pointing at it |
| 13.8 | A dark theme | 12.1.5.1 — a deliberate single-look commitment |
| 13.9 | **Any form in Section B** — a schema-generated one over arbitrary strategy families, or the bounded builder that replaced it | 12.4 — the section presents a catalogue computed ahead of serving (8.11), so it configures nothing and has no form of any kind. The seams stay general and stay reachable: the registry enumerates every family (7.1.9), the factory builds any of them (7.1.8), and the CLI runs them (8.9). What is excluded is the *page* growing a control plane at all |
| 13.12 | Ordering records within a leaf by support, size, or any other signal | 12.4.1.4 — within-leaf order is arbitrary and stated to be arbitrary. An ordering chosen to reduce waste is an assignment strategy, which 1.2 does not ship. Read order is the one choice that claims nothing |
| 13.13 | **Automated or reader-triggered search for a chain** — suggesting expressions, ranking candidates, or optimizing a sweep on demand | 1.2 and 11.1 — a page that proposed a good chain would be offering an assignment strategy through the back door. **A fixed catalogue is not this**, and the distinction is the mechanism rather than the outcome: 8.11.3's entries are chosen once by an author to span a structural range, are ordered structurally rather than by score, and change only when someone edits the definition and rebuilds. Nothing searches, nothing ranks, and nothing responds to what a reader did. What is excluded is a *procedure that finds* a chain, not a *list that shows* several |
| 13.14 | A **size-health column in P2** — the count of containers below the size floor (6.3.5), or any other single figure standing in for it | The count does not separate the layouts it is read across. Under 12.4.1.4's packing every leaf ends in a remainder, so the column counts one container per leaf, and it is silent on how much of the corpus sits in those remainders. The cost model's fragmentation term is not the substitute it looks like: the shortfall sum telescopes to `container count − corpus size ÷ capacity`, so it restates the container count beside it and is invariant to how records are distributed. Size health is a **distribution**, and no one number in the metric row carries it; 6.3.5 keeps producing the figures and the CLI report keeps showing them, where a percentile spread has room. What is excluded is a P2 column claiming to answer a question it cannot |
| 13.16 | A **per-stage subset count in P1** — how many subsets the corpus stands in after each prefix of a chain | 12.4.4.3 — no KPI appears in P1, and the count is the one figure a block could carry that a reader could take for a score off a picture whose geometry means nothing. **The count itself is not excluded, only its placement**: it is a structural property the family reports (8.11.2) and the left panel lists (12.4.2.1), where it sits as a number in a list beside the chain that produced it rather than as a label on a diagram. P1 states the shape of a chain; how a chain performs belongs to P2 and P3 |
| 13.17 | Outbound links from Section A's illustration pane to the interactive canvas (9.12) and the generated figures (9.7) | 12.3.5 — the pane is the closed six-beat medicine-cabinet sequence. Those artifacts remain in the repository and stay reachable from the README; they are not a footer of this pane |
| 13.18 | **Composing and scoring an Assignment Strategy from the browser** | 12.4 — the capability is not lost, it is relocated to the CLI (8.9), which scores any chain against any capacity on any corpus. What the browser gave up it gave up for a measured price: serving it meant the corpus resident for the serving process's life, a peak near half a gigabyte, and seconds of CPU per click, on every deployed instance whether or not a reader ever pressed the control. Since the family and its sweep are both bounded (12.4.1), the space a reader could have reached was small enough to enumerate once and ship, which is what 8.11 does. **What would flip this: a strategy space too large to enumerate.** At that point a reader has something to explore that a catalogue cannot hold, and this row is revisited rather than cited |
| 13.19 | **Computing Gini in the browser, running a sweep, or adding a Gini family to the catalogue** | 1.2, 12.8.5, 13.13 — Section D describes a screening search; it does not perform one. A page that scored $G(S)$ on demand, expanded a chain, or listed a Gini family beside the fixtures would be offering an assignment strategy through the back door. The twelve-event numbers on the figures are authored instance arithmetic (12.8.4), not a live evaluation |
