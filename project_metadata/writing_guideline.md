# Writing Guidelines

This file summarizes the writing preferences established while revising the problem statement.
It is a plain editorial reference, not an official repository instruction.

## Order new information

Introduce ideas in the order a reader needs them. Establish the setting and the practical problem
before presenting notation, formulas, data structures, or qualifications.

A useful teaching sequence is:

1. name the familiar operation or problem in its domain context;
2. explain the concept in simple words;
3. introduce the formal name or symbol;
4. describe the mechanism that implements it;
5. analyze its cost and benefit together;
6. state the general observations;
7. conclude with the main consequence.

Do not introduce a solution structure before explaining the problem it solves. For example,
describe predicate-to-container resolution before introducing an index table as one pattern for
performing that resolution. When a concept relies on a premise such as columnar storage or late
materialization, explain the premise first.

Keep related reasoning together. If cost and benefit answer the same question, present them in one
subsection rather than separating them into disconnected arguments.

## Use a teaching tone

Write as if explaining the subject to college students encountering it for the first time. Prefer
plain declarative sentences over compressed expert shorthand. Maintain technical precision, but
do not require the reader to unpack several unstated ideas from one sentence.

Begin with an intuitive description, then increase formality. A reader should understand what an
object or operation does before being asked to interpret its notation.

Ground abstract ideas in the system being studied. In a database discussion, describe records,
queries, containers, predicate evaluation, data fetches, and materialization rather than leaving
the reader inside an unnecessarily abstract storage model.

## Introduce notation after meaning

State the concept first and place its symbol immediately after it. Explain unfamiliar notation in
the sentence that follows its first use.

For a forward reference, use this pattern:

> an abstract and naive description of the concept (`symbol`, defined in §X)

For example:

> the cost of materializing from the main table all records fetched to serve the query
> ($M_q$, defined in §3.4)

Do not lead with an undefined symbol and explain it later. Do not make the reader follow a forward
reference merely to learn the symbol's approximate meaning.

When notation may be mistaken for ordinary arithmetic, explain the operator directly. For
example, after introducing $\lambda(e)$ as the container assigned to event $e$, explain that
$\lambda^{-1}(c)$ is the set of events assigned to container $c$.

## State new concepts in complete sentences

Do not encode a new idea inside a short label such as “a byte-weighted variant.” State the idea
directly, explain why it matters, and then give its representation.

For example, first state that both event count and byte size are useful measures of data-fetch
overhead. Then state that the byte size of a container is

$$\operatorname{bytes}(E_c)=\sum_{e\in E_c}\operatorname{size}(e).$$

Headings may organize ideas, but they must not carry information that the ensuing prose fails to
state.

## Use concrete operation names

Name important system actions as operations. Prefer a concrete term such as **container fetch**
and a matching notation such as `FETCH(c)` over a metaphorical action whose database meaning must
be inferred.

Use the chosen term consistently in headings, prose, notation, diagrams, and cross-references.
Distinguish the operation from its cost: `FETCH(c)` is the action, while the volume returned is
the data-fetch cost.

## Connect formulas to the question

Before presenting a formula, state what practical quantity it represents and why the reader needs
it. Explain the numerator, denominator, and units in prose when introducing a ratio.

Do not imply that the model measures something before naming the question being studied. Connect
the metric to that question—for example, event count and compressed byte size matter because both
can describe data-fetch overhead.

After a derivation, translate the result back into plain language. The reader should not have to
interpret an inequality unaided to discover its operational meaning.

## Prefer observations to unnecessary proofs

Do not spend a subsection proving behavior that follows directly from a plainly stated mechanism
unless the proof resolves a genuine ambiguity. State the resulting observation and move on to its
consequence.

Useful observations identify what changes and what remains invariant. Examples include whether an
index changes query results, whether several indexes can coexist, whether low-cardinality labels
improve compression, and whether a cost varies across candidate layouts.

End the argument with its principal benefit. For the index-table discussion, that benefit is late
materialization: narrow, compressible columns resolve the predicate before dense main-table
columns are fetched.

## Keep the exposition on its subject

Do not interrupt an explanatory section with an “Out of scope” passage or reminders about what the
paper does not study. Develop the selected subject, its mechanism, and its consequences. Omit
non-goals from that explanatory flow.
