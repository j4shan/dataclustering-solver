# Open problems — dataclustering-solver

Findings that belong to **this repository**, collected from the navigator architecture discussion
of 2026-08-23/24 so they can be reviewed on their own schedule. Navigator-level concerns are not
here; they live in the navigator repository.

IDs are the ones used in that conversation and are stable — cite by ID, never by position.

**All nine have since been acted on**, under the execution plan in
`project_metadata/plans/navigator-execution-plan.md`. The spec update that gated the work was
confirmed and applied first. Each entry's **Status** and **Action** record what was done.

**P22–P27 were added on 2026-08-24**, when a container runtime became available and the
deployment artifact was built and run for the first time. Three of them are defects that only
running the image could have surfaced, and one is the terminology decision that renamed the
*thesis* to the **exhibit** across both repositories. **P29 was added on 2026-08-26**, when two
sessions editing one working tree published a commit neither had validated.

## Why these exist

This project was built as a single-exhibit, single-reader, loopback demonstration. Three
architectural decisions have since been taken that retire that premise:

1. This exhibit becomes one of several, each an independent repository and an independently
   deployed web server, listed by a shared landing page.
2. The GUI moves from the standard library to **FastAPI + uvicorn**.
3. Deployment becomes **public**, on a mainstream cloud host, behind one front door that routes
   by **disjoint URL path suffix on a single shared domain**.

Every finding below is a place where the existing design encodes the retired premise.

## Status ledger

| ID | One line | Severity | Status |
| --- | --- | --- | --- |
| P5 | Root-absolute URLs escape the exhibit mount point | blocking | resolved, enforced forward |
| P16 | No trailing-slash canonicalization; addressing contract unwritten | blocking | resolved, enforced forward |
| P12 | Benchmark endpoint is unbounded public compute | blocking | resolved, enforced forward |
| P9 | Spec clause 10.3.1 forbids the framework now chosen | blocking | resolved |
| P15 | CSP `'self'` stops isolating under a shared origin | degrading | resolved, enforced forward |
| P18 | Dataset is built on first run, not shipped in the image | degrading | resolved |
| P13 | Sweep duration versus front-door timeout ceiling | degrading | resolved |
| P19 | Platform origin hostname bypasses the front door | degrading | resolved, enforced forward |
| P17 | Corpus size asserted in code is contradicted by the tree | cosmetic | resolved |
| P23 | Container cannot start: log directory is not writable by the runtime user | blocking | resolved |
| P24 | Front door refuses the platform's own readiness probe | blocking | resolved, enforced forward |
| P25 | Container ignores `SIGTERM` and is hard-killed on every deploy | degrading | resolved |
| P22 | Deployment artifact had never been built or run | blocking | resolved |
| P26 | "Thesis" is the wrong word for an independently deployed page | degrading | resolved |
| P27 | `CLAUDE.md` points at a term dictionary that has moved | cosmetic | resolved |
| P29 | A concurrent session's in-flight work was published mid-edit | degrading | resolved |

Closed during the discussion and recorded only so the trail is complete: P1 (eager
initialization at startup — adopted), P2 (navigator as its own repository — adopted), P3 and P7
(isolation and theme — resolved by the artifact/theme decisions), P4 (terminology — withdrawn),
P6 (child-process supervision — withdrawn when exhibits became independently deployed servers),
P8, P10, P11, P14 (navigator-level, not this repository).

---

**P5**

