# Running a user test of a skill

A user test puts a skill in front of people who did not write it and records
what happens. These notes come from running one.

## Before the session

- **Decide what the scenario is for.** Say in the handout whether participants
  should paste the scenario as a prompt or write their own request from it.
  Pasting tests the skill on a well-specified request; paraphrasing tests it on
  a realistic one. Participants left to guess will split, and any wording in a
  pasted scenario ("go back and forth until you feel comfortable") becomes an
  instruction to the agent.
- **Make the scenario's premise checkable, or say that it is invented.**
  Participants research the premise first (for example, the legislation a
  scenario mentions). That is either part of what you are observing or a
  distraction.
- **Consider a no-skill baseline.** Run the same task once without the skill,
  either cold or after a short discussion of the concept. Otherwise it is hard
  to see what the skill contributed.
- **Set up sharing in advance.** Ask participants to work in a regular chat,
  not Cowork, and to ask for outputs as markdown files. Collect share links in
  one place. Claude Docs and published artifacts may not be readable by the
  people analyzing the session, even in the same organization.
- **Tell participants what tools can help.** Browser access and pasting URLs
  unblock pages the agent cannot fetch. Decide whether to allow them, since
  they change what the skill can do.

## During the session

- Record the debrief, with consent stated at the start.
- Ask open questions first ("how did that go?"), then about specific steps.
- Leave time for "what else should exist?" Participants who have just used one
  skill tend to name the next one.

## After the session

- Transcribe without speaker attribution unless participants agreed to be
  named. Remove names from chat logs before circulating them.
- Gather every chat and output, labeled by scenario. Note which outputs could
  not be retrieved and why.
- Break feedback into changes to the skill, guidance for users, and changes to
  the exercise. Note what the current skill text already says on each point.
- Read the chat logs as a separate source from the debrief. They show behavior
  participants did not mention, and they correct things participants
  misremembered.
- Put dated findings in `docs/research/` of the repository that owns the skill
  or, if general, here. Put adopted advice in the skill's `README.md` or in
  [writing-skills.md](writing-skills.md).
