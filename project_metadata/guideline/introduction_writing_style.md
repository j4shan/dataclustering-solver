# Writing Guidelines
## Plan and Execute a Logical Chain
When your goal is to get a topic across to an audience / readers, create an acyclic learning graph (DAG) to capture the interdependency between key arguments.
Your writing sequence should be a linearized (topologically sorted) operation sequence.

Example: understand basic math symbols -> understand the core formula -> understand experiment results -> derive the conclusion.

Note: a reasoning chain / DAG should never be included in the required output. They are temporary planning metadata to help generate the deliverable.

## Recommended Presentation Flow

1. Start with a mental model, explain the key concepts;
2. Define terms and mathematical symbols;
3. Define logical relationships and math formula;
4. [Optional] Add graphical illustration like diagrams, charts or images to emphasize key concepts.
5. Put forward observations and arguments to support (3).
6. Conclude the topic by summarizing key takeaways.

## Writing Style and Tone

Use simple words and sentence structures commonly found in a technical presentation.
Address the readers using a teaching persona:
- A professor presenting a paper;
- A manager presenting an execution plan;
Clarity is as important as correctness.

## Terminology and Reference

When introducing a new term, math symbol or acronym, ensure its formal definition is covered in the adjacent context.
When multiple key terms or a new math formula are introduced together, present their definitions in a tabular format - 1 row per term.
When introducing a technical term unknown to the general public, e.g. a scientific phenomenon, theory, design principle, surround the term with square brackets and inject a wiki weblink like [<term>]. Beware of context-dependent ambiguous terms.

When emphasizing a defined concept, cite its original definition location using "\<the concept description\> (`symbol`, defined in §X)".
As an example:
> the cost of materializing from the main table all records fetched to serve the query
> ($M_q$, defined in §2.4)