**Category:** coding implementation, architecture / seam
**Scope:** production
**Severity:** blocking
**Components:** front end — application shell and Section B benchmark script — `simulator/gui/static/index.html`, `simulator/gui/static/section-b.js`
**Problem Description:** When: on every request, once this exhibit is served under a URL path suffix rather than at a domain root. The page addresses six of its own resources from the site root. That is correct only while this exhibit owns the whole origin. Reached at `/dataclustering/`, those requests leave the exhibit's path and arrive at the landing page's namespace instead — the three explainer figures fail to load, and all three benchmark calls post to an address that does not belong to this exhibit. Section A renders without its illustrations and Section B cannot run at all.
**Cause:** The server root and the exhibit root have always been the same path, so root-absolute and document-relative addressing were indistinguishable and the difference was never forced.
**Evidence:** Five references in two hand-authored files. Two `noscript` fallback links to the illustrations, `href="/figures/graphics/section-a-illustration.html"` `[simulator/gui/static/index.html: 45]` and `href="/figures/graphics/section-c-illustration.html"` `[simulator/gui/static/index.html: 107]`, targeting the prefix defined at `[simulator/gui/server.py: 45]`. Three benchmark calls: `fetch("/api/evaluate")` `[simulator/gui/static/section-b.js: 392]`, `fetch("/api/family")` `[simulator/gui/static/section-b.js: 504]`, `fetch("/api/dataset")` `[simulator/gui/static/section-b.js: 505]`. The pre-rendered fragments are **not** affected: the pre-render tool's asset prefix is already relative `[tools/render_formulation.py: 68]`, so `formulation.html` and `production-design.html` are correct as they stand.
**Action:** Done. Every URL the page emits is now relative to its own document — seven edits across two hand-authored files (the five references named above, plus the two `data-mount` attributes beside the fallback links, which had the same defect). No generated artifact was re-rendered and the pre-render tooling was not touched. The rule is now checked rather than remembered: a parametrised test scans every served HTML, CSS, JavaScript and SVG document for a URL beginning with a single slash, and the whole page was exercised through a prefix-stripping proxy at `/dataclustering/` — every asset, both documents, both illustrations, and a full evaluation. Requirement recorded as 12.2.13.
**Status:** resolved, enforced forward

---

**P16**

**Category:** coding implementation, architecture / seam
**Scope:** production, build & deploy
**Severity:** blocking
**Components:** front end and build pipeline — document addressing contract — `simulator/gui/static/`, front-door routing configuration
**Problem Description:** When: whenever a visitor reaches the exhibit without a trailing slash. Document-relative addressing, which P5 adopts, is only correct when the document's own URL ends in a slash. A page that works perfectly at `/dataclustering/` breaks completely at `/dataclustering`, because the browser then resolves every relative reference against the domain root. Nothing currently establishes the trailing slash, and nothing states the rule, so the same defect will be reintroduced by the next person who writes a URL into a page.
**Cause:** The condition that makes relative addressing correct is a property of the deployed URL, and no component currently owns it.
**Evidence:** No canonicalization exists because there is no front door yet; the served page is currently always at the origin root, where the question cannot arise.
**Action:** Done, in both parts. Contractually, clause 12.2.13 now states both rules — every URL relative to its own document, and nothing addressed above the mount point — and names the trailing slash as the condition that makes the first one correct. Operationally, the redirect belongs to the front door and is listed in the deployment sequence; it was exercised against a stand-in proxy, which answered `308` from `/dataclustering` to `/dataclustering/`. The same rules are published to third parties in the navigator repository's `CONTRACT.md`, rules 5 and 6.
**Status:** resolved, enforced forward

---

**P12**

