# Collaborative prose review protocol

**Objective.** Review technical prose through independent reading, turn-based debate, and explicit reconciliation before changing source files. Use this protocol when several related documents need a consistent voice and a reviewer could accidentally change a mathematical or operational claim while improving its style.

**Your tasks.** Give three reviewers the same brief, review one file at a time, limit discussion to four turns per file, record the discussion in one Markdown scratchpad, and summarize the agreed changes for the user.

## 1. Define the review brief

Name the source files and their reading order. Give every reviewer the same problem definition, audience, desired tone, and scope. State which source files are read-only during review. Require reviewers to preserve supported claims, qualifications, formulas, symbols, numbers, links, code, identifiers, and document structure. Ask them to flag factual or mathematical concerns separately from style proposals.

Use a brief such as:

> The prose is rigid and unnatural. Propose local paraphrases of connected sentences that improve structure, tone, and word choice for a technically literate reader. Preserve the technical meaning and all embedded markup. Do not edit the source files during review. Record any suspected factual or mathematical issue separately from the rewrite proposal.

## 2. Set up the scratchpad and turn gates

Create one shared `.md` scratchpad outside the source files. Give it a section for the common brief and a section for each file. The coordinator opens only one file section at a time and advances only after its fourth turn is complete.

Allow exactly four scratchpad turns for each file:

1. **Reviewer A — initial review.** Read the active file independently. Post recurring prose problems and one or two line-cited before/after passages.
2. **Reviewer B — challenge.** Draft an independent assessment before reading A's post. Then read it, challenge or endorse specific proposals, and post one or two additional passages.
3. **Reviewer C — challenge.** Draft an independent assessment before reading A and B. Then compare all three views, challenge or endorse specific proposals, and post one or two additional passages.
4. **Reviewer A — reconciliation.** Read B and C, then record agreed editorial rules, revised examples, rejected proposals with reasons, and unresolved technical questions.

Use an exclusive file lock for every scratchpad append, or have the coordinator serialize writes. Mark each post with the file, turn number, and reviewer. Do not let a reviewer write into a later file section before the coordinator opens it.

## 3. Review meaning as well as rhythm

Read each passage in context before proposing a rewrite. Prefer a small window of connected sentences over isolated word substitutions. Lead with the action or decision when the current prose stacks abstractions first. Remove repetition and interrupting cross-references only when their information remains clear nearby.

Compare each proposed passage with its source. Check that it keeps every condition, uncertainty, direction of an inequality, exception, and distinction between a model estimate and a measured result. Treat a change from “can” to “does,” from “expected” to “guaranteed,” or from an example value to a universal requirement as a meaning change. Keep mathematical and operational concerns in a separate note; do not silently settle them through a style edit.

## 4. Debate concrete alternatives

Respond to another reviewer's wording or claim, not only to its general theme. State what the proposal improves, what it risks, and the smallest correction that resolves the risk. Preserve the document's established voice unless the shared brief explicitly changes it. Use line references and before/after passages so the coordinator can verify each disagreement against the source.

## 5. Reconcile the file

In turn four, record a usable decision for every contested proposal: adopt, revise, or reject, with a short reason. State the editorial rules that apply to the file as a whole. Keep unresolved factual or mathematical questions visible and separate from the agreed prose. Close the file section before starting the next source file.

## 6. Summarize and hand off

After all file sections close, report the main prose discoveries, the agreed editing approach, and one before/after example per file. Distinguish confirmed corrections from open technical checks. Link the scratchpad and source files. State whether any source file changed during review.

If the user has not already authorized editing, request acceptance of the rewrite approach. Once editing is authorized, revise one source file at a time. Preserve formulas, links, identifiers, tables, headings, and other embedded structure; compare them with the original and check the final diff. Apply accepted technical clarifications as short assumption or boundary statements, without adding analysis the user did not request.
