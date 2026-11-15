---
name: technical-writing
description: Deprecated and retained for reference only. Produce a technical explanation as a linearized teaching sequence — mental model, term and symbol definitions, formulas, optional figures, supporting arguments, and takeaways.
disable-model-invocation: true
---

# Technical writing

**Deprecated.** Retain this skill for reference. Do not install it by default.

**Objective.** Get a topic across to readers as a teaching presentation: one acyclic
learning sequence, defined terms where they appear, and a title that names the subject.

**Your tasks.** Plan the learning sequence, write in the recommended flow, keep the
teaching persona, and define every new term where it is introduced.

## 1. Plan the learning sequence

Create an acyclic learning graph (DAG) of the interdependency between key arguments.
Write in a linearized (topologically sorted) order.

Example: understand basic math symbols -> understand the core formula -> understand
experiment results -> derive the conclusion.

Never include the reasoning chain or DAG in the required output. They are temporary
planning metadata.

## 2. Present in this flow

1. Start with a mental model. Explain the key concepts.
2. Define terms and mathematical symbols.
3. Define logical relationships and math formulas.
4. Optionally add a diagram, chart, or image to emphasize a key concept.
5. Put forward observations and arguments that support (3).
6. Conclude by summarizing key takeaways.

## 3. Write in the teaching persona

Use simple words and sentence structures commonly found in a technical presentation.
Address readers as a professor presenting a paper or a manager presenting an execution
plan. Clarity is as important as correctness.

Write every title as a noun or noun phrase, never as a questioning sentence.

## 4. Define terms where they appear

When introducing a new term, math symbol, or acronym, cover its formal definition in
the adjacent context.

When introducing several key terms or a new math formula together, present their
definitions in a table — one row per term.

When introducing a technical term unknown to the general public (a scientific
phenomenon, theory, or design principle), surround the term with square brackets and
inject a wiki weblink like [<term>]. Watch for context-dependent ambiguous terms.

When emphasizing a defined concept, cite its original definition as
"<the concept description> (`symbol`, defined in §X)".

Example:

> the cost of materializing from the main table all records fetched to serve the query
> ($M_q$, defined in §2.4)