**Category:** security
**Scope:** production
**Severity:** blocking
**Components:** back end — benchmark endpoint — `simulator/gui/api.py`, `simulator/gui/server.py`
**Problem Description:** When: from the first moment this exhibit is publicly reachable. The benchmark endpoint accepts a request and synchronously runs a scoring sweep across the whole in-memory dataset. On loopback that is a feature: the only caller is the reader who started the process, and there is nothing to protect them from. Publicly, it is an unauthenticated endpoint that converts a small request into a large amount of CPU and memory work, and an anonymous caller may issue them concurrently and without pause. Nothing in the current design bounds how many sweeps run at once, how long one may take, or how large a candidate configuration may be.
**Cause:** Synchronous unbounded evaluation was designed under the single-local-reader premise recorded in clause 12.2.4, and public exposure retires that premise without retiring the design.
**Evidence:** Evaluation is documented as synchronous precisely because the dataset is preloaded `[simulator/gui/server.py: 9]`. The only present limit on a request is a one-megabyte body cap `[simulator/gui/server.py: 57]`, which bounds the size of the input and not the work it causes.
**Action:** Done, in the two layers this repository owns; the third is deployment configuration. The payload bounds were already enforced before any work began — four blocks, four chain stages, four capacity points, each checked through the same parameter schema as any other input — so what was missing was the process layer, and that is now built: a semaphore admitting one evaluation at a time and answering 429 rather than queueing, released on the refusal path as well as the success path, plus the wall-clock ceiling set with P13. Both were exercised against a running instance: three concurrent evaluations produced one 200 and two 429s, and an instance configured with a 1 ms ceiling answered 503 with a message the page can display. The rate limit on the benchmark path is step 4 of the deployment sequence. Requirement recorded as 12.2.14.
**Status:** resolved, enforced forward

---

**P9**

**Category:** specification defect
**Scope:** production, project documentation
**Severity:** blocking
**Components:** back end — stack constraints — `project_metadata/simulator-spec.md` §10.3.1, `project_metadata/ui-spec.md` §12.2.1
**Problem Description:** When: at the moment the GUI is rewritten on FastAPI. A recorded requirement states that the GUI adds no dependency and is served by the standard library with no web framework and no ASGI server. The decision taken is FastAPI on uvicorn, which contradicts it directly. The clause is not merely stylistic: it carries a stated rationale — that a demonstration is opened on someone else's machine minutes before it is needed, and every added dependency is another way that fails in front of an audience. Public deployment changes that calculus, because the demonstration is now a running service rather than a clean checkout, but the change has to be made deliberately rather than by contradiction.
**Cause:** The clause encodes a distribution model — clone and run locally — that public deployment replaces.
**Evidence:** The framework prohibition and its reasoning are stated in full at §10.3.1 `[project_metadata/simulator-spec.md: 224]`. The loopback requirement, justified on the ground that there is no trust boundary to enforce, is at `[simulator/gui/__init__.py: 25]`.
**Action:** Done. The spec update was presented, confirmed, and applied before any code changed. §10.3.1 now admits FastAPI on uvicorn for the GUI alone and keeps both auditability rules intact — no template engine, and §10.3.5's ban on third-party browser assets and build steps untouched. §12.2.1 now reads: bind address supplied by the environment, defaulting to loopback. Sixteen clauses moved in total, including the deletion of §13.2, which had recorded containerized deployment as deliberately not required. The GUI was then ported: `StaticFiles` supplies path containment, uvicorn supplies the serving loop, and the existing suite passed across the port with only the assertions whose requirement had changed edited.
**Status:** resolved

---

**P15**

**Category:** security, architecture / seam
**Scope:** production
**Severity:** degrading
**Components:** front end — content security policy — `simulator/gui/server.py`
**Problem Description:** When: always, once a second exhibit shares the domain. The isolation requirement is that no exhibit may interfere with another. Routing all exhibits under one domain places them in one browser origin, which means the browser no longer enforces that separation, and the present policy silently depends on the assumption that has just been retired. `default-src 'self'` was a strong statement while the origin held one exhibit; it becomes a permissive one when the origin holds all of them, because every sibling exhibit is then `'self'` too. Script, style, image and connection sources all widen from this exhibit to the whole site at once.
**Cause:** `'self'` is an origin-level keyword, and the contents of the origin changed from one exhibit to many.
**Evidence:** Six of the eight directives in the policy are built from `'self'` `[simulator/gui/server.py: 64]`. The accompanying rationale asserts the reader can confirm the page makes no outbound request — a claim that holds only for a single-exhibit origin.
**Action:** Done. Every fetch directive is now built from the mount point the deployment supplies, so a deployed instance sends `default-src https://<domain>/<id>/` and a laptop — which is alone on its origin — still sends `'self'`, that being exactly its own mount point. Both limits are recorded in clause 12.6.5.3 rather than left implicit: browser storage cannot be path-scoped, which is now a second and harder reason for §13.4's existing prohibition, and CSP protects readers rather than endpoints, which is 12.2.14 and 12.2.15. The prohibition is published to third parties as rule 6 of the navigator's `CONTRACT.md`.
**Status:** resolved, enforced forward

