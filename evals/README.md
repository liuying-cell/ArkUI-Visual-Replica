# Behavioral Evaluation Cases

`cases.json` defines forward-test cases for trigger precision, workflow routing, reference
budget, evidence discipline, and negative boundaries. It is a fixture, not proof that the skill
performs well.

Run each case in a fresh task with an isolated project copy and the raw artifacts implied by the prompt. Use the bundled labs for gesture, timeline, and scroll cases where the scene matches. Supply the referenced screenshot, mockup, or HTML for the other visual cases. Leave the skill discoverable and use the prompt without a skill mention when testing automatic triggering. Use explicit invocation only in a separate routing run. Keep expected workflows, references, and acceptance checks out of the task prompt.

Record:

- whether the skill triggered;
- the workflow selected;
- references actually read;
- edits or artifacts produced;
- visual evidence level reached and motion checks actually completed on the named target;
- pass, partial, or fail for each acceptance item;
- any user-project or unrelated-file side effects.

Treat a forbidden reference as a routing defect unless the agent explains a concrete task need
that is not already covered by the required references. Re-run all affected cases after changing
`SKILL.md`, reference routing, scripts, or behavioral constraints.
