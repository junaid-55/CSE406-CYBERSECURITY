# ToolGuard implementation and experiment guide

This document maps the project plan to the implemented system. Everything is
local and artificial: the inbox, outbox, addresses, profile, and canary.

## Hardware-conscious model choice

The target ThinkPad T480 has an Intel i5-8350U (4 cores/8 threads) and 12 GiB
RAM. ToolGuard therefore defaults to `llama3.2:3b` through Ollama. A typical
4-bit 3B model is substantially more practical on this CPU than the originally
proposed 8B model while retaining tool-call support. Keep other applications
closed during experiments. Use reduced repetitions only for development smoke
tests; keep the final reported model and repetition count fixed.

The deterministic backend is a transparent state machine for automated tests
and demo rehearsal. It intentionally follows the bundled payloads in vulnerable
mode. Never report its attack-success figures as empirical LLM results.

## Implemented modules

| Module | Responsibility |
|---|---|
| `src/workspace.py` | Atomic persistent mock inbox/outbox and reset |
| `src/tools.py` | Four student-written tools, schemas, argument checks, metadata |
| `src/llm_client.py` | Ollama HTTP adapter and deterministic rehearsal backend |
| `src/agent.py` | Student-written tool-call loop and security gateway |
| `src/attacker.py` | Inserts attacker-controlled email data only |
| `src/payloads.py` | A1–A4 plus canary-exfiltration C1 |
| `src/policy.py` | Deterministic least-privilege capability derivation |
| `src/logger.py` | Atomic structured JSON traces |
| `src/evaluator.py` | State-based per-run and aggregate metrics |
| `experiments/` | Benign, vulnerable, and defended suites |
| `tests/` | Tools, policy, attack, defense, and evaluator verification |

## Trust and execution path

```text
attacker.py -> mock email -> read_email output -> LLM tool request
                                                   |
                                                   v
user prompt -> deterministic capability set -> policy firewall -> executor
```

The model proposes actions but cannot directly mutate the workspace. Only the
executor can do that. In defended mode, the firewall checks each proposed tool
against capabilities derived from the unchanged original user prompt.

Security modes:

| Mode | Behavior |
|---|---|
| `vulnerable` | Registered model-requested tools execute |
| `delimited` | Same executor plus an untrusted-data prompt wrapper |
| `defended` | Code-enforced task capability allowlist |

With `--confirm`, an allowed sensitive/write operation also needs explicit
interactive approval. A denied or missing confirmation fails closed.

## Installation and validation

ToolGuard itself uses only Python's standard library. Python 3.11 or newer is
recommended.

```bash
python3 -m unittest discover -v
python3 -m src.workspace reset
python3 -m src.agent --backend deterministic --mode vulnerable \
  --prompt "Summarize my latest email."
```

Install Ollama using its official instructions, then prepare the real model:

```bash
ollama pull llama3.2:3b
ollama serve
ollama list
```

Use a second terminal for ToolGuard. A simple real-model smoke test is:

```bash
python3 -m src.workspace reset
python3 -m src.agent --backend ollama --mode defended \
  --prompt "Summarize my latest email."
```

## Live attack/defense demo

Baseline:

```bash
python3 -m src.workspace reset
python3 -m src.agent --backend ollama --mode vulnerable \
  --prompt "Summarize my latest email."
```

Attack—the attacker only plants external data:

```bash
python3 -m src.attacker --payload A2
python3 -m src.agent --backend ollama --mode vulnerable \
  --prompt "Summarize my latest email."
python3 -m src.workspace show
```

Defense with the same payload and user task:

```bash
python3 -m src.workspace reset
python3 -m src.attacker --payload A2
python3 -m src.agent --backend ollama --mode defended \
  --prompt "Summarize my latest email."
python3 -m src.workspace show
```

Legitimate write and confirmation:

```bash
python3 -m src.agent --backend ollama --mode defended --confirm \
  --prompt 'Send an email to bob@demo.local saying "Demo complete".'
```

If a real small model does not emit a tool call for a payload, record the failed
trial. Do not substitute deterministic output as model output.

## Reproducible experiments

Attack cases address the planted message directly as email ID 3. This keeps
small-model failures in newest-message planning from preventing the injection
text from reaching the model; benign task B2 separately measures the full
list-then-read workflow. In vulnerable and firewall modes, the intentionally
unsafe baseline promotes `read_email` output into a trusted system message.
Delimited mode keeps the same output marked as untrusted data. Report this
controlled trust-boundary misconfiguration when interpreting ASR.

Run each suite with the same model, settings, and repetition count:

```bash
python3 -m experiments.run_benign --backend ollama --repetitions 5
python3 -m experiments.run_attacks --backend ollama --repetitions 5
python3 -m experiments.run_defenses --backend ollama --mode delimited --repetitions 5
python3 -m experiments.run_defenses --backend ollama --mode defended --repetitions 5
python3 -m src.evaluator logs
```

JSON logs include the prompt, mode, model, available/allowed tools, exact calls
and arguments, policy decisions, final response, before/after workspace state,
and state-derived metrics. Log filenames use UTC timestamps and case IDs.

Before collecting final results, archive or move rehearsal logs so deterministic
and Ollama trials are not aggregated together. Record:

```bash
python3 --version
ollama --version
ollama list
```

Also record the model digest shown by Ollama, `config.yaml`, payload version,
task/case IDs, repetition count, and the machine specification.

## Report result table

Populate this only from Ollama JSON logs:

| Mode | Trials | ASR | Blocked attack rate | Benign utility | False blocking |
|---|---:|---:|---:|---:|---:|
| Normal baseline | | N/A | N/A | | |
| Vulnerable attack | | | | | |
| Delimiting baseline | | | | | |
| Firewall | | | | | |
| Firewall + confirmation | | | | | |

Screenshots should show the attacker insertion, malicious `read_email` result,
model tool request, vulnerable outbox state, firewall decision, defended outbox,
and a successful explicitly authorized write. State clearly that traditional
packet/header modification is not applicable; the attacker-controlled email
`body` in the logical tool-result message is the malicious payload.

## Limitations

- The deterministic intent parser covers the fixed, documented task suite; a
  production policy planner would need broader verified intent handling.
- A small CPU-run model may have lower attack or task success than an 8B model.
- Prompt delimiting is a comparison baseline, not a hard security boundary.
- The workspace models email behavior but does not reproduce a real provider.
- All findings apply to the pinned model and payload/task set used in the run.