---

**P18**

**Category:** architecture / seam, process / planning
**Scope:** build & deploy
**Severity:** degrading
**Components:** build pipeline — dataset provisioning in a deployed container — `simulator/__main__.py`, `.gitignore`
**Problem Description:** When: on every cold start of a deployed instance. The dataset is not in the repository — it is ignored by design, on the sound reasoning that it is reproducible from a manifest and a seed — and the command-line entry point builds it on first run if it is absent. In a local demonstration that is exactly right: one slow first run, then a warm working tree. In a deployed container with an ephemeral filesystem, "first run" is every start, so each deploy, restart, crash recovery and scale event pays full dataset generation before the service can answer, and the platform's own health-check deadline may well expire first.
**Cause:** Build-on-first-use assumes a filesystem that survives between runs, which a container image does not provide.
**Evidence:** Generation is triggered by absence of the manifest, in `_load_or_build` `[simulator/__main__.py: 42]`. The dataset root is ignored at `[.gitignore: 42]`. The generated corpus is 124 MB on disk across five files.
**Action:** Done. The `Dockerfile` builds in two stages, the first of which runs `python -m simulator generate` — the same command a reader runs locally, so there is no build-only path into the provider — and the second copies the result in. The repository stays free of generated data, every instance is byte-identical, and the cost is paid once at build time. Requirement recorded as 10.3.12.1. **Not verified by execution:** no container runtime is installed on this machine, so the image has never been built. That is the one item in this document asserted from reading rather than from running.
**Status:** resolved

---

**P13**

**Category:** coding implementation, architecture / seam
**Scope:** production, build & deploy
**Severity:** degrading
**Components:** back end and build pipeline — request duration versus platform limits — benchmark endpoint and front-door configuration
**Problem Description:** When: whenever a benchmark sweep runs longer than the front door permits. Every managed front door imposes a hard ceiling on how long it will wait for an origin to respond, and that ceiling is not configurable on entry-level plans. A sweep that exceeds it produces a gateway error at the browser while the exhibit process continues consuming CPU on a result nobody will receive — the worst of both outcomes, and one that will read as a bug in the benchmark rather than as a platform limit. The ceiling is roughly 100 seconds for a CDN-style front door and roughly 30 for a serverless-platform proxy, which is what makes the front-door choice a constraint on the benchmark's design rather than an operational detail.
**Cause:** A long-running synchronous request is unremarkable over loopback, where nothing sits in the path, and acquires a hard deadline the moment a managed proxy is introduced.
**Evidence:** No measurement of worst-case sweep duration exists in the repository, which is itself part of the problem: the number that must fit inside the platform ceiling is unknown.
**Action:** Done, and the measurement decided it. The largest request the page can send — four blocks of four chain stages and four capacities each, plus the baseline's four, so twenty evaluations and sixty metric rows — runs in **13.0 seconds** against the 600 000-event corpus, measured twice (12.9 s, 13.0 s) on an 18-core arm64 laptop. That fits comfortably, so **the endpoint stays synchronous and Section B does not become submit-and-poll.** The ceiling is set at 75 seconds: chosen from the front door rather than from the measurement, so that under a CDN-style front door waiting about 100 seconds this process always gives up first. A shared container is slower than the machine measured, which is why the margin is this wide and why step 4 of the deployment sequence measures the deployed instance again rather than assuming.
**Status:** resolved

