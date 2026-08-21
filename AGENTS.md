# Project scope — dataclustering-solver

This project **frames and measures** a data-clustering problem: assigning events to storage
containers so as to minimize the volume read but not selected. It ships a problem definition, a
simulator that scores any candidate layout, explainer assets, and a local demonstration GUI that
presents all three. It deliberately ships **no assignment strategy** — strategies are
third-party plugins, and anything shipped is a baseline or a demonstration fixture, never a
recommendation.

## Spec Alignment

**Where the spec lives.** Two files, read as one document and referred to together as **the spec**:

| Relative Path | Description |
| --- | --- |
| [`project_metadata/simulator-spec.md`](project_metadata/simulator-spec.md) | Requirements for the problem, the harness, the plugin seams, and the engineering rules. |
| [`project_metadata/ui-spec.md`](project_metadata/ui-spec.md) | Requirements for the demonstration GUI, including the resolved design tokens. |

**What the spec holds.** Two kinds of clause, and nothing else:

- **Production requirements** — what the shipped product does, at the altitude of a requirement
  written before the code exists: capabilities, contracts, architecture style, quality
  attributes. They cover the code under `simulator/`, the resources the build generates and
  ships, and the public contracts a third party writes against.
- **User-supplied implementation guidelines** — a direction the user gave in a prompt that
  constrains *how* the product is built. It is recorded because nothing else in the repository
  preserves it. A structure, algorithm, library call or file path an agent chose on its own is
  not one of these and stays out.

The spec never records fulfilment status — no state column, no `Done`/`Partial`/`Spec` marker, no
note that a clause is not yet built. The spec states what must be true; the tests report what is.

The spec does not govern the content of an authored document: the formal statement, the engine
mapping, the README and the term dictionary are each their own authority, as the table at the end
of this file says. Requirements on **generated** resources — the figures, the canvases, the
scenario file, the pre-rendered fragments — do stay in the spec, because the build produces them
and the product ships them.

**Clause sequence id.** Every clause carries a hierarchical dotted id — `4.2.3`, `12.4.1` — unique
across the pair and individually addressable. Numbering runs continuously across both files, so
**§12 and above is the UI spec and everything below is the simulator spec**; a bare id is never
ambiguous. The spec is a snapshot of current requirements, not a version history: a superseded
clause is deleted rather than struck through or annotated, and ids are never renumbered.

**Update rule.** Whenever an action would add, remove, or alter a requirement or a user-supplied
guideline, the spec update is part of that action. Before performing either, stop and:

1. Present an **update summary** — the clause ids affected, and the add / edit / delete proposed
   for each. Removing a requirement means deleting the clause, or moving it to the *Deliberately
   not required* table with the reason — §11, or §13 if it is a GUI concern.
2. Ask the user to confirm, offering exactly `1. Yes` / `2. No`.
3. On **Yes**, apply the spec update first, then carry out the main action. On **No**, abort the
   main action as well and ask the user what to change.

A refactor, a bug fix restoring stated behaviour, a performance change within a stated budget, or
a wording edit alters no clause and triggers none of this.

Where the spec and the code disagree, one of them is a defect. Say which, and fix that one — never
silently reword a clause to match whatever the code happens to do.

## Authored HTML graphics

Authored HTML that draws — pane fragments and standalone canvases — is stored
under [`resources/graphics/`](resources/graphics/). A pane fragment is named
`section-<letter>-illustration.html` (`section-a-illustration.html`,
`section-c-illustration.html`, …). A standalone canvas is named `*-canvas.html`.
Do not add these files under `simulator/gui/static/`. That directory holds the
application shell, styles, scripts, and pre-rendered documents only. Generated
SVG pairs remain in [`resources/img/`](resources/img/). The files are served
through `/figures/` (9.16).

## Testing discipline

Every expectation this project holds is recorded in exactly two places: a **unit test** that
asserts it, and a **spec clause** that states it. A behaviour with neither is not a requirement,
and adding one means adding both.

Two patterns are prohibited outright:

- **No secondary implementation.** Production logic is written once. A module whose purpose is to
  be compared against another module — a reference implementation, an oracle, "the obvious slow
  way" — is not allowed, however small, slow, or independent it is. Testing a computation by
  writing it twice means two things to keep correct and no way to tell which one is wrong.
- **No runtime sidecar.** Nothing ships inside `simulator/` that exists only to check other code:
  no shadow mode, no debug-only parallel path, no self-verifying wrapper.

This does not mean fewer tests. It means tests **assert** rather than **recompute**. All of these
remain the right way to pin behaviour down:

- **closed-form anchors** — properties whose value is derivable without running the code
- **invariants and property tests** — relationships that hold for any input
- **round-trip and seam tests** — export, re-ingest, and compare
- **test-local fixtures** that construct inputs (`tests/conftest.py`)

## Related documents

| document | what it is |
| --- | --- |
| [`README.md`](README.md) | project abstract; the problem built up across several sections, no mathematics |
| [`project_metadata/problem-statement.md`](project_metadata/problem-statement.md) | the formal problem statement — model, objective, constraints, complexity |
| [`project_metadata/problem-statement-appendix.md`](project_metadata/problem-statement-appendix.md) | repository-only terminology reference and Poisson approximation derivation supporting the formal statement |
| [`project_metadata/production-design.md`](project_metadata/production-design.md) | the engine mapping — the problem statement realized on Databricks and Spark, and where it diverges |
| [`.disabled-terminology-discipline/term-dictionary.md`](.disabled-terminology-discipline/term-dictionary.md) | the project's coined vocabulary as a key-value lookup. **The discipline governing it is currently disabled**, which is what the directory name records: the file is kept for reference, and a newly coined term is not written into it. The *Terminology discipline* instruction it was governed by is supplied to the agent at user scope and is not part of this repository |
| [`project_metadata/simulator-spec.md`](project_metadata/simulator-spec.md) | **requirements for the problem, harness and seams** — §1–§11 |
| [`project_metadata/ui-spec.md`](project_metadata/ui-spec.md) | **requirements for the demonstration GUI** — §12–§13, including the resolved design tokens |
| [`project_metadata/section-a-illustration.md`](project_metadata/section-a-illustration.md) | product requirements for Section A's illustration pane — what it teaches, the shared instance, and how the figures are drawn |

The problem statement is the authority on the *problem*. The spec is the authority on what this
repository must *build*. Where a downstream document restates a decision from an upstream one, a
stale restatement is a defect of the same kind as stale code.
