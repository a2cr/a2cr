# A2CR Vision

A2CR starts with a modest goal: make AI handoffs small, explicit, testable, and
safer than copying a whole conversation history.

There is a broader design question behind that goal:

> What is the smallest useful state one agent can pass to another so real work
> can continue safely?

A2CR is an early attempt to explore that question in public. If different
agents, tools, and developers settle on similar handoff shapes, context relay
becomes easier to reuse across systems instead of staying inside one product.
The goal is not to preserve everything an AI said. The goal is to give the next
agent the few facts it needs to act with continuity, accountability, and
restraint.

If this pattern becomes a shared convention, it could apply beyond coding
agents. Any AI system that needs to hand off work across tools, models, devices,
or time can benefit from a compact state relay:

- cross-client handoff between Codex, Claude Code, Cursor, and other MCP clients
- long-running research, support, operations, and documentation agents
- multi-agent workspaces where agents coordinate without treating chat history
  as the source of truth
- industrial, operational, embodied, or physical AI, where a system may need to
  pass the current task, asset or environment notes, inspection results, safety
  constraints, validation status, and next action without exposing raw logs or
  credentials

That future depends on clear schemas, careful security boundaries, and real
feedback from people building agent workflows. A2CR-style handoffs should not
replace certified safety systems, human approval, or industrial control
requirements; they are a way to make AI work state easier to inspect and relay.

As WorkThreads matures, A2CR could also support richer coordination patterns.
WorkBaton is for serial handoff, while WorkThreads is the planned space for
shared work: agents could claim tasks, ask for review, record decisions, hand
off partial results, surface blockers, and let humans inspect what changed
before the next action. This could make A2CR useful not only for restarting one
AI window, but also for coordinating teams of agents across software projects,
research workflows, operations, and field or industrial tasks.

One possible direction is portable IDs. Instead of tying a handoff to one chat
window, one tool, or one vendor, a future handoff shape could carry stable
identifiers that other agents can understand:

```json
{
  "relay_id": "a2cr:relay:example-001",
  "workspace_id": "workspace:demo-lab",
  "task_id": "task:inspect-shelf-042",
  "handoff_id": "handoff:agent-a-to-agent-b:001",
  "actor_id": "agent:mobile-unit-01",
  "environment_id": "env:warehouse-zone-3",
  "asset_id": "asset:conveyor-07",
  "inspection_id": "inspection:visual-check-2026-05-13",
  "safety_case_id": "safety:keep-clear-zone-a"
}
```

These IDs are examples, not required fields in the current wrapper. They show
the kind of stable references that could make context relay reusable across
software agents, physical systems, and future agent runtimes. They should not
contain credentials, personal data, or secrets.

If you are building agents, MCP clients, developer tools, robotics workflows,
industrial AI systems, or long-running automation, this is the part we want to
explore with you: what should a useful handoff contain, and what must it never
contain?