---

**P19**

**Category:** security, architecture / seam
**Scope:** production, build & deploy
**Severity:** degrading
**Components:** back end — public reachability of the deployed instance — deployment configuration and the exhibit's request handling
**Problem Description:** When: always, once deployed to a managed container platform. Such a platform gives every service a public hostname of its own and expects the service to bind all interfaces on a port it supplies. The front door is therefore not the only way in: the platform hostname reaches the same process directly, bypassing the shared domain, the path prefix, the redirect that guarantees the trailing slash, and every protection configured at the front door — including the rate limit that P12 depends on as its outer layer. The page also misbehaves when reached that way, because it is then at an origin root rather than under its path.
**Cause:** Loopback binding, the mechanism that previously made the front door the only route, is not available on a platform that requires the service to be reachable by the platform's own router.
**Evidence:** The loopback requirement and its rationale that there is no trust boundary to enforce are at `[simulator/gui/__init__.py: 25]`; both premises fail on a public platform.
**Action:** Done. The front door presents `X-Navigator-Origin` on every request it forwards, and a request arriving without it — or with the wrong value — is answered `404`, not `403`, because a different answer for a wrong secret tells a prober there is one. The comparison is constant-time. The check is disabled when no secret is configured, which is the local demonstration, where there is no front door to bypass. Verified live: with a secret configured, the container's own address answered 404 on every path while the same paths through the front door answered 200. The navigator uses the identical arrangement for itself. Requirement recorded as 12.2.15.
**Status:** resolved, enforced forward

---

**P17**

**Category:** project documentation
**Scope:** production
**Severity:** cosmetic
**Components:** back end — server module documentation — `simulator/gui/server.py`
**Problem Description:** When: always. The server's own documentation states that the expensive part of a run is reading six gigabytes of corpus, and offers that figure as the justification for loading the dataset once at startup. The only dataset in the tree is two orders of magnitude smaller. The reasoning for eager loading is sound either way, so nothing is broken by the discrepancy — but the figure is the kind of statement a reader trusts, and it was in fact relied upon during hosting design, where it would have led to provisioning a container roughly eight times larger than needed.
**Cause:** Either the figure describes an external-provider corpus rather than the shipped synthetic one and does not say so, or it predates the current generation parameters.
**Evidence:** The claim is at `[simulator/gui/server.py: 11]`. The generated corpus measures 124 MB across five files, the largest being a 63 MB selection log and a 37 MB event table.
**Action:** Done. The claim is gone. The rewritten module docstring gives the reason for eager loading without asserting a size at all — the argument never needed the number, which is what made the stale one pure liability. Where a size does now matter, it is stated with its source: the `Dockerfile` records 124 MB across five files as what sizes the container. The same correction was applied to the README's account of the serving model.
**Status:** resolved

---

---

**P22**

**Category:** process / planning
**Scope:** build & deploy
**Severity:** blocking
**Components:** build pipeline — container image — `Dockerfile`
**Problem Description:** When: previously always. The deployment artifact had never been built or run, so nothing about it was known to work and three defects were sitting in it undetected. The image is now built and exercised end to end.
**Cause:** No container runtime on the machine until 2026-08-24.
**Evidence:** Image 812 MB; resident memory 410 MB, confirming the plan's 1 GB sizing. The maximum sweep the page can send — four blocks × four chain stages × four capacities plus the baseline's four, 20 evaluations, 60 rows — completed in 5.72 s, 5.67 s and 5.70 s on the container's four CPUs, against a 75 s ceiling and a ~100 s front door. Three concurrent evaluations returned 200, 429, 429.
**Action:** Built, run, and exercised: every route answers through the front door, the descriptor returns the real self-description, the CSP names the configured mount point, admission control holds, readiness reports healthy, and the container stops with exit 0. The container figure is faster than the 13.0 s laptop figure recorded in B5; the discrepancy is unexplained and changes no decision, since both are far below the ceiling.
**Status:** resolved

