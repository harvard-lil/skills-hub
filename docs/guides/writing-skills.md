# Writing skills

How to write a skill's instructions, its metadata, and its guide. Much of this
comes from watching people use skills in a user test. Which file is packaged, and which file has which audience, is set by the
[hub-directory decision](../adr/2026-10-16-hub-directory-and-user-guide.md).

## Instructions (`SKILL.md` body)

The general rule: describe the goal and the judgment involved, not a script.
Agents are capable enough that over-specified steps mostly stop them from
fitting the work to the person. Name the routes and sources that tend to work
without making any one of them mandatory.

- **Build in a review pass.** Have the skill re-check its output against its
  sources before calling it done, and say what the pass changed. In testing,
  users who asked for one found real errors.
- **Give outputs a shape.** Ship a template in `references/`, and say that
  sections beyond it need the user's request. Without one, outputs from
  different runs cannot be compared. Agents also add sections users find hard
  to evaluate.
- **Ship a worked example** when the output is a document. Keep it abbreviated,
  with facts that were checked and dated, since an agent may imitate it.
- **Produce a short handoff as well as the full record** when the output is
  meant for someone else.
- **Say what a choice costs when asking the person to choose.** People default
  to "everything." That is a fine answer once they know what it implies. Define
  any grouping the agent invents before asking someone to pick from it.
- **Mark how each fact is known**: visited, seen in a search result, from
  memory, or supplied by the user. Memory is a lead to confirm, not a finding.
- **Explain why, where the field has reasons.** "Collect the documentation"
  produces less than a short list of what the documentation is for. A list of
  purposes lets the agent recognize material the skill author did not name.
- **Save long intermediate results to files.** Anything held only in a browser
  tab or tool output is gone when the session ends.
- **Name the next skill at the boundary.** When the person's goal goes past
  this skill, say which skill continues it. Offer to continue if that skill is
  installed, and suggest installing it if not. A hard stop just gets ignored.
- **Fit questions to the person.** Ask what they already know when it isn't
  clear, and adjust how much you explain. Tell them up front how the
  conversation will go, so they know when decisions are coming.

## Metadata

### `description` (`SKILL.md` frontmatter)

The agent reads this to decide whether to load the skill, so it is a routing
signal.

- Say what the skill produces, then when to use it.
- **Trigger on the need, not on the user's role.** "Use when someone needs a
  dataset's boundaries pinned down so it can be preserved, monitored, or handed
  off" reaches anyone with that need. A list of the kinds of people who might
  use the skill reaches no one in particular.
- **Exclude the near misses.** If a common request shares the skill's
  vocabulary but not its purpose, say so ("Not for answering a question from
  data, such as looking up a statistic"). Avoid verbs that pull in those
  requests, such as "query" for a skill that is not about querying.
- Keep it on one line. The builder's frontmatter parser is line-based.
- Add a rubric scenario for each exclusion, so an evaluation can show whether
  routing works.

### `summary` (`_hub/metadata.yaml`)

One sentence for someone browsing the site and deciding whether to install the
skill. Say what they get, in plain words.

- `description`: "Use when someone names a dataset they want to preserve…"
- `summary`: "Turn a loose name like "CDC covid data" into a precise list of
  what to save, ready to hand to whoever collects it."

### Guide (`README.md`)

The skill page leads with the guide. It also ships with the skill, so an agent
can answer "how do I use this?" if `SKILL.md` points to it. Useful sections, in
order:

1. **What it does**, in two or three sentences.
2. **Before you start**: what to have ready, and why each thing changes the
   result.
3. **Starting a conversation**: one example request in a user's own words.
4. **What you'll be asked**: the decisions the person will face, so they can
   think ahead.
5. **Getting the most out of it**: moves particular to this skill that worked
   in testing.
6. **What you get back**, and where an example lives.
7. **Limits**, and which skill comes next.

Write from observed use where you have it. Tips nobody has tested read like
marketing.

## Advice that applies to every skill

Advice that applies to any skill, or to AI chatbots generally, belongs on one
page of the hub's site rather than repeated in each guide. Put that page in
`website/` and link it from every skill page with `website/_skill_note.html`.
`pubdata-skills`' "Using Skills Well" page is an example. Since a guide ships
inside the package, link to the hub page by its absolute URL.

Topics such a page covered after the first user test:

- **Check the setup first.** Is the skill installed and in use? Can the agent
  reach the sites, and see interactive pages?
- **Ask in your own words**, with context, rather than pasting a scenario.
- **Treat the first result as a draft.** Ask for a check pass, push on thin
  claims, ask for confidence, and ask for dependent statements to be updated
  when a decision changes.
- **Ask for files in a usable format, and work where the conversation can be
  shared.**
