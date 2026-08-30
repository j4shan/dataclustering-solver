# Project scope — dataclustering-solver

This project **frames and measures** a data-clustering problem: assigning events to storage
containers so as to minimize the volume read but not selected. It ships a problem definition, a
simulator that scores any candidate layout, explainer assets, and a local demonstration GUI that
presents them. It deliberately ships **no assignment strategy** — strategies are
third-party plugins, and anything shipped is a baseline or a demonstration fixture, never a
recommendation.

## Spec Alignment

**Where the spec lives.** Two files, read as one document and referred to together as **the spec**:

| Relative Path | Description |
| --- | --- |
| [`project_metadata/simulator-spec.md`](project_metadata/simulator-spec.md) | Requirements for the problem, the harness, the plugin seams, and the engineering rules. |
| [`project_metadata/ui-spec.md`](project_metadata/ui-spec.md) | Requirements for the demonstration GUI, including the resolved design tokens. |

**Origin.** Every clause must originate from a requirement the user stated directly in a prompt.
An agent-chosen structure, algorithm, library, or file path is not a requirement and is not written
into the spec. The spec states what must be true; it never records fulfilment.

**Clause sequence id.** Every clause carries a hierarchical dotted id — `4.2.3`, `12.4.1` —
unique across the pair and individually addressable. Numbering runs continuously across both files,
so **§12 and above is the UI spec and everything below is the simulator spec**; a bare id is never
ambiguous. The spec is a snapshot of current requirements, not a version history: a superseded
clause is deleted rather than struck through or annotated, and ids are never renumbered.

**Workflow.** When an action that generates code or modifies a design is executed:

1. **Capture** the requirements the user stated explicitly in the prompt.
2. Respond with a **spec update proposal** — the clause ids affected, and the add / edit / delete
   proposed for each. Removing a requirement means deleting the clause, or moving it to the
   *Deliberately not required* table with the reason — §11, or §13 if it is a GUI concern. Ask
   the user to confirm, offering exactly `1. Yes` / `2. No`.
3. On **Yes**, update the spec, then carry out the action. On **No**, abort the action and ask the
   user what to change.

If the prompt states no new requirement, there is no proposal and no spec change.

Where the spec and the code disagree, one of them is a defect. Say which, and fix that one — never
silently reword a clause to match whatever the code happens to do.

## Authored HTML graphics

Authored HTML that draws — pane fragments and standalone canvases — is stored
under [`resources/graphics/`](resources/graphics/), together with the formal
problem statement and its appendix. A pane fragment is named
`section-<letter>-illustration.html` (`section-a-illustration.html`,
`section-c-illustration.html`, …). A standalone canvas is named `*-canvas.html`.
Do not add these files under `simulator/gui/static/`. That directory holds the
application shell, styles, scripts, and pre-rendered documents only. Generated
SVG pairs remain in [`resources/img/`](resources/img/). The files are served
through `/figures/` (9.16).

## Testing discipline

- **No runtime sidecar.** Nothing ships inside `simulator/` that exists only to check other code:
  no shadow mode, no debug-only parallel path, no self-verifying wrapper.
- **No redundant cases.** Before adding a unit test, check the existing suite for a case that
  already asserts the same behaviour. Do not add a second case that repeats an existing
  assertion under a different name, fixture, or file.

## Related documents

| document | what it is |
| --- | --- |
| [`README.md`](README.md) | project abstract; the problem built up across several sections, no mathematics |
| [`resources/graphics/problem-statement.md`](resources/graphics/problem-statement.md) | the formal problem statement — model, objective, constraints, complexity |
| [`resources/graphics/problem-statement-appendix.md`](resources/graphics/problem-statement-appendix.md) | repository-only terminology reference and Poisson approximation derivation supporting the formal statement |
| [`project_metadata/production-design.md`](project_metadata/production-design.md) | the engine mapping — the problem statement realized on Databricks and Spark, and where it diverges |
| [`.disabled-terminology-discipline/term-dictionary.md`](.disabled-terminology-discipline/term-dictionary.md) | the project's coined vocabulary as a key-value lookup. **The discipline governing it is currently disabled**, which is what the directory name records: the file is kept for reference, and a newly coined term is not written into it. The *Terminology discipline* instruction it was governed by is supplied to the agent at user scope and is not part of this repository |
| [`project_metadata/simulator-spec.md`](project_metadata/simulator-spec.md) | **requirements for the problem, harness and seams** — §1–§11 |
| [`project_metadata/ui-spec.md`](project_metadata/ui-spec.md) | **requirements for the demonstration GUI** — §12–§13, including the resolved design tokens |
| [`project_metadata/section-a-illustration.md`](project_metadata/section-a-illustration.md) | product requirements for Section A's illustration pane — what it teaches, the shared instance, and how the figures are drawn |
| [`project_metadata/section-d-illustration.md`](project_metadata/section-d-illustration.md) | product requirements for Section D — the Gini walkthrough and the four figures |
| [`project_metadata/section-d-walkthrough.md`](project_metadata/section-d-walkthrough.md) | the left-pane source for Section D |
| [`project_metadata/guideline/introduction_writing_style.md`](project_metadata/guideline/introduction_writing_style.md) | writing contract for Section D's left pane |

The problem statement is the authority on the *problem*. The spec is the authority on what this
repository must *build*. Where a downstream document restates a decision from an upstream one, a
stale restatement is a defect of the same kind as stale code.