---

**P23**

**Category:** coding implementation
**Scope:** build & deploy
**Severity:** blocking
**Components:** build pipeline — container startup — `Dockerfile`
**Problem Description:** When: always, on every container start. The image would not start at all, exiting before it bound a socket.
**Cause:** The image drops to a non-root user, but `/app` belongs to root and every run creates its log directory relative to the working directory.
**Evidence:** The first `docker run` exited 1 with `PermissionError: [Errno 13] Permission denied: 'data/logs'` and no other output.
**Action:** Done. The image creates `/app/data/logs`, hands it to the runtime user, and points `SIMULATOR_LOG_DIR` at it; the corpus beside it stays read-only, since nothing writes to it after the build. This restores 10.3.7 inside the artifact 10.3.12 mandates and alters no clause.
**Status:** resolved

---

**P24**

**Category:** specification defect
**Scope:** production, build & deploy
**Severity:** blocking
**Components:** back end — readiness and front-door admission — `simulator/gui/server.py`, `simulator/gui/api.py`, `project_metadata/ui-spec.md`
**Problem Description:** When: whenever the instance runs with a front-door secret configured, which is every public deployment. The readiness endpoint was refused by the front-door check, so the instance could never report itself ready and the platform would restart forever a container that was serving perfectly.
**Cause:** Two clauses contradicted each other in the deployed configuration: 12.2.15 refused every request lacking the shared secret without exception, while 12.2.9.1 made that endpoint what the platform asks. The platform's probe arrives on an internal address and cannot be given the secret.
**Evidence:** With a secret set, the container logged `refused a request that did not come through the front door` and `GET /api/health → 404` every 30 seconds, with an accumulating failing streak, while every other route returned 200 through the front door in the same run.
**Action:** Done, in both parts. Clause 12.2.15 now carries a single exemption for the readiness endpoint, and makes that exemption safe by requiring the exempt answer to be reduced to whether the process is up; 12.2.9.1 records that it is the one endpoint answered without the secret. The code admits the request, marks it, and withholds the process id, dataset and start time from a caller that did not come through the front door — the local launcher, which has no front door in front of it, still gets everything 12.2.8 needs. Verified in the container: readiness answers 200 with the signature alone and no secret, the descriptor still 404s without one, and the healthcheck reports `healthy`.
**The navigator had the identical defect** and was fixed in the same pass: its own front door refused its own `/healthz`, so it could never have been routed to either. Rule 4 of its `CONTRACT.md` now states the exemption and the reduction, so no future exhibit author reproduces this — the rule that caused the defect is the rule that now prevents it. That fix and its tests live in the navigator repository, per this report's scope.
**Status:** resolved, enforced forward

---

**P25**

**Category:** coding implementation
**Scope:** build & deploy
**Severity:** degrading
**Components:** build pipeline — container shutdown — `Dockerfile`
**Problem Description:** When: on every stop, deploy and restart of the deployed instance. The container ignored `SIGTERM` and was hard-killed at the end of its grace period, so 12.2.10's clean shutdown did not hold inside the artifact that actually ships — and the restart path depends on the listener being closed, not merely on the process ending.
**Cause:** The start command needed a shell to expand two variables, and without `exec` that shell remained process 1 with the server as its child. A process-1 shell does not forward signals, so the server's own handler never saw one.
**Evidence:** `docker stop` took the full 15 s grace period and exited 137, with no shutdown line in the log; process 1 was `sh -c python -m simulator gui …`. After the fix process 1 is the server, stop takes 0 s, exit is 0, and the log ends `closing listener` / `stopped`.
**Action:** Done. The command `exec`s, replacing the shell. Restores 12.2.10 inside the container and alters no clause.
**Status:** resolved

---

**P26**

