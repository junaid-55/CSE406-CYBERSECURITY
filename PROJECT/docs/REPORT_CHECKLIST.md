# CSE406 Project 29 report and demo checklist

## Evidence to collect

- [ ] Python, Ollama, model tag, and model digest
- [ ] T480 CPU/RAM specification
- [ ] Exact `config.yaml`, task set, payload version, and repetitions
- [ ] Benign tool trace and correct output
- [ ] Attacker insertion trace proving no victim tool was invoked
- [ ] Malicious `read_email` tool result
- [ ] Unauthorized tool request in vulnerable mode
- [ ] Outbox state proving the unauthorized action
- [ ] Same case blocked in defended mode
- [ ] Empty defended outbox
- [ ] Explicitly authorized send succeeding, with confirmation if enabled
- [ ] Aggregate Ollama metrics generated from JSON logs
- [ ] Failed attacks retained and counted

## Required explanation

- [ ] Define indirect prompt injection and tool-output injection
- [ ] Distinguish it from direct jailbreaking and answer-only RAG poisoning
- [ ] State the attacker, victim, agent, executor, and workspace assumptions
- [ ] Identify `read_email().body` as attacker-controlled data
- [ ] Explain why natural-language data and instructions share model context
- [ ] Define success from workspace state rather than model text
- [ ] Explain allowlist derivation and enforcement outside the LLM
- [ ] Discuss prompt delimiting versus the capability boundary
- [ ] Discuss false blocks, small-model limitations, and external validity
- [ ] List actual contribution by each member

## Figures

- [ ] Topology and trust boundary
- [ ] Normal timing diagram
- [ ] Vulnerable attack timing diagram
- [ ] Defended timing diagram
- [ ] Logical tool request/result schema instead of packet headers
