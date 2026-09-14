# Project metadata guideline

**Objective.** Keep project-owned documents and authored assets in a fixed tree so later
sessions find requirements, contracts, plans, and exhibits in one place.

**Your tasks.** Maintain the product spec, place project metadata, and place authored
resources. Each section states when it applies.

## 1. Capture a requirement

When the user states a product requirement — what the product is, what it must do, how it
must behave, or how it must look and feel — write it into the PRD for the matching
top-level component. Create that file if it does not exist — this is your responsibility,
not a precondition to wait on.

When the prompt states no new product requirement, leave the product spec unchanged.

The word **spec** means these PRD files and nothing else.

Never write a decision the system resolved on its own and the user did not confirm. Typical
examples: UI widget theme, colour code, size.

Never write coding implementation guidelines, tools and dependencies, or build processes
unless the user explicitly requested them.

## 2. Keep one PRD per top-level component

Put each top-level system component in its own file under `project_metadata/product_spec/`,
relative to the project root.

## 3. Identify every clause

Give every clause a hierarchical dotted id — `1.2.3` — unique across the product spec. The
spec is a snapshot of current requirements, not a version history. Delete a superseded
clause. Never strike it through, annotate it, or renumber remaining ids.

## 4. Review the spec when changing code

Read the product spec before you change code. Where the spec and the code disagree, say
which is the defect and fix that one. Never silently reword a clause to match the code.

## 5. Retire a requirement

When the user retires a requirement, delete the clause.

## 6. Place project metadata

Keep project-owned documents under `project_metadata/`, relative to the project root.

- Put product requirements in `project_metadata/product_spec/`. Follow the product-spec
  commands above.
- Put project-owned writing and generation contracts in `project_metadata/instructions/`.
- Put transient execution plans in `project_metadata/plans/`. Never version them.

## 7. Place authored resources

Split authored assets by where they end up, not by what they are. Two trees, relative to
the project root.

`site/` is the published exhibit. It is served as-is and copied as-is: whatever sits in it
reaches the public, and nothing else does. The directory layout is the URL layout, so a
path that works on disk works in the browser.

- Put the page, its stylesheets, and its scripts at `site/`.
- Put walkthrough and glossary fragments at `site/`, beside the page that mounts them.
- Put illustration fragments in `site/figures/html/`.
- Put figures in `site/figures/img/`.
- Put formal documents in `site/docs/`.

`resources/` is authoring material. It is never served and never published.

- Put diagram sources in `resources/img_src/`.
- Put figure prompts in `resources/img_prompt/`.
- Put authored scenario and fixture data in `resources/data/`. Do not put runtime-generated
  data there.

Never put temporary or git-ignored resources in either tree.

Two rules follow from the split:

- Adding a file to `site/` publishes it. If a reader should not have it, it belongs in
  `resources/`.
- A generator writes its source to `resources/` and its output to `site/`. A diagram
  source and the raster it exports do not live together.