**Category:** product design
**Scope:** production, project documentation
**Severity:** degrading
**Components:** both repositories — naming throughout
**Problem Description:** When: always, going forward. "Thesis" named the *argument* a project makes, not the thing the landing page lists, and it would read as false advertising on a personal project that is a demonstration rather than a dissertation.
**Cause:** The word was chosen when this repository was the only one and its content genuinely was a single technical argument.
**Evidence:** 35 occurrences here and 107 in the landing-page repository, spanning a served URL, a request header, a public identifier and a configuration file name.
**Action:** Done, as two words rather than one. A **project** is the work and the repository holding it; an **exhibit** is the independently deployed web page that presents one project. One project contributes exactly one exhibit. Renamed accordingly: `GET /thesis.json` → `GET /exhibit.json` (clause 12.2.16 edited under the confirmation procedure), `thesis_id` → `exhibit_id`, the header `X-Portal-Origin` → `X-Navigator-Origin`, the container user to `app`, and `thesis-portal` → `personal-project-navigator` with its package, `theses.toml` → `exhibits.toml`, and its environment prefix. Verified end to end: the navigator fetches the renamed descriptor from a running exhibit and renders it. Nothing was deployed yet, so the renames cost nothing at the front door.
**Status:** resolved

---

**P27**

**Category:** process / planning
**Scope:** project documentation
**Severity:** cosmetic
**Components:** repository instructions — `.claude/CLAUDE.md`
**Problem Description:** When: always. The *Related documents* table points at `project_metadata/term-dictionary.md`, which does not exist; the file is at `.disabled-terminology-discipline/term-dictionary.md`.
**Cause:** The terminology discipline was disabled and the dictionary moved with it; the pointer was not updated.
**Evidence:** `find` locates the file only under the disabled directory.
**Action:** Done, by repointing rather than dropping. Dropping the row would have removed the only record that the coined vocabulary exists and where it lives; repointing keeps it findable and adds what the old row could not say — that the discipline is disabled, so a newly coined term is deliberately not written into the file. This is why P26's *exhibit* is recorded in this report and in clause 12.2.16 rather than in the dictionary.
**Status:** resolved

---

**P29**

**Category:** process / planning
**Scope:** development tooling, build & deploy
**Severity:** degrading
**Components:** build pipeline — repository state — the working tree as a whole
**Problem Description:** When: while two sessions edit one working tree at the same time. A commit was pushed that captured another session's half-finished work, and the published commit had a failing test — the Section A equation read `∑iK` with a `K` its surrounding text never defined, which the "every symbol is defined" test correctly rejected. Three further tests went red in the working tree between staging and pushing.
**Cause:** `git add -A` stages whatever is on disk at that instant, and a second session was writing to the same tree throughout — files were modified seconds before the push. Nothing in the workflow distinguished this session's changes from another's.
**Evidence:** Running the suite against the pushed commit in a detached worktree gave `1 failed, 585 passed`, while the same suite in the working tree had passed moments earlier. File modification times spanned a continuous window ending sixteen seconds before the check.
**Action:** Done. The push was stopped rather than repeated, and the working tree was left untouched — force-pushing into a tree another writer owns risks destroying work in progress. The other session then completed and amended the commit itself. The merged result was re-validated rather than assumed: the suite is green at 589, the container image was rebuilt from the changed assets and re-exercised end to end (readiness exempt and reduced, descriptor refused without the secret, every route served, the maximum sweep at 5.6 s, concurrent evaluations refused 429, `SIGTERM` exit 0, healthcheck `healthy`), and the navigator was run against a live exhibit to confirm the renamed descriptor still drives the card.
**Status:** resolved

**The general lesson**, recorded because it will recur: a green suite in the working tree is not evidence that the *commit* is green when more than one writer is active. What proves it is running the suite against the committed state — a detached worktree of `HEAD` — which is how this was caught and is what should be done before any publish from a shared tree.
